# DLAI Course Downloader

Download all video lessons of a DeepLearning.AI short course using your Chrome login session, or export a CSV of direct video URLs for use with other downloaders.

## Requirements

- Chrome is logged in and can play the target course videos
- uv is installed
  ```bash
  brew install uv
  ```

## Installation

Install as a uv tool to get system-wide commands:

```bash
uv tool install -e .
```

This provides two commands:
- `dl-download` - Download course videos
- `dl-export-csv` - Export CSV of video URLs

## Usage

### 1) Download the entire course

```bash
dl-download "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

Options:
- `--threads 8` – parallel segments (default 8)
- `--quality "res:1080,codec:h264"` – yt-dlp sort order
- `--out "/custom/output/dir"` – custom destination root directory
- `--dry-run` – only print the list to be downloaded (no download)

Behavior:
- Resolves the full course outline via the public API; downloads only video-type lessons
- Skips already-downloaded items and supports resume
- Uses your Chrome session via `yt-dlp --cookies-from-browser chrome`

Example:
```bash
dl-download \
  --threads 12 --quality "res:1080,codec:h264" \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

### 2) Export CSV of direct URLs

Outputs `videos.csv` into your current working directory. CSV columns: `url,title,path`.

```bash
dl-export-csv "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

Optional verification:
```bash
dl-export-csv --verify --out videos.csv \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

## Project Structure

```
dlai-course-downloader/
├── dlai_downloader/
│   ├── __init__.py          # Package initialization
│   ├── core.py              # Core functionality and data handling
│   └── commands.py          # Command line interfaces
├── pyproject.toml           # Project configuration and dependencies
└── README.md               # This file
```

## Notes and troubleshooting

- Ensure Chrome is logged in and can play the lesson in a normal browser tab
- If extraction fails, try updating yt-dlp with `uv tool install --reinstall dlai-course-downloader`
- Re-run the same command to resume interrupted downloads; the archive file prevents re-downloading completed items
- If you use a non-default Chrome profile, make sure the logged-in profile is the default one used by yt-dlp's `--cookies-from-browser chrome`

## Uninstall

To remove the installed commands:

```bash
uv tool uninstall dlai-course-downloader
```

## Usage notice

- This project is for personal learning and research only
- Respect the Terms of Service and copyright policies of DeepLearning.AI and related websites
- Do not distribute videos, direct links, or exported CSV publicly; you assume all associated risks