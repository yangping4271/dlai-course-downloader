"""DeepLearning.AI 课程下载器核心功能模块"""
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Union
from urllib.parse import urlparse, quote

import requests

# 配置常量
COURSE_HOST = "learn.deeplearning.ai"
REQUEST_TIMEOUT = 30
DEFAULT_THREADS = 8
DEFAULT_QUALITY = "res:1080,codec:h264"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    index: int
    title: str
    url: str


def sanitize_filename(name: str) -> str:
    """清理文件名，移除跨平台不兼容的字符"""
    name = re.sub(r"[\\/:*?\"<>|]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def slugify(text: str) -> str:
    """将文本转换为URL友好的slug"""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "lesson"


def is_specialization_url(url: str) -> bool:
    """判断URL是否为专项课程URL"""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split('/') if p]
    return len(parts) >= 2 and parts[0] == 'specializations'


def get_specialization_slug(url: str) -> str:
    """从专项课程URL中提取slug"""
    parsed = urlparse(url)
    if parsed.netloc != COURSE_HOST:
        raise ValueError(f"URL host must be {COURSE_HOST}")

    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 2 or parts[0] != 'specializations':
        raise ValueError("Not a recognized specialization URL under /specializations/<slug>")

    return parts[1]


def get_course_base_url(input_url: str) -> Tuple[str, str]:
    """从任意课程课时URL获取课程基础URL和课程slug"""
    parsed = urlparse(input_url)
    if parsed.netloc != COURSE_HOST:
        raise ValueError(f"URL host must be {COURSE_HOST}")

    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 2 or parts[0] != 'courses':
        raise ValueError("Not a recognized course URL under /courses/<slug>")

    course_slug = parts[1]
    course_base = f"https://{COURSE_HOST}/courses/{course_slug}"
    return course_base, course_slug


def get_course_slug(url: str) -> str:
    """从URL中提取课程slug"""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 2 or parts[0] != 'courses':
        raise ValueError("Expect course URL under /courses/<slug> or any lesson under it")
    return parts[1]


def build_session_with_chrome_cookies() -> requests.Session:
    """构建用于获取元数据的requests会话"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://{COURSE_HOST}/",
    })
    return session


def _build_api_url(course_slug: str) -> str:
    """构建API URL，修复硬编码问题"""
    api_params = json.dumps({"json": {"courseSlug": course_slug}})
    encoded_params = quote(api_params, safe='')
    return f"https://{COURSE_HOST}/api/trpc/course.getCourseBySlug?input={encoded_params}"


def _build_specialization_api_url(specialization_slug: str) -> str:
    """构建专项课程API URL"""
    api_params = json.dumps({"json": {"specializationSlug": specialization_slug}})
    encoded_params = quote(api_params, safe='')
    return f"https://{COURSE_HOST}/api/trpc/course.getSpecialization?input={encoded_params}"


def fetch_course_data(course_slug: str) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """统一的课程数据获取函数

    Returns:
        Tuple: (course_title, lessons_map, ordered_keys)
    """
    session = build_session_with_chrome_cookies()
    api_url = _build_api_url(course_slug)

    try:
        resp = session.get(api_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        json_obj = data.get("result", {}).get("data", {}).get("json", {})

        course_title: str = json_obj.get("name") or course_slug
        lessons_map: Dict[str, Any] = json_obj.get("lessons", {})
        listing: List[Dict[str, Any]] = json_obj.get("listing", [])

        # 获取排序的课时键
        ordered_keys: List[str] = []
        for block in listing or []:
            for item in block.get("content", []) or []:
                if item.get("type") == "lesson" and item.get("key"):
                    ordered_keys.append(item["key"])

        return course_title, lessons_map, ordered_keys

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API请求失败: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"API响应解析失败: {e}")


def fetch_specialization_data(specialization_slug: str) -> Tuple[str, List[Dict[str, Any]]]:
    """获取专项课程数据

    Returns:
        Tuple: (specialization_title, courses_list)
        courses_list 中每个元素包含: {"name": str, "slug": str, "lessons": Dict}
    """
    session = build_session_with_chrome_cookies()
    api_url = _build_specialization_api_url(specialization_slug)

    try:
        resp = session.get(api_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        json_obj = data.get("result", {}).get("data", {}).get("json", {})

        specialization_title: str = json_obj.get("name") or specialization_slug
        courses_raw: List[Dict[str, Any]] = json_obj.get("courses", [])

        # 提取课程信息
        courses_list: List[Dict[str, Any]] = []
        for course in courses_raw:
            course_name = course.get("name", "")
            course_slug = course.get("slug", "")
            lessons_map = course.get("lessons", {})
            courses_list.append({
                "name": course_name,
                "slug": course_slug,
                "lessons": lessons_map
            })

        return specialization_title, courses_list

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"专项课程API请求失败: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"专项课程API响应解析失败: {e}")



def fetch_course_outline_via_api(course_slug: str) -> Tuple[str, List[Lesson]]:
    """通过API获取课程大纲，仅包含视频课时"""
    course_title, lessons_map, ordered_keys = fetch_course_data(course_slug)

    lessons: List[Lesson] = []

    def add_lesson(key: str, lesson_obj: Dict[str, Any]):
        if not lesson_obj:
            return
        if (lesson_obj.get("type") or "").lower() != "video":
            return
        idx = int(lesson_obj.get("index") or 0)
        name = str(lesson_obj.get("name") or f"Lesson {idx}")
        lesson_slug = str(lesson_obj.get("slug") or key)
        lesson_name_slug = slugify(name)
        url = (
            f"https://{COURSE_HOST}/courses/{course_slug}/lesson/{lesson_slug}/{lesson_name_slug}"
        )
        lessons.append(Lesson(index=idx, title=name, url=url))

    # 按顺序添加课时
    if ordered_keys:
        for k in ordered_keys:
            add_lesson(k, lessons_map.get(k))
    else:
        for k, v in sorted(lessons_map.items(), key=lambda kv: int((kv[1] or {}).get("index") or 0)):
            add_lesson(k, v)

    lessons = [l for l in lessons if l.index > 0]
    lessons.sort(key=lambda l: l.index)

    if not lessons:
        raise RuntimeError("课程 API 返回为空或无视频课时。")

    return course_title, lessons


def get_outline_for_csv(course_slug: str) -> Tuple[str, List[Dict[str, Any]]]:
    """为CSV导出获取课程大纲"""
    course_title, lessons_map, ordered_keys = fetch_course_data(course_slug)

    def is_video(obj: Dict[str, Any]) -> bool:
        return (obj.get("type") or "").lower() == "video"

    lessons: List[Dict[str, Any]] = []
    if ordered_keys:
        for key in ordered_keys:
            obj = lessons_map.get(key)
            if obj and is_video(obj):
                lessons.append(obj)
    else:
        for _, obj in sorted(lessons_map.items(), key=lambda kv: int((kv[1] or {}).get("index") or 0)):
            if obj and is_video(obj):
                lessons.append(obj)

    return course_title, lessons


def get_specialization_outline_for_csv(specialization_slug: str) -> Tuple[str, List[Dict[str, Any]]]:
    """为CSV导出获取专项课程大纲

    Returns:
        Tuple: (specialization_title, lessons_list)
        lessons_list中每个元素包含课时信息，并额外添加course_name、course_slug和course_index字段
    """
    specialization_title, courses = fetch_specialization_data(specialization_slug)

    def is_video(obj: Dict[str, Any]) -> bool:
        return (obj.get("type") or "").lower() == "video"

    all_lessons: List[Dict[str, Any]] = []

    for course_index, course in enumerate(courses):
        course_name = course["name"]
        course_slug = course["slug"]
        lessons_map = course["lessons"]

        # 按index排序并筛选视频课时
        video_lessons = []
        for _, obj in sorted(lessons_map.items(), key=lambda kv: int((kv[1] or {}).get("index") or 0)):
            if obj and is_video(obj):
                # 复制对象并添加课程信息
                lesson_with_course = obj.copy()
                lesson_with_course["course_name"] = course_name
                lesson_with_course["course_slug"] = course_slug
                lesson_with_course["course_index"] = course_index
                video_lessons.append(lesson_with_course)

        all_lessons.extend(video_lessons)

    return specialization_title, all_lessons


def extract_direct_url(lesson_url: str) -> str:
    """使用yt-dlp解析实际媒体URL"""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--cookies-from-browser", "chrome",
        "-g",
        "-f", "bv*+ba/b",
        lesson_url,
    ]

    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or "Unknown yt-dlp error"
            raise RuntimeError(f"yt-dlp执行失败: {error_msg}")

        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if not lines:
            raise RuntimeError("yt-dlp未返回任何URL")

        return lines[0]

    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp执行超时")
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"调用yt-dlp时发生未知错误: {e}")


def build_lesson_url(course_slug: str, lesson_obj: Dict[str, Any]) -> Tuple[int, str, str]:
    """构建课时查看URL"""
    idx = int(lesson_obj.get("index") or 0)
    name = str(lesson_obj.get("name") or f"Lesson {idx}")
    lesson_slug = str(lesson_obj.get("slug") or idx)
    name_slug = quote(name.lower().replace(" ", "-").replace("/", "-"))
    url = f"https://{COURSE_HOST}/courses/{course_slug}/lesson/{lesson_slug}/{name_slug}"
    return idx, name, url


def build_specialization_lesson_url(specialization_slug: str, lesson_obj: Dict[str, Any]) -> Tuple[int, str, str, str]:
    """构建专项课程课时查看URL

    Returns:
        Tuple: (idx, name, url, course_name)
    """
    idx = int(lesson_obj.get("index") or 0)
    name = str(lesson_obj.get("name") or f"Lesson {idx}")
    lesson_slug = str(lesson_obj.get("slug") or idx)
    course_name = str(lesson_obj.get("course_name", "Unknown Course"))
    name_slug = quote(name.lower().replace(" ", "-").replace("/", "-"))
    url = f"https://{COURSE_HOST}/specializations/{specialization_slug}/lesson/{lesson_slug}/{name_slug}"
    return idx, name, url, course_name


def run_yt_dlp_download(lesson: Lesson, output_dir: str, threads: int = DEFAULT_THREADS, prefer: str = DEFAULT_QUALITY) -> int:
    """运行yt-dlp下载视频"""
    safe_title = sanitize_filename(lesson.title)
    filename_template = os.path.join(output_dir, f"{lesson.index:02d} - {safe_title}.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--cookies-from-browser", "chrome",
        "--download-archive", os.path.join(output_dir, ".downloaded.txt"),
        "--no-overwrites",
        "--continue",
        "-N", str(threads),
        "-S", prefer,
        "--add-metadata",
        "--merge-output-format", "mp4",
        "-o", filename_template,
        lesson.url,
    ]

    logger.info(f"[下载] {lesson.index:02d}. {lesson.title}")
    logger.info(f"URL: {lesson.url}")

    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except KeyboardInterrupt:
        logger.info("下载被用户中断")
        raise
    except Exception as e:
        logger.error(f"[错误] 调用 yt-dlp 失败: {e}")
        return 1