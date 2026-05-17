# 常见故障排查

## 1. `ReferenceError: module is not defined`

**原因**：脚本入口写成了 `module.exports = ...`。

**解决**：改为 `async (page) => { ... }`。Playwright CLI 的 `run-code` 要求传入一个 async 函数。

## 2. `ConvertFrom-Json: Unexpected character`

**原因**：`--raw` 输出里混入了非 JSON 文本，通常来自脚本异常堆栈。

**解决**：检查 JS 脚本是否有语法错误，确保所有可能抛异常的代码都被 `try/catch` 包裹。

## 3. 评论区返回空数组或 `code: -403`

三种可能原因，按优先级排查：

### 3a. 用了带签名的 API 路径
主评论必须用 `reply/main`（不带 `/wbi/`），不能用 `reply/wbi/main`。后者需要 Wbi 签名，直连返回 -403。

检查你的 URL：应该是 `api.bilibili.com/x/v2/reply/main?...`，**不是** `api.bilibili.com/x/v2/reply/wbi/main?...`。

### 3b. fetch 缺少 credentials 参数
`page.evaluate` 中的 `fetch` 必须带 `{ credentials: 'include' }`，否则没有 Cookie，API 会拒绝。

```javascript
// 正确
const res = await fetch(url, { credentials: 'include' });

// 错误（没有 Cookie）
const res = await fetch(url);
```

### 3c. oid 为空或不正确
`oid` 必须是视频的 `aid`（纯数字），不是 `bvid`。确认 `videoMeta.aid` 已正确从 `__INITIAL_STATE__` 中提取。

## 4. 字幕为空或显示"无字幕"

### 4a. 视频确实没有 AI 字幕
部分视频 UP 主未上传字幕且 B 站 AI 未生成字幕，此时属正常情况。

### 4b. 拦截时机不对
字幕接口返回较慢，`waitForTimeout(4000)` 可能不够。增加到 6000ms，或在 `page.goto` 之前就注册 `responseHandler`（推荐做法，模板中已是如此）。

## 5. `playwright-cli run-code --raw` 返回 `null` 或空输出

### 5a. JS 脚本没有 return
脚本必须以 `return { ... }` 结尾，返回一个包含结果的对象。如果忘了 `return` 或中途 `return` 了 `undefined`，CLI 会输出 `null`。

### 5b. 套娃使用了 pwsh -Command
在 PowerShell 中错误地用了 `pwsh -Command "...$scriptPath..."`，导致变量被提前展开。直接执行 `.ps1` 脚本即可。

## 6. 评论区只有 20 条，没有更多

**原因**：cursor 分页的 `next_offset` 没有正确传递。

**检查点**：
- 第一页的 offset 为空字符串 `""`，不是 `null`
- 后续页使用上一页返回的 `pagination_reply.next_offset`
- `encodeURIComponent(JSON.stringify({offset: nextOffsetValue}))` 必须正确编码

**调试**：在 `page.evaluate` 内加一行 `console.log('nextOffset:', nextOffset)` 检查游标值。

## 7. 子评论为空

**原因**：`root` 参数类型错误或 `oid` 不正确。

**检查点**：
- `root` 必须使用 `rpid_str`（字符串类型），不能用 `rpid`（数字类型）
- `oid` 使用 `aid`（纯数字视频ID），不能用 `bvid`

## 8. 中文乱码

**原因**：PowerShell 终端编码不是 UTF-8。

**解决**：执行脚本前必须设置：

```powershell
chcp 65001 >$null
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

模板中已包含这三行，不要删除。

## 9. 字幕 URL 拦截不到

**原因**：视频还没开始播放，播放器初始化请求尚未发出。

**解决**：确保在 `page.goto` **之前**就注册 `responseHandler`，不要放到 `goto` 之后。模板中的顺序是：

```javascript
page.on('response', responseHandler);  // 先注册
await page.goto(videoUrl, ...);          // 再导航
```

如果视频需要手动点击播放，可以在 `goto` 后加一句：

```javascript
await page.click('button.bilibili-player-video-btn-start').catch(() => {});
```

## 10. `player/wbi/v2` 返回成功但字幕列表为空

**现象**：API 返回 `code: 0`，但 `data.subtitle.subtitles` 为空数组。拦截逻辑正常，URL 也匹配，就是没有字幕。

**根因**：B站 AI 字幕**仅在用户已登录时返回**。未登录状态下 API 不报错，只是不返回 AI 字幕。

**验证方法**：

```javascript
async (page) => {
    const cookies = await page.context().cookies('https://www.bilibili.com');
    return { hasLogin: cookies.some(c => c.name === 'DedeUserID') };
}
```

**解决**：
1. 用 `--headed` 模式启动浏览器（让用户能看到窗口）
2. 检测到未登录时，导航到 `https://passport.bilibili.com/login`，提示用户手动登录
3. 用 `--profile` 参数固定 profile 路径（如 `$env:LOCALAPPDATA\bili-reader-profile`），避免每次换目录都需要重新登录

## 11. `File access denied: outside allowed roots`

**现象**：

```
Error: File access denied: C:\some\path\script.js is outside allowed roots.
Allowed roots: C:\original\cwd\.playwright-cli, C:\original\cwd
```

**根因**：`run-code --filename` 有文件沙箱，只能访问**浏览器启动时的 CWD 及其子目录**。如果浏览器从目录 A 启动，但脚本文件在目录 B，就会被拒绝。

**解决**：
- 确保浏览器和 `run-code` 在同一个 CWD 下执行
- 或将 JS 脚本写在浏览器启动时 CWD 的子目录下

## 12. 浏览器启动后立即关闭（headed 模式）

**现象**：`Start-Process` 返回了 PID，但 `playwright-cli list` 显示 `status: closed`。

**根因**：PowerShell 的 `Start-Process -WindowStyle Hidden` 与 `--headed` 参数冲突。headed 浏览器需要窗口消息循环，隐藏窗口会导致进程异常退出。

**解决**：去掉 `-WindowStyle Hidden`，或使用无头模式（不带 `--headed`）。

```powershell
# 正确（headed，窗口正常显示）
Start-Process playwright-cli.cmd -ArgumentList "open --persistent --browser edge --headed"

# 错误（headed + Hidden = 闪退）
Start-Process playwright-cli.cmd -ArgumentList "open --persistent --browser edge --headed" -WindowStyle Hidden
```

## 13. `Browser is already in use for <profile>, use --isolated`

**现象**：启动浏览器时报 profile 被占用。

**根因**：上一次浏览器实例未正确关闭，profile 目录被锁定。

**解决**：启动前先 `playwright-cli close-all`，等待 2-3 秒确保进程完全退出。

> ⚠️ `close-all` 会关闭所有 Edge 窗口，包括用户正在浏览的，执行前请提醒用户保存工作。

## 14. `Browser 'default' is not open` 但 `list` 显示 open

**现象**：`playwright-cli list` 输出 `status: open`，但 `run-code` 报浏览器未打开。

**根因**：`.playwright-cli` 目录下的 session 文件（`page-*.yml`）与 CWD 绑定。浏览器从目录 A 启动（session 写入 A 的 `.playwright-cli`），但 `run-code` 在目录 B 执行（找 B 的 `.playwright-cli`，找不到 session）。

**解决**：确保 `run-code` 与浏览器启动在同一个 CWD 下执行。便携化方案中用 `Set-Location $ScriptDir` 统一工作目录。

## 15. 脚本复制到新目录后字幕消失但评论正常

**现象**：在原目录运行一切正常，复制脚本到新目录后字幕变"无字幕"，评论和元数据正常。

**根因**：`--persistent` 模式的 user-data-dir 按 CWD 自动生成。不同目录 = 不同 profile = 不同的 Cookie。新 profile 没有 B站登录态 → AI 字幕不返回（见第 10 条）。

**解决**：用 `--profile` 参数固定 profile 路径：

```powershell
$ProfileDir = Join-Path $env:LOCALAPPDATA 'bili-reader-profile'
Start-Process playwright-cli.cmd -ArgumentList "open","--persistent","--browser","edge","--profile",$ProfileDir,"--headed"
```