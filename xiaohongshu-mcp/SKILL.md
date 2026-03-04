---
name: xiaohongshu-mcp
description: >
  Automate Xiaohongshu (RedNote) content operations using a Python client for the xiaohongshu-mcp server.
  Use for: (1) Publishing image, text, and video content, (2) Searching for notes and trends,
  (3) Analyzing post details and comments, (4) Managing user profiles and content feeds.
  Triggers: xiaohongshu automation, rednote content, publish to xiaohongshu, xiaohongshu search, social media management.
---

# Xiaohongshu MCP Skill (with Python Client)

Automate content operations on Xiaohongshu (小红书) using a bundled Python script that interacts with the `xpzouying/xiaohongshu-mcp` server (8.4k+ stars).

**Project:** [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)

## 1. Local Server Setup

This skill requires the `xiaohongshu-mcp` server to be running on your local machine.

### Step 1: Download Binaries

Download the appropriate binaries for your system from the [GitHub Releases](https://github.com/xpzouying/xiaohongshu-mcp/releases) page.

| Platform | MCP Server | Login Tool |
| -------- | ---------- | ---------- |
| macOS (Apple Silicon) | `xiaohongshu-mcp-darwin-arm64` | `xiaohongshu-login-darwin-arm64` |
| macOS (Intel) | `xiaohongshu-mcp-darwin-amd64` | `xiaohongshu-login-darwin-amd64` |
| Windows | `xiaohongshu-mcp-windows-amd64.exe` | `xiaohongshu-login-windows-amd64.exe` |
| Linux | `xiaohongshu-mcp-linux-amd64`  |`	xiaohongshu-login-linux-amd64`|

Grant execute permission to the downloaded files:
```shell
chmod +x xiaohongshu-mcp-darwin-arm64 
```

### Step 2: Login (First Time Only)
Run the login tool. It will open a browser window with a QR code. Scan it with your Xiaohongshu mobile app.
```shell
  ./xiaohongshu-login-darwin-arm64
```


> **Important**: Do not log into the same Xiaohongshu account on any other web browser, as this will invalidate the server's session.

### Step 3: Start the MCP Server

Run the MCP server in a separate terminal window. It will run in the background.

```shell
# Run in headless mode (recommended)
./xiaohongshu-mcp-darwin-arm64 

# Or, run with a visible browser for debugging
./xiaohongshu-mcp-darwin-arm64 -headless=false 
```

The server will be available at `http://localhost:18060`.


# yt-dlp Video Downloader

Download videos from thousands of websites using yt-dlp.

## Prerequisites

Before downloading, verify dependencies are installed:

```bash
# Check yt-dlp
which yt-dlp || echo "yt-dlp not installed. Install with: pip install yt-dlp"

# Check ffmpeg (required for audio extraction and format merging)
which ffmpeg || echo "ffmpeg not installed. Install with: brew install ffmpeg"
```

If not installed, install them first:
```bash
pip install yt-dlp
brew install ffmpeg  # macOS
```


## 2. Using the Skill

This skill includes a Python client (`scripts/xhs_client.py`) to interact with the local server. You can use it directly from the shell.

### Available Commands

| Command | Description | Example |
| --- | --- | --- |
| `status` | Check login status | `python scripts/xhs_client.py status` |
| `search <keyword>` | Search for notes | `python scripts/xhs_client.py search "咖啡"` |
| `detail <id> <token>` | Get note details | `python scripts/xhs_client.py detail "note_id" "xsec_token"` |
| `feeds` | Get recommended feed | `python scripts/xhs_client.py feeds` |
| `publish <title> <content> <images>` | Publish an image note | `python scripts/xhs_client.py publish "Title" "Content" "url1,url2"` |
| `publish_video <title> <content> <video>` | Publish a video | `python scripts/xhs_client.py publish_video "Title" "Desc" "/path/to/video.mp4"` |

### Command Options

#### Publish Commands

Both `publish` (image) and `publish_video` (video) support the following options:

| Option | Description | Default |
| --- | --- | --- |
| `--tags` | Comma-separated tags | None |
| `--visibility` | Visibility setting: `公开可见`, `仅自己可见`, `仅互关好友可见` | `公开可见` |

**Examples:**

```shell
# Publish an image note with tags and custom visibility
python scripts/xhs_client.py publish "My Title" "My content here" "http://img1.jpg,http://img2.jpg" --tags "tag1,tag2" --visibility "公开可见"

# Publish a video with tags
python scripts/xhs_client.py publish_video "Video Title" "Video description" "/path/to/video.mp4" --tags "vlog,daily" --visibility "公开可见"
```

**Video Publishing Notes:**
- Only supports local video file paths (absolute path required)
- Video processing may take longer; default timeout is 5 minutes
- Recommended video size: ≤ 1GB
- Supported formats: MP4, MOV, etc.

### Example Workflow: Market Research

1.  **Check Status**: First, ensure the server is running and you are logged in.
    ```shell
    python ~/clawd/skills/xiaohongshu-mcp/scripts/xhs_client.py status
    ```

2.  **Search for a Keyword**: Find notes related to your research topic. The output will include the `feed_id` and `xsec_token` needed for the next step.
    ```shell
    python ~/clawd/skills/xiaohongshu-mcp/scripts/xhs_client.py search "户外电源"
    ```

3.  **Get Note Details**: Use the `feed_id` and `xsec_token` from the search results to get the full content and comments of a specific note.
    ```shell
    python ~/clawd/skills/xiaohongshu-mcp/scripts/xhs_client.py detail "64f1a2b3c4d5e6f7a8b9c0d1" "security_token_here"
    ```

4.  **Analyze**: Review the note's content, comments, and engagement data to gather insights.


### Download with Custom Output Path
视频链接例子:  https://www.xiaohongshu.com/explore/68cd2df7000000001101e113?xsec_token=ABKgAqHdzKHe5mXx40MCU1fsScs7NgslhyRnxCVWux2OI=&xsec_source=pc_search&source=web_explore_feed
```bash
  yt-dlp -P "downloads" \
    -o "%(title)s-%(id)s.%(ext)s" \
    "https://www.xiaohongshu.com/explore/[feed_id]?xsec_token=[token]=&xsec_source=[xsec_source]&source=[source]"
```
 
