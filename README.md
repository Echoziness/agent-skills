# Agent Skills

A collection of OpenCode/Claude agent skills.

## Available Skills

| Skill | Description |
|-------|-------------|
| [simple-video-downloader](simple-video-downloader/) | Video downloader powered by yt-dlp. Supports Bilibili, YouTube, Twitter, Twitch and 1700+ sites. |

## Installation

```bash
# Install a specific skill
npx skills add Echoziness/agent-skills@simple-video-downloader
```

## Adding New Skills

To add a new skill:

1. Create a folder with your skill name
2. Add `SKILL.md` with proper frontmatter (name, description)
3. Optionally add `references/` for documentation
4. Push to this repository
