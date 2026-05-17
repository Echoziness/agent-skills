# 已知限制与注意事项

> 如果你打算基于此 skill 开发或修改，请先阅读本文件。

## 功能限制

1. **字幕只取第一条语言**：`subtitles[0]`，多语种字幕（如中英双语）只拿到第一种。如需多语言，应遍历 `json.data.subtitle.subtitles` 数组。

2. **评论上限硬编码**：主评论最多 5 页（约 100 条），子评论最多 20 条主评论 × 5 条。热门视频覆盖率偏低，可改为参数或动态扩展。

3. **不获取弹幕**：B站弹幕是视频理解的重要维度，当前脚本未涉及。弹幕需要通过 `player/wbi/v2` 之外的接口获取。

4. **不支持多 P 视频**：只处理单页（当前 URL 对应的 P），分 P 视频需遍历 `__INITIAL_STATE__.videoData.pages`。

5. **字幕文本丢失时间戳**：`map(s => s.content).join(' ')` 只拼接纯文本，原始 JSON 中的 `from`/`to` 时间戳信息被丢弃。对做时间线分析的场景不友好。

## 工程层面的坑

6. **`close-all` 会关闭所有 Edge 实例**：包括用户正在使用的浏览器窗口。脚本在退出时（交互模式按 q）会自动执行 `close-all` 清理浏览器。

7. **PowerShell 5.x 下 `Out-File -Encoding utf8` 输出带 BOM**：不影响 JSON 解析，但可能影响下游工具。可改用 `[System.IO.File]::WriteAllText`。

8. **网络错误无重试**：API 请求失败或超时直接 break，没有指数退避重试逻辑。

9. **JS 模板内嵌在 PowerShell here-string 中**：修改 JS 需在 PS1 文件中操作，无语法高亮。独立模板见 `references/step-by-step.md` 底部。

10. **评论 fetch 的 `oid` 依赖元数据提取成功**：如果 `__INITIAL_STATE__` 解析失败导致 `aid` 为空，评论区会静默跳过而非报错。

11. **脚本会在 skill 目录下生成文件**：`scripts/bili-data/`（输出数据）、`scripts/.bili-tmp/`（临时 JS 脚本）、`scripts/.playwright/`（CLI 配置）、`scripts/.playwright-cli/`（浏览器 session）都会留在 skill 目录中。这是 Playwright CLI 文件沙箱限制的无奈之举。脚本退出后可安全清理 `bili-data/`、`.bili-tmp/` 和 `.playwright-cli/`；**注意 `.playwright-cli/` 在浏览器运行时不可删除**（-session 文件是 playwright-cli 定位浏览器实例的依据，删了会报 `Browser is not open`）。`.playwright/` 建议保留（避免每次重新生成配置）。