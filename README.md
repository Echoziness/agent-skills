# Agent Skills

A collection of OpenCode agent skills.

## Available Skills

| Skill | Description |
|-------|-------------|
| [bilibili-reader](skills/bilibili-reader/) | 让 AI "观看" B 站视频——提取 AI 字幕、评论和视频元数据 |
| [simple-video-downloader](skills/simple-video-downloader/) | Video downloader powered by yt-dlp. Supports Bilibili, YouTube, Twitter, Twitch and 1700+ sites. |
| [career-planning-agent](skills/career-planning-agent/) | 通过情景行为证据，为大学生形成可修正的、证据驱动的职业探索假设 |
| [career-scenario-designer](skills/career-scenario-designer/) | 为职业生涯规划设计场景题（通用 S 场景 + 定制 T 场景），配套 career-planning-agent |
| [news](skills/news/) | 整合多源新闻信息，提供深度分析与洞察，不遗落重要新闻与前沿动态 |
| [algo-judge](skills/algo-judge/) | 算法题出题与自动评测，模拟 OJ 系统，支持 7 种语言 |
| [acm-tracker](skills/acm-tracker/) | 算法训练进度追踪，基于行为观察动态更新评估并推荐下一步 |

## Installation

```bash
# Install a specific skill
npx skills add Echoziness/agent-skills@bilibili-reader
npx skills add Echoziness/agent-skills@simple-video-downloader
npx skills add Echoziness/agent-skills@career-planning-agent
npx skills add Echoziness/agent-skills@career-scenario-designer
npx skills add Echoziness/agent-skills@news
npx skills add Echoziness/agent-skills@algo-judge
npx skills add Echoziness/agent-skills@acm-tracker
```

## Adding New Skills

1. Create a folder under `skills/` with your skill name
2. Add `SKILL.md` with proper frontmatter (name, description)
3. Optionally add `references/` for documentation and `scripts/` for executables
4. Push to this repository
