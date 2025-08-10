## 项目说明
使用 Chrome 登录态与 yt-dlp，批量解析 DeepLearning.AI 短课程的所有“视频课时”，按顺序命名并下载；或仅导出直链 CSV 供其他下载器使用。项目统一通过 uv 管理并执行。

### 目录结构
- `download_course.py`：真实下载脚本（按顺序生成 `NN - 标题.mp4`）
- `download_course.sh`：下载脚本的便捷启动器（使用 uv 运行）
- `scripts/export_csv.py`：仅解析直链并导出 CSV（不下载）
- `export_csv.sh`：CSV 导出便捷启动器（使用 uv 运行）
- `pyproject.toml`：uv 项目配置

### 先决条件（必须）
- 已在本机 Chrome 中登录并可正常播放课程视频（脚本将调用浏览器 Cookie）
- 已安装 uv 与 yt-dlp：
  ```bash
  brew install uv yt-dlp
  ```
  说明：uv 负责运行 Python；yt-dlp 解析直链/下载，二者缺一不可。

### 一、真实下载整门课（通过 uv 执行）
- 用法（包装脚本，内部用 uv 运行）：
  ```bash
  ./download_course.sh "<课程任一课时链接或课程首页链接>"
  ```
  示例：
  ```bash
  ./download_course.sh "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
  ```
- 行为：
  - 自动解析整门课的“视频课时”（跳过阅读材料等非视频）
  - 命名为 `NN - 标题.mp4`，按平台顺序编号
  - 断点续传、跳过已下载：启用 `--continue`、`--no-overwrites`、`--download-archive .downloaded.txt`
  - 默认质量优先级：1080p h264（可调整）
- 可选参数（直接传给脚本）：
  - 并发：`--threads 8`
  - 质量：`--quality "res:1080,codec:h264"`
  - 输出目录：`--out "My Downloads"`
  示例：
  ```bash
  ./download_course.sh --threads 12 --quality "res:1080,codec:h264" --out "Claude Code" \
    "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
  ```

- 仅预览清单（不下载）：
  ```bash
  ./download_course.sh --dry-run "<课程链接>"
  ```

### 二、仅导出直链 CSV（通过 uv 执行，不下载）
- 用法（包装脚本，内部用 uv 运行）：
  ```bash
  ./export_csv.sh "<课程任一课时链接或课程首页链接>"
  ```
- 输出：在项目根目录生成 `videos.csv`
- CSV 格式（满足你工具要求）：
  ```csv
  url,title
  https://example.com/playlist.m3u8,01 - Introduction
  ```
  我额外保留了可选的 `path` 列（空值）；你的工具会忽略多余列。
- 验证（可选）：加 `--verify` 对直链做 HTTP HEAD 校验（不下载）。
  ```bash
  ./export_csv.sh --verify --out videos.csv "<课程链接>"
  ```

### 三、常见问题与排查
- 必须确保 Chrome 已登录：脚本通过 `yt-dlp --cookies-from-browser chrome` 使用浏览器会话来解析直链
- 若解析失败（如 403/需要登录）：
  - 在 Chrome 打开该课时链接并确认能正常播放
  - 更新 yt-dlp：`yt-dlp -U`
  - 重试命令
- 若下载中断：可直接重复执行命令；已启用续传与跳过逻辑，不会重复下载
- 速度/质量：可通过 `--threads`/`--quality` 调整（见上）
 - 多 Chrome 配置文件：若非默认 Profile，请确保登录态在默认 Profile；或参考 yt-dlp 文档指定 Profile（本项目采用默认配置）。

### 四、示例命令（均通过 uv 执行）
- 补齐当前课程剩余视频（推荐执行）：
  ```bash
  ./download_course.sh "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
  ```
- 仅导出 CSV，供其它下载器使用：
  ```bash
  ./export_csv.sh "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/66b35/introduction"
  ```

### 使用声明
- 本项目仅供个人学习与研究使用。
- 请遵守 DeepLearning.AI 等网站的服务条款与版权政策，不得用于商业用途。
- 请勿公开传播或批量分发课程视频、直链或导出的 CSV；相关风险由使用者自行承担。

### 备注
- 直链多为 HLS `.m3u8`，可能带时效签名；请在有效期内使用
- 本项目不会存储你的登录信息；直链解析由 yt-dlp 使用你的浏览器 Cookie 完成
