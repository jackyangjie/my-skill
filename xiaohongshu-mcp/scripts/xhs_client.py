#!/usr/bin/env python3
"""
Xiaohongshu MCP Client - A Python client for xiaohongshu-mcp HTTP API.

Usage:
    python xhs_client.py <command> [options]

Commands:
    status                              Check login status
    search <keyword>                    Search notes by keyword
    detail <feed_id> <xsec_token>       Get note details
    feeds                               Get recommended feed list
    publish <title> <content> <images>  Publish a note (image)
    publish_video <title> <content> <video>  Publish a video
    published                           List published videos history

Examples:
    python xhs_client.py status
    python xhs_client.py search "咖啡推荐"
    python xhs_client.py detail "abc123" "token456"
    python xhs_client.py feeds
    python xhs_client.py publish "标题" "内容" "http://img1.jpg,http://img2.jpg" --tags "标签1,标签2"
    python xhs_client.py publish_video "视频标题" "视频描述" "/path/to/video.mp4" --tags "标签1,标签2"
    python xhs_client.py published
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime

BASE_URL = "http://localhost:18060"
TIMEOUT = 60

# Published videos record file (in workspace)
# Script is at: ~/.openclaw/workspace/skills/xiaohongshu-mcp/scripts/xhs_client.py
# Record file should be at: ~/.openclaw/workspace/xiaohongshu_published.json
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
RECORD_FILE = os.path.join(WORKSPACE_DIR, "xiaohongshu_published.json")


def load_published_records():
    """Load published video records from file."""
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_published_records(records):
    """Save published video records to file."""
    try:
        with open(RECORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"⚠️  Warning: Could not save publish record: {e}")
        return False


def is_video_published(feed_id):
    """Check if a video has already been published."""
    records = load_published_records()
    return feed_id in records


def add_published_record(feed_id, title, video_path, status="success"):
    """Add a video to the published records."""
    records = load_published_records()
    records[feed_id] = {
        "title": title,
        "video_path": video_path,
        "published_at": datetime.now().isoformat(),
        "status": status
    }
    save_published_records(records)


def format_datetime(iso_string):
    """Format ISO datetime string to readable format with date."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_string


def list_published_videos(limit=20):
    """List recently published videos."""
    records = load_published_records()
    if not records:
        print("📭 No published videos found.")
        return
    
    print(f"📚 Published Videos ({len(records)} total):\n")
    # Sort by published time, newest first
    sorted_records = sorted(
        records.items(),
        key=lambda x: x[1].get('published_at', ''),
        reverse=True
    )[:limit]
    
    for i, (feed_id, info) in enumerate(sorted_records, 1):
        published_at = format_datetime(info.get('published_at', ''))
        print(f"[{i}] {info.get('title', 'Unknown')}")
        print(f"    Feed ID: {feed_id}")
        print(f"    Published: {published_at}")
        print(f"    Status: {info.get('status', 'Unknown')}")
        print()


def sanitize_text(text):
    """Sanitize text to avoid JSON parsing issues."""
    if not isinstance(text, str):
        return text
    # Replace problematic characters that might cause JSON parsing issues
    # Keep basic emojis but normalize whitespace
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove control characters except newline and tab
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return text.strip()


def truncate_title(title, max_length=20):
    """Truncate title to fit Xiaohongshu's limit (default 20 chars)."""
    if len(title) <= max_length:
        return title
    # Try to truncate at a sensible point, leaving room for ellipsis
    truncated = title[:max_length-1]
    # Don't cut off in the middle of an emoji (rough check)
    while len(truncated) > 0 and ord(truncated[-1]) > 127 and len(truncated.encode('utf-8')) > max_length * 3:
        truncated = truncated[:-1]
        if len(truncated) <= max_length - 2:
            break
    return truncated + "…"


def check_status():
    """Check login status."""
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/login/status", timeout=TIMEOUT)
        data = resp.json()
        if data.get("success"):
            login_info = data.get("data", {})
            if login_info.get("is_logged_in"):
                print(f"✅ Logged in as: {login_info.get('username', 'Unknown')}")
            else:
                print("❌ Not logged in. Please run the login tool first.")
        else:
            print(f"❌ Error: {data.get('error', 'Unknown error')}")
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server. Make sure xiaohongshu-mcp is running on localhost:18060")
        sys.exit(1)


def search_notes(keyword, sort_by="综合", note_type="不限", publish_time="不限"):
    """Search notes by keyword with optional filters."""
    try:
        payload = {
            "keyword": keyword,
            "filters": {
                "sort_by": sort_by,
                "note_type": note_type,
                "publish_time": publish_time
            }
        }
        resp = requests.post(
            f"{BASE_URL}/api/v1/feeds/search",
            json=payload,
            timeout=TIMEOUT
        )
        data = resp.json()
        
        if data.get("success"):
            feeds = data.get("data", {}).get("feeds", [])
            records = load_published_records()
            
            print(f"🔍 Found {len(feeds)} notes for '{keyword}':\n")
            
            for i, feed in enumerate(feeds, 1):
                note_card = feed.get("noteCard", {})
                user = note_card.get("user", {})
                interact = note_card.get("interactInfo", {})
                feed_id = feed.get('id', '')
                
                # Check if already published
                status_mark = "✓" if feed_id in records else " "
                
                print(f"[{status_mark}] [{i}] {note_card.get('displayTitle', 'No title')}")
                print(f"      Author: {user.get('nickname', 'Unknown')}")
                print(f"      Likes: {interact.get('likedCount', '0')} | Collects: {interact.get('collectedCount', '0')} | Comments: {interact.get('commentCount', '0')}")
                print(f"      feed_id: {feed_id}")
                print(f"      xsec_token: {feed.get('xsecToken')}")
                print()
        else:
            print(f"❌ Search failed: {data.get('error', 'Unknown error')}")
        
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server.")
        sys.exit(1)


def get_note_detail(feed_id, xsec_token, load_comments=False):
    """Get detailed information about a specific note."""
    try:
        payload = {
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "load_all_comments": load_comments
        }
        resp = requests.post(
            f"{BASE_URL}/api/v1/feeds/detail",
            json=payload,
            timeout=TIMEOUT
        )
        data = resp.json()
        
        if data.get("success"):
            note_data = data.get("data", {}).get("data", {})
            note = note_data.get("note", {})
            comments = note_data.get("comments", {})
            
            print(f"📝 Note Details:\n")
            print(f"Title: {note.get('title', 'No title')}")
            print(f"Author: {note.get('user', {}).get('nickname', 'Unknown')}")
            print(f"Location: {note.get('ipLocation', 'Unknown')}")
            print(f"\nContent:\n{note.get('desc', 'No content')}\n")
            
            interact = note.get("interactInfo", {})
            print(f"Likes: {interact.get('likedCount', '0')} | Collects: {interact.get('collectedCount', '0')} | Comments: {interact.get('commentCount', '0')}")
            
            comment_list = comments.get("list", [])
            if comment_list:
                print(f"\n💬 Top Comments ({len(comment_list)}):")
                for c in comment_list[:5]:
                    user_info = c.get("userInfo", {})
                    print(f"  - {user_info.get('nickname', 'Anonymous')}: {c.get('content', '')}")
        else:
            print(f"❌ Failed to get details: {data.get('error', 'Unknown error')}")
        
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server.")
        sys.exit(1)


def get_feeds():
    """Get recommended feed list."""
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/feeds/list", timeout=TIMEOUT)
        data = resp.json()
        
        if data.get("success"):
            feeds = data.get("data", {}).get("feeds", [])
            records = load_published_records()
            
            print(f"📋 Recommended Feeds ({len(feeds)} notes):\n")
            
            for i, feed in enumerate(feeds, 1):
                note_card = feed.get("noteCard", {})
                user = note_card.get("user", {})
                interact = note_card.get("interactInfo", {})
                feed_id = feed.get('id', '')
                
                # Check if already published
                status_mark = "✓" if feed_id in records else " "
                
                print(f"[{status_mark}] [{i}] {note_card.get('displayTitle', 'No title')}")
                print(f"      Author: {user.get('nickname', 'Unknown')}")
                print(f"      Likes: {interact.get('likedCount', '0')}")
                print()
        else:
            print(f"❌ Failed to get feeds: {data.get('error', 'Unknown error')}")
        
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server.")
        sys.exit(1)


def publish_note(title, content, images, tags=None, visibility="公开可见"):
    """Publish a new note (image post)."""
    try:
        # Sanitize inputs
        title = sanitize_text(title)
        content = sanitize_text(content)
        
        # Check and truncate title length
        original_title = title
        title = truncate_title(title, max_length=20)
        if len(original_title) > 20:
            print(f"⚠️  Title too long ({len(original_title)} chars), truncated to: {title}")
        
        payload = {
            "title": title,
            "content": content,
            "images": images if isinstance(images, list) else [img.strip() for img in images.split(",") if img.strip()],
            "visibility": visibility
        }
        if tags:
            if isinstance(tags, str):
                tag_list = [sanitize_text(t.strip()) for t in tags.split(",") if t.strip()]
            else:
                tag_list = [sanitize_text(str(t)) for t in tags if t]
            if tag_list:
                payload["tags"] = tag_list
        
        resp = requests.post(
            f"{BASE_URL}/api/v1/publish",
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"❌ Server returned invalid JSON (status {resp.status_code}):")
            print(f"   Response: {resp.text[:200]}")
            return {"success": False, "error": f"Invalid JSON response: {resp.status_code}"}
        
        if data.get("success"):
            print(f"✅ Note published successfully!")
            print(f"   Post ID: {data.get('data', {}).get('post_id', 'Unknown')}")
        else:
            print(f"❌ Publish failed: {data.get('error', 'Unknown error')}")
        
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server.")
        sys.exit(1)


def publish_video(title, content, video_path, feed_id=None, tags=None, visibility="公开可见"):
    """
    Publish a video to Xiaohongshu.
    
    Args:
        title: Video title (required, max 20 chars)
        content: Video description/content (required)
        video_path: Absolute path to local video file (required)
        feed_id: Original feed ID for duplicate checking (optional)
        tags: List of tags (optional)
        visibility: Visibility setting - 公开可见(default), 仅自己可见, 仅互关好友可见
    
    Note:
        - Only supports local video file paths, not HTTP URLs
        - Video processing may take longer, please be patient
        - Recommended video size: <= 1GB
        - Title will be auto-truncated if超过20 characters
    """
    try:
        # Check if already published (if feed_id provided)
        if feed_id and is_video_published(feed_id):
            print(f"⚠️  This video has already been published!")
            print(f"   Feed ID: {feed_id}")
            record = load_published_records().get(feed_id, {})
            print(f"   Published at: {record.get('published_at', 'Unknown')}")
            print(f"   Title: {record.get('title', 'Unknown')}")
            return {"success": False, "error": "Video already published", "already_published": True}
        
        # Sanitize inputs to prevent JSON parsing errors
        title = sanitize_text(title)
        content = sanitize_text(content)
        
        # Check and truncate title length (Xiaohongshu limit is 20 chars)
        original_title = title
        title = truncate_title(title, max_length=20)
        if len(original_title) > 20:
            print(f"⚠️  Title too long ({len(original_title)} chars), truncated to: {title}")
        
        payload = {
            "title": title,
            "content": content,
            "video": video_path,
            "visibility": visibility
        }
        if tags:
            # Ensure tags is a list of strings
            if isinstance(tags, str):
                tag_list = [sanitize_text(t.strip()) for t in tags.split(",") if t.strip()]
            else:
                tag_list = [sanitize_text(str(t)) for t in tags if t]
            if tag_list:
                payload["tags"] = tag_list
        
        print(f"⏳ Uploading video, this may take a while...")
        print(f"   Title: {title}")
        
        resp = requests.post(
            f"{BASE_URL}/api/v1/publish_video",
            json=payload,
            timeout=300,  # Longer timeout for video upload
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        # Handle non-JSON responses
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"❌ Server returned invalid JSON (status {resp.status_code}):")
            print(f"   Response: {resp.text[:200]}")
            return {"success": False, "error": f"Invalid JSON response: {resp.status_code}"}
        
        if data.get("success"):
            print(f"✅ Video published successfully!")
            print(f"   Post ID: {data.get('data', {}).get('post_id', 'Unknown')}")
            print(f"   Status: {data.get('data', {}).get('status', 'Unknown')}")
            
            # Save to published records if feed_id provided
            if feed_id:
                add_published_record(feed_id, title, video_path, status="success")
                print(f"📚 Saved to publish history (Feed ID: {feed_id})")
        else:
            error_msg = data.get('error', 'Unknown error')
            print(f"❌ Video publish failed: {error_msg}")
            # Print request details for debugging
            print(f"\n📋 Debug info:")
            print(f"   Payload keys: {list(payload.keys())}")
            print(f"   Title length: {len(title)} chars")
            print(f"   Content length: {len(content)} chars")
        
        return data
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Xiaohongshu MCP Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # status command
    subparsers.add_parser("status", help="Check login status")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search notes")
    search_parser.add_argument("keyword", help="Search keyword")
    search_parser.add_argument("--sort", default="综合", 
                               choices=["综合", "最新", "最多点赞", "最多评论", "最多收藏"],
                               help="Sort by")
    search_parser.add_argument("--type", default="不限",
                               choices=["不限", "视频", "图文"],
                               help="Note type")
    search_parser.add_argument("--time", default="不限",
                               choices=["不限", "一天内", "一周内", "半年内"],
                               help="Publish time")
    search_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    # detail command
    detail_parser = subparsers.add_parser("detail", help="Get note details")
    detail_parser.add_argument("feed_id", help="Feed ID")
    detail_parser.add_argument("xsec_token", help="Security token")
    detail_parser.add_argument("--comments", action="store_true", help="Load all comments")
    detail_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    # feeds command
    feeds_parser = subparsers.add_parser("feeds", help="Get recommended feeds")
    feeds_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    # published command (new)
    published_parser = subparsers.add_parser("published", help="List published videos history")
    published_parser.add_argument("--limit", type=int, default=20, help="Maximum number of records to show")
    
    # publish command (image)
    publish_parser = subparsers.add_parser("publish", help="Publish an image note")
    publish_parser.add_argument("title", help="Note title (max 20 chars)")
    publish_parser.add_argument("content", help="Note content")
    publish_parser.add_argument("images", help="Image URLs (comma-separated)")
    publish_parser.add_argument("--tags", help="Tags (comma-separated)")
    publish_parser.add_argument("--visibility", default="公开可见",
                                choices=["公开可见", "仅自己可见", "仅互关好友可见"],
                                help="Visibility setting (default: 公开可见)")
    
    # publish_video command
    video_parser = subparsers.add_parser("publish_video", help="Publish a video")
    video_parser.add_argument("title", help="Video title (max 20 chars, will be auto-truncated)")
    video_parser.add_argument("content", help="Video description")
    video_parser.add_argument("video", help="Local video file path (absolute path)")
    video_parser.add_argument("--feed-id", help="Original feed ID for duplicate checking")
    video_parser.add_argument("--tags", help="Tags (comma-separated)")
    video_parser.add_argument("--visibility", default="公开可见",
                              choices=["公开可见", "仅自己可见", "仅互关好友可见"],
                              help="Visibility setting (default: 公开可见)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "status":
        result = check_status()
    elif args.command == "search":
        result = search_notes(args.keyword, args.sort, args.type, args.time)
        if hasattr(args, 'json') and args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "detail":
        result = get_note_detail(args.feed_id, args.xsec_token, args.comments)
        if hasattr(args, 'json') and args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "feeds":
        result = get_feeds()
        if hasattr(args, 'json') and args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "published":
        list_published_videos(limit=args.limit)
    elif args.command == "publish":
        images = args.images.split(",")
        tags = args.tags.split(",") if args.tags else None
        result = publish_note(args.title, args.content, images, tags, args.visibility)
    elif args.command == "publish_video":
        tags = args.tags.split(",") if args.tags else None
        result = publish_video(args.title, args.content, args.video, args.feed_id, tags, args.visibility)


if __name__ == "__main__":
    main()
