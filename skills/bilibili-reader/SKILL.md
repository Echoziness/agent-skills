---
name: bilibili-reader
description: "赋予 AI '观看' Bilibili 视频的能力（仅限 Windows + PowerShell 环境，利用系统预装 Microsoft Edge，无需额外安装浏览器）。基于 Playwright CLI，自动化提取视频的 AI 字幕（视频核心内容）、视频元数据（标题/UP主/播放量等）和结构化评论（主评论+子评论+点赞数）。当用户提供 B站视频链接（含 BV/AV 号），并要求看视频、总结视频内容、阅读视频内容、提取字幕/评论，或分析观点和反应时，必须触发此技能。"
---

# Bilibili Reader

## 快速开始

推荐直接执行便携化脚本 `scripts/br.ps1`，它内置了完整的浏览器管理、登录检测和提取逻辑：

```powershell
.\scripts\br.ps1 -Url 'https://www.bilibili.com/video/BV1xxxxxx/'
# 或交互模式
.\scripts\br.ps1
```

依赖：Node.js 18+、`npm install -g @playwright/cli`（推荐 >= 1.5.0）+ Microsoft Edge（Windows 已预装）+ B站账号（首次需登录）。

## 核心知识：B站数据的三层获取策略

### 1. 视频元数据 → 零成本直读

页面内嵌 `window.__INITIAL_STATE__`，`page.evaluate(() => window.__INITIAL_STATE__)` 一次性拿完。

### 2. AI 字幕 → 必须拦截，不可直连，且需要登录

字幕 URL 来自 `player/wbi/v2`（带 Wbi 动态签名），直连返回 -352。必须用 `page.on('response')` 被动拦截。

**`player/wbi/v2` 仅在用户已登录时返回 AI 字幕**。未登录时 `code: 0` 但 `subtitles: []`。通过 `DedeUserID` cookie 检测登录状态。

### 3. 评论区 → 直连 API，但别用错路径

| API 路径 | 需要签名？ | 说明 |
|---|---|---|
| `reply/main`（不带 `/wbi/`） | 否 | 主评论，cursor 分页 |
| `reply/wbi/main` | 是 | ❌ 别用，直连返回 -403 |
| `reply/reply` | 否 | 子评论，`root`=rpid_str + `pn/ps` 分页 |

所有 `fetch` 必须在 `page.evaluate` 内执行，加 `{ credentials: 'include' }`。

> 完整 API 参数和分页细节见 [references/api-reference.md](references/api-reference.md)

---

## 执行纪律

### JS 脚本层（run-code 沙箱内）

1. 入口必须是 `async (page) => {}`——禁止 `module.exports`
2. `page.evaluate` 里禁止 `require`——没有 Node.js
3. 字幕 URL 只能拦截获取——禁止自算 Wbi 签名
4. 评论用 `reply/main`——不是 `reply/wbi/main`
5. fetch 必须在 `page.evaluate` 内——外层没 Cookie

### 浏览器管理层

6. AI 字幕需登录——未登录时引导用户在浏览器中登录 B站
7. `--profile` 固定路径——否则 `--persistent` 按 CWD 自动生成 profile，换目录丢失登录态
8. 启动前 `close-all`——旧 session 残留会连接错误实例。**但 `close-all` 会关闭所有 Edge 窗口，包括用户正在使用的。执行脚本前必须主动告知用户："启动时会关闭所有 Edge 窗口，请提前保存工作。"**
9. `run-code --filename` 有文件沙箱——只能访问浏览器启动时 CWD 及其子目录
10. 禁止 `Start-Process -WindowStyle Hidden` + `--headed`——浏览器会闪退
11. 浏览器就绪必须轮询——`Start-Process` 立即返回不代表已注册到 daemon

### PowerShell 层

12. UTF-8 编码必须声明（`chcp 65001` + 三行 Encoding 设置）
13. `ConvertFrom-Json` 必须 `-ErrorAction Stop`
14. 禁止套娃 `pwsh -Command`
15. 禁止 `taskkill` 杀浏览器——用 `close-all`

> Playwright CLI 底层行为详解见 [references/playwright-deep-dive.md](references/playwright-deep-dive.md)
> 故障排查见 [references/troubleshooting.md](references/troubleshooting.md)
> 已知限制和注意事项见 [references/caveats.md](references/caveats.md)

---

## 工作流

### 方式 A：直接执行脚本（推荐）

```powershell
.\scripts\br.ps1 -Url '<B站视频链接>'
```

脚本自动处理：目录创建 → 配置生成 → 浏览器启动 → 登录检测 → 数据提取 → 文件输出。

输出到脚本所在目录的 `bili-data/` 子目录（即 `scripts/bili-data/`，完整路径为 `<skill根目录>/scripts/bili-data/`）：`<BVID>_subs.txt`、`<BVID>_comments.json`、`<BVID>_meta.json`。读取结果时注意路径是 `scripts/bili-data/` 而非 skill 根目录。

### 方式 B：手动分步执行

当脚本不可用或需要调试时使用。完整步骤和命令见 [references/step-by-step.md](references/step-by-step.md)。

1. 创建工作目录，写入 `.playwright/cli.config.json`，启动浏览器并等待就绪
2. 将 JS 提取脚本写入工作目录子目录（文件沙箱限制），替换 `__VIDEO_URL__`
3. `playwright-cli run-code --raw --filename <script.js>` 执行
4. PowerShell 解析 JSON，保存三个文件
5. `playwright-cli close-all` 清理浏览器

> ⚠️ `close-all` 会关闭所有 Edge 窗口，执行前务必告知用户保存工作。

### 生成报告

读取输出文件，四维度分析：
1. **视频身份卡**：标题、UP 主、播放量、弹幕数、点赞数
2. **核心提炼**：字幕主旨、脉络、UP 主观点
3. **舆论风向标**：高赞评论代表群体情绪，子评论补充细节
4. **内容与受众匹配度**：传播效果与互动深度分析

评论过长时用 `read` 的 `limit/offset` 分段读。
