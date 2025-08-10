# DLAI Course Downloader (uv + yt-dlp)

Download all video lessons of a DeepLearning.AI short course using your Chrome login session, or export a CSV of direct video URLs for use with other downloaders. The scripts are path-independent and can be executed from any working directory.

For a Chinese guide, see: [README.zh-CN.md](README.zh-CN.md)

## Requirements
- Chrome is logged in and can play the target course videos
- uv and yt-dlp are installed
  ```bash
  brew install uv yt-dlp
  ```

## What you get
- `download_course.sh` – downloads the whole course in order as `NN - Title.mp4`
- `export_csv.sh` – exports a CSV with direct URLs (no download)
- Internals: `download_course.py`, `scripts/export_csv.py`, `pyproject.toml`

## Usage

### 1) Download the entire course (shell script)
Run the script from any directory. Files are saved to your current working directory as `<CWD>/<Course Name>/NN - Title.mp4`.

```bash
/path/to/project/download_course.sh "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

Options (append after the URL or before it):
- `--threads 8` – parallel segments (default 8)
- `--quality "res:1080,codec:h264"` – yt-dlp sort order
- `--out "/custom/output/dir"` – custom destination root directory
- `--dry-run` – only print the list to be downloaded (no download)

Behavior:
- Resolves the full course outline via the public API; downloads only video-type lessons
- Skips already-downloaded items and supports resume (`--continue`, `--no-overwrites`, `--download-archive .downloaded.txt`)
- Uses your Chrome session via `yt-dlp --cookies-from-browser chrome`

Example:
```bash
/path/to/project/download_course.sh \
  --threads 12 --quality "res:1080,codec:h264" \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

### 2) Export CSV of direct URLs (no download)
Outputs `videos.csv` into your current working directory. CSV columns: `url,title,path`. The `path` column defaults to the current working directory; other tools may ignore it.

```bash
/path/to/project/export_csv.sh "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

Optional verification:
```bash
/path/to/project/export_csv.sh --verify --out videos.csv \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

## Notes and troubleshooting
- Ensure Chrome is logged in and can play the lesson in a normal browser tab
- Update yt-dlp if extraction fails: `yt-dlp -U`
- Re-run the same command to resume interrupted downloads; the archive file prevents re-downloading completed items
- If you use a non-default Chrome profile, make sure the logged-in profile is the default one used by `yt-dlp --cookies-from-browser chrome`

## Usage notice
- This project is for personal learning and research only
- Respect the Terms of Service and copyright policies of DeepLearning.AI and related websites
- Do not distribute videos, direct links, or exported CSV publicly; you assume all associated risks
