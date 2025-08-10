# DLAI 课程下载工具（uv + yt-dlp）

使用 Chrome 登录态与 yt-dlp 批量解析 DeepLearning.AI 短课程的全部“视频课时”，按顺序命名下载；或仅导出直链 CSV 供其他工具使用。脚本为路径无关（path-independent），可在任意工作目录执行。

英文文档请见：README.md

## 先决条件
- 本机 Chrome 已登录且可正常播放目标课程视频
- 已安装 uv 与 yt-dlp
  ```bash
  brew install uv yt-dlp
  ```

## 你会得到
- `download_course.sh` – 下载整门课程，输出为 `NN - 标题.mp4`
- `export_csv.sh` – 导出直链 CSV（不下载）
- 其它：`download_course.py`、`scripts/export_csv.py`、`pyproject.toml`

## 使用方法

### 1) 下载整门课（Shell 脚本）
可在任意目录执行。保存路径默认是当前工作目录：`<CWD>/<课程名>/NN - 标题.mp4`。

```bash
/path/to/project/download_course.sh "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

可选参数：
- `--threads 8` – 分片并发（默认 8）
- `--quality "res:1080,codec:h264"` – yt-dlp 排序
- `--out "/自定义/输出目录"` – 自定义保存根目录
- `--dry-run` – 仅打印清单，不下载

行为说明：
- 通过公开 API 解析整门课，且只下载“视频”类型的课时
- 跳过已完成并支持续传（`--continue`、`--no-overwrites`、`--download-archive .downloaded.txt`）
- 通过 `yt-dlp --cookies-from-browser chrome` 使用你的浏览器会话解析直链

示例：
```bash
/path/to/project/download_course.sh \
  --threads 12 --quality "res:1080,codec:h264" \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

### 2) 仅导出直链 CSV（不下载）
会在当前工作目录生成 `videos.csv`，列包含：`url,title,path`。其中 `path` 默认填充为当前工作目录；你的下载器可忽略此列。

```bash
/path/to/project/export_csv.sh "https://learn.deeplearning.ai/courses/<course>/lesson/<id>/<slug>"
```

可选校验：
```bash
/path/to/project/export_csv.sh --verify --out videos.csv \
  "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
```

## 注意与排查
- 确保 Chrome 已登录并能直接播放对应课时
- 解析失败可尝试更新 yt-dlp：`yt-dlp -U`
- 中断后可直接重试；凭归档文件避免重复下载
- 若使用非默认 Chrome Profile，确保登录态在默认 Profile 上（或参考 yt-dlp 文档指定）

## 使用声明
- 本项目仅供个人学习与研究使用
- 请遵守 DeepLearning.AI 等网站的服务条款与版权政策，不得用于商业用途
- 请勿公开传播或批量分发课程视频、直链或导出的 CSV；相关风险由使用者自行承担
