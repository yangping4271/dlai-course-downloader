#!/usr/bin/env python3
import argparse
import os
import re
import sys
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
from urllib.parse import urlparse

import requests
# Note: We rely on yt-dlp's --cookies-from-browser=chrome for downloads.
# Python requests here does not require Chrome cookies for metadata API.


COURSE_HOST = "learn.deeplearning.ai"
LESSON_PATH_SEGMENT = "/lesson/"  # kept for reference but not used


@dataclass
class Lesson:
    index: int
    title: str
    url: str


def sanitize_filename(name: str) -> str:
    # Remove/replace problematic characters for cross-platform safety
    name = re.sub(r"[\\/:*?\"<>|]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "lesson"


def get_course_base_url(input_url: str) -> Tuple[str, str]:
    """Given any course lesson URL, return (course_base_url, course_slug)."""
    parsed = urlparse(input_url)
    if parsed.netloc != COURSE_HOST:
        raise ValueError(f"URL host must be {COURSE_HOST}")
    # Expect path like: /courses/<slug>/lesson/<id>/<lesson-slug>
    parts = [p for p in parsed.path.split('/') if p]
    # parts: ['courses', '<slug>', 'lesson', '<id>', '<lesson-slug>']
    if len(parts) < 2 or parts[0] != 'courses':
        raise ValueError("Not a recognized course URL under /courses/<slug>")
    course_slug = parts[1]
    course_base = f"https://{COURSE_HOST}/courses/{course_slug}"
    return course_base, course_slug


def build_session_with_chrome_cookies() -> requests.Session:
    """Build a requests session for metadata fetching.

    Note: We assume Chrome is logged in for actual media downloads via yt-dlp's
    --cookies-from-browser=chrome. For metadata (course outline), public API is
    accessible without cookies, so we do not read browser cookies here.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://{COURSE_HOST}/",
    })
    return session


def fetch_course_outline_via_api(course_slug: str) -> Tuple[str, List['Lesson']]:
    """Use public tRPC endpoint to get course and ordered lessons; only include videos."""
    session = build_session_with_chrome_cookies()
    api = (
        f"https://{COURSE_HOST}/api/trpc/course.getCourseBySlug?"
        f"input=%7B%22json%22%3A%7B%22courseSlug%22%3A%22{course_slug}%22%7D%7D"
    )
    resp = session.get(api, timeout=30)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    json_obj = data.get("result", {}).get("data", {}).get("json", {})
    course_title: str = json_obj.get("name") or course_slug
    lessons_map: Dict[str, Any] = json_obj.get("lessons", {})
    listing: List[Dict[str, Any]] = json_obj.get("listing", [])

    ordered_keys: List[str] = []
    for block in listing or []:
        for item in block.get("content", []) or []:
            if item.get("type") == "lesson" and item.get("key"):
                ordered_keys.append(item["key"]) 

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


def run_yt_dlp_download(lesson: Lesson, output_dir: str, threads: int = 8, prefer: str = "res:1080,codec:h264") -> int:
    safe_title = sanitize_filename(lesson.title)
    filename_template = os.path.join(output_dir, f"{lesson.index:02d} - {safe_title}.%(ext)s")

    cmd = [
        "yt-dlp",
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

    print(f"[下载] {lesson.index:02d}. {lesson.title}\nURL: {lesson.url}")
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"[错误] 调用 yt-dlp 失败: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="DeepLearning.AI 课程批量下载器（使用 Chrome 登录态 + yt-dlp）")
    parser.add_argument("url", help="课程任一课时链接，或课程主页链接")
    parser.add_argument("--out", dest="out_dir", default=None, help="输出目录（默认使用课程名创建文件夹）")
    parser.add_argument("--threads", type=int, default=8, help="分片并发数，默认 8")
    parser.add_argument("--quality", default="res:1080,codec:h264", help="质量/编码排序，传给 yt-dlp 的 -S 参数")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并展示将要下载的清单，不实际下载")

    args = parser.parse_args()

    course_base, course_slug = get_course_base_url(args.url)

    print(f"[解析] 课程主页: {course_base}")
    course_title, lessons = fetch_course_outline_via_api(course_slug)

    print(f"[课程] {course_title}")
    print(f"[视频课时数] {len(lessons)}\n")

    for lesson in lessons:
        print(f" - {lesson.index:02d}. {lesson.title} -> {lesson.url}")

    if args.dry_run:
        return

    out_dir = args.out_dir or sanitize_filename(course_title)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n[下载目录] {out_dir}\n")

    failures = 0
    for lesson in lessons:
        code = run_yt_dlp_download(lesson, out_dir, threads=args.threads, prefer=args.quality)
        if code != 0:
            failures += 1
            print(f"[失败] {lesson.index:02d}. {lesson.title}")

    if failures:
        print(f"\n完成，但有 {failures} 个课时下载失败。可重试或检查登录态/网络。")
        sys.exit(1)
    else:
        print("\n全部课时已下载完成。")


if __name__ == "__main__":
    main()
