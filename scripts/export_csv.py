#!/usr/bin/env python3
import argparse
import csv
import json
import os
import subprocess
import sys
from typing import List, Tuple, Dict, Any
from urllib.parse import urlparse

import requests

COURSE_HOST = "learn.deeplearning.ai"


def get_course_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 2 or parts[0] != 'courses':
        raise ValueError("Expect course URL under /courses/<slug> or any lesson under it")
    return parts[1]


def get_outline(course_slug: str) -> Tuple[str, List[Dict[str, Any]]]:
    api = (
        f"https://{COURSE_HOST}/api/trpc/course.getCourseBySlug?"
        f"input=%7B%22json%22%3A%7B%22courseSlug%22%3A%22{course_slug}%22%7D%7D"
    )
    r = requests.get(api, timeout=30)
    r.raise_for_status()
    data = r.json()
    json_obj = data.get("result", {}).get("data", {}).get("json", {})
    title = json_obj.get("name") or course_slug
    lessons_map: Dict[str, Any] = json_obj.get("lessons", {})
    listing: List[Dict[str, Any]] = json_obj.get("listing", [])

    ordered_keys: List[str] = []
    for block in listing or []:
        for item in block.get("content", []) or []:
            if item.get("type") == "lesson" and item.get("key"):
                ordered_keys.append(item["key"]) 

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

    return title, lessons


def extract_direct_url(lesson_url: str) -> str:
    # Use yt-dlp to resolve actual media URL via Chrome cookies without downloading
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "chrome",
        "-g",
        "-f", "bv*+ba/b",
        lesson_url,
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip()}")
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("No URL returned by yt-dlp")
    # Many HLS cases return 1 line (muxed) or 2 lines (separate video/audio). Prefer first.
    return lines[0]


def build_lesson_url(course_slug: str, lesson_obj: Dict[str, Any]) -> Tuple[int, str, str]:
    idx = int(lesson_obj.get("index") or 0)
    name = str(lesson_obj.get("name") or f"Lesson {idx}")
    lesson_slug = str(lesson_obj.get("slug") or idx)
    # Build canonical viewing URL; yt-dlp will resolve to real media URL
    from urllib.parse import quote
    name_slug = quote(name.lower().replace(" ", "-").replace("/", "-"))
    url = f"https://{COURSE_HOST}/courses/{course_slug}/lesson/{lesson_slug}/{name_slug}"
    return idx, name, url


def main():
    parser = argparse.ArgumentParser(description="Export CSV of direct video URLs for a DLAI course (Chrome cookies required)" )
    parser.add_argument("url", help="Any lesson URL under the course, or the course homepage URL")
    parser.add_argument("--out", default="videos.csv", help="Output CSV path (default: videos.csv)")
    parser.add_argument("--verify", action="store_true", help="Verify each URL with a HEAD request after resolving")
    args = parser.parse_args()

    course_slug = get_course_slug(args.url)
    course_title, lessons = get_outline(course_slug)

    rows: List[Dict[str, str]] = []
    for obj in sorted(lessons, key=lambda o: int(o.get("index") or 0)):
        idx, name, view_url = build_lesson_url(course_slug, obj)
        try:
            direct_url = extract_direct_url(view_url)
            if args.verify:
                try:
                    vr = requests.head(direct_url, allow_redirects=True, timeout=15)
                    vr.raise_for_status()
                except Exception:
                    pass
            rows.append({
                "url": direct_url,
                "title": f"{idx:02d} - {name}",
            })
            print(f"[ok] {idx:02d} - {name}")
        except Exception as e:
            print(f"[skip] {idx:02d} - {name}: {e}")

    # Default path column: script execution working directory
    exec_path = os.getcwd()
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "path"])
        writer.writeheader()
        for r in rows:
            writer.writerow({"url": r["url"], "title": r["title"], "path": exec_path})

    print(f"Exported {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
