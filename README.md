# Agent Skills

A collection of OpenCode agent skills.

## Available Skills

| Skill | Description |
|-------|-------------|
| [bilibili-reader](skills/bilibili-reader/) | 让 AI "观看" B 站视频——提取 AI 字幕、评论和视频元数据 |
| [simple-video-downloader](skills/simple-video-downloader/) | Video downloader powered by yt-dlp. Supports Bilibili, YouTube, Twitter, Twitch and 1700+ sites. |

## Installation

```bash
# Install a specific skill
npx skills add Echoziness/agent-skills@bilibili-reader
npx skills add Echoziness/agent-skills@simple-video-downloader
```

## Adding New Skills

1. Create a folder under `skills/` with your skill name
2. Add `SKILL.md` with proper frontmatter (name, description)
3. Optionally add `references/` for documentation and `scripts/` for executables
4. Push to this repository
