# Agent Skills

A collection of OpenCode agent skills.

## Available Skills

| Skill | Description |
|-------|-------------|
| [bilibili-reader](skills/bilibili-reader/) | 让 AI "观看" B 站视频——提取 AI 字幕、评论和视频元数据 |
| [simple-video-downloader](skills/simple-video-downloader/) | Video downloader powered by yt-dlp. Supports Bilibili, YouTube, Twitter, Twitch and 1700+ sites. |
| [career-planning-agent](skills/career-planning-agent/) | 通过情景行为证据，为大学生形成可修正的、证据驱动的职业探索假设 |
| [career-scenario-designer](skills/career-scenario-designer/) | 为职业生涯规划设计场景题（通用 S 场景 + 定制 T 场景），配套 career-planning-agent |

## Installation

```bash
# Install a specific skill
npx skills add Echoziness/agent-skills@bilibili-reader
npx skills add Echoziness/agent-skills@simple-video-downloader
npx skills add Echoziness/agent-skills@career-planning-agent
npx skills add Echoziness/agent-skills@career-scenario-designer
```

## Adding New Skills

1. Create a folder under `skills/` with your skill name
2. Add `SKILL.md` with proper frontmatter (name, description)
3. Optionally add `references/` for documentation and `scripts/` for executables
4. Push to this repository
