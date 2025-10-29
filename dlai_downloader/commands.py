"""DeepLearning.AI 课程下载器命令行接口"""
import argparse
import csv
import logging
import os
import sys
from typing import List, Dict, Any

import requests

from .core import (
    get_course_base_url,
    get_course_slug,
    fetch_course_outline_via_api,
    get_outline_for_csv,
    extract_direct_url,
    build_lesson_url,
    run_yt_dlp_download,
    sanitize_filename,
    DEFAULT_THREADS,
    DEFAULT_QUALITY
)

# 配置日志
logger = logging.getLogger(__name__)


def download_main():
    """下载课程视频命令的主函数"""
    parser = argparse.ArgumentParser(description="DeepLearning.AI 课程批量下载器（使用 Chrome 登录态 + yt-dlp）")
    parser.add_argument("url", help="课程任一课时链接，或课程主页链接")
    parser.add_argument("--out", dest="out_dir", default=None, help="输出目录（默认使用课程名创建文件夹）")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS, help=f"分片并发数，默认 {DEFAULT_THREADS}")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help=f"质量/编码排序，传给 yt-dlp 的 -S 参数，默认 {DEFAULT_QUALITY}")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并展示将要下载的清单，不实际下载")

    args = parser.parse_args()

    try:
        # 验证URL
        course_base, course_slug = get_course_base_url(args.url)
        logger.info(f"[解析] 课程主页: {course_base}")

        # 获取课程大纲
        course_title, lessons = fetch_course_outline_via_api(course_slug)
        logger.info(f"[课程] {course_title}")
        logger.info(f"[视频课时数] {len(lessons)}")

        # 显示课程列表
        for lesson in lessons:
            logger.info(f" - {lesson.index:02d}. {lesson.title} -> {lesson.url}")

        if args.dry_run:
            return

        # 创建输出目录
        out_dir = args.out_dir or os.path.join(os.getcwd(), sanitize_filename(course_title))
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"\n[下载目录] {out_dir}")

        # 下载视频
        failures = 0
        for lesson in lessons:
            try:
                code = run_yt_dlp_download(lesson, out_dir, threads=args.threads, prefer=args.quality)
                if code != 0:
                    failures += 1
                    logger.error(f"[失败] {lesson.index:02d}. {lesson.title}")
            except KeyboardInterrupt:
                logger.info("下载被用户中断")
                sys.exit(1)
            except Exception as e:
                failures += 1
                logger.error(f"[失败] {lesson.index:02d}. {lesson.title}: {e}")

        # 显示结果
        if failures:
            logger.error(f"\n完成，但有 {failures} 个课时下载失败。可重试或检查登录态/网络。")
            sys.exit(1)
        else:
            logger.info("\n全部课时已下载完成。")

    except ValueError as e:
        logger.error(f"参数错误: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"运行时错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"未知错误: {e}")
        sys.exit(1)


def export_csv_main():
    """导出CSV清单命令的主函数"""
    parser = argparse.ArgumentParser(description="Export CSV of direct video URLs for a DLAI course (Chrome cookies required)")
    parser.add_argument("url", help="Any lesson URL under the course, or the course homepage URL")
    parser.add_argument("--out", default="videos.csv", help="Output CSV path (default: videos.csv)")
    parser.add_argument("--verify", action="store_true", help="Verify each URL with a HEAD request after resolving")

    args = parser.parse_args()

    try:
        # 验证URL并获取课程信息
        course_slug = get_course_slug(args.url)
        course_title, lessons = get_outline_for_csv(course_slug)

        rows: List[Dict[str, str]] = []
        processed_count = 0
        success_count = 0

        for obj in sorted(lessons, key=lambda o: int(o.get("index") or 0)):
            processed_count += 1
            idx, name, view_url = build_lesson_url(course_slug, obj)

            try:
                direct_url = extract_direct_url(view_url)

                # 验证URL（如果需要）
                if args.verify:
                    try:
                        vr = requests.head(direct_url, allow_redirects=True, timeout=15)
                        vr.raise_for_status()
                    except requests.exceptions.RequestException:
                        logger.warning(f"[警告] {idx:02d} - {name}: URL验证失败")

                rows.append({
                    "url": direct_url,
                    "title": f"{idx:02d} - {name}",
                })
                success_count += 1
                logger.info(f"[成功] {idx:02d} - {name}")

            except RuntimeError as e:
                logger.error(f"[跳过] {idx:02d} - {name}: {e}")
            except Exception as e:
                logger.error(f"[跳过] {idx:02d} - {name}: 未知错误 - {e}")

        # 写入CSV文件
        try:
            exec_path = os.getcwd()
            with open(args.out, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["url", "title", "path"])
                writer.writeheader()
                for r in rows:
                    writer.writerow({"url": r["url"], "title": r["title"], "path": exec_path})

            logger.info(f"导出完成: {success_count}/{processed_count} 个课时已导出到 {args.out}")

        except IOError as e:
            logger.error(f"写入CSV文件失败: {e}")
            sys.exit(1)

    except ValueError as e:
        logger.error(f"参数错误: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"运行时错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"未知错误: {e}")
        sys.exit(1)