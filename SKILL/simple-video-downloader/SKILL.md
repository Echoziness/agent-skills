---
name: simple-video-downloader
description: Video downloader skill powered by yt-dlp. Downloads videos from Bilibili, YouTube, Twitter, Twitch and 1700+ sites. Use when user wants to download videos, extract audio, or get video metadata from any supported platform.
---

# Simple Video Downloader

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) - a powerful open-source video downloader.

## Prerequisites

**This skill requires yt-dlp to be installed.** Before proceeding:

1. Check if yt-dlp is available:
   ```bash
   yt-dlp --version
   ```

2. If not installed, let the user decide how to handle it:
   - Install via: `pip install yt-dlp` or download binary from [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases)
   - If user has no Python, they may prefer alternative approaches (browser extensions, online services, etc.)

**Do not install yt-dlp for the user.** Let them choose their preferred method.

## Workflow

1. **Get info**: Run `yt-dlp -j <URL>` for metadata, `yt-dlp -F <URL>` for available formats
2. **Analyze**: Check resolution, duration, chapters, subtitles/danmaku availability
3. **Ask user**: Use question tool to confirm options
4. **Build command**: Construct and execute the download command

## Common Options

| Option | Purpose |
|--------|---------|
| `-f "bestvideo+bestaudio"` | Best quality video + audio merge |
| `--write-subs --sub-lang danmaku` | Download danmaku (Bilibili) |
| `--write-thumbnail --embed-thumbnail` | Download and embed cover |
| `--embed-metadata` | Embed video metadata |
| `-x --audio-format mp3` | Extract audio as MP3 |
| `--cookies-from-browser chrome` | Use browser cookies for premium content |

## Output

Save to `_Output/` directory:
```
-o "_Output/%(title)s [%(id)s].%(ext)s"
```

## Tips

- **Chapters**: Embedded in video by default. Do NOT use `--split-chapters` (creates messy leftover files)
- **Bilibili**: 4K/1080P60 requires premium membership. Ask about danmaku preference
- **Verify**: Use `ffprobe` to check downloaded file details

## Reference

For detailed yt-dlp options, see: [references/usage-guide.md](references/usage-guide.md)
