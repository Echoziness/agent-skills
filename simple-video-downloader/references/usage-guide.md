# yt-dlp Usage Guide

Essential commands and tips for video downloading. Based on yt-dlp functionality.

## Installation

- **PyPI**: `pip install yt-dlp`
- **Windows**: Download `yt-dlp.exe` from [releases](https://github.com/yt-dlp/yt-dlp/releases)
- **macOS**: `brew install yt-dlp`
- **Linux**: Download binary or `pip install yt-dlp`

## Get Video Information

```bash
# View metadata (JSON)
yt-dlp -j <URL>

# List available formats
yt-dlp -F <URL>

# Show detailed info
yt-dlp --dump-json <URL>
```

## Format Selection

```bash
# Best quality (video + audio merged)
-f "bestvideo+bestaudio"

# Specific format
-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

# Audio only
-x --audio-format mp3

# Video only (no audio)
-f bestvideo
```

## Common Options

### Subtitles & Danmaku
```bash
# Download subtitles
--write-subs --sub-lang en

# Download danmaku (Bilibili)
--write-subs --sub-lang danmaku

# Auto-translate subtitles
--write-subs --translate-langs en
```

### Thumbnails
```bash
# Download and embed thumbnail
--write-thumbnail --embed-thumbnail
```

### Metadata
```bash
# Embed metadata
--embed-metadata

# Write description
--write-description
```

### Authentication
```bash
# Use browser cookies (for premium content)
--cookies-from-browser chrome

# Login with credentials
-u username -p password
```

## Output Template

```bash
# Custom filename
-o "%(title)s.%(ext)s"
-o "%(uploader)s/%(title)s.%(ext)s"

# Output directory
-o "_Output/%(title)s.%(ext)s"
```

Available template variables: `id`, `title`, `uploader`, `upload_date`, `duration`, `view_count`, `like_count`, etc.

## Post-Processing

```bash
# Merge video + audio (default)
--merge-output-format mp4

# Embed subtitle into video
--embed-subs

# Add chapters (if available)
--add-chapters
```

## Useful Tips

1. **Check formats first**: Always run `-F` to see what's available
2. **Avoid --split-chapters**: Creates separate files, leaves mess in working directory
3. **Use cookies**: For Bilibili 4K/1080P60, need to use `--cookies-from-browser`
4. **Verify downloads**: Use `ffprobe` to check file integrity

## Supported Sites

yt-dlp supports 1700+ sites including:
- YouTube, Bilibili, Niconico
- Twitter, Instagram, TikTok
- Twitch, Vimeo, Coursera
- Many more...

For full list, see: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
