# Playwright CLI 深层行为详解

> 这些行为大多未在官方文档中记录，是通过大量对比实验才确认的。理解它们可以避免在浏览器管理上浪费数小时。

## 目录

- [1. Profile 与 CWD 的绑定关系](#1-profile-与-cwd-的绑定关系)
- [2. Session 文件的 CWD 绑定](#2-session-文件的-cwd-绑定)
- [3. 文件沙箱：run-code --filename 的访问控制](#3-文件沙箱run-code---filename-的访问控制)
- [4. --headed 与 -WindowStyle Hidden 的冲突](#4---headed-与--windowstyle-hidden-的冲突)
- [5. 浏览器注册到 Daemon 的时序](#5-浏览器注册到-daemon-的时序)
- [6. close-all 的清理范围](#6-close-all-的清理范围)
- [7. --profile 参数的正确用法](#7---profile-参数的正确用法)
- [8. .playwright/cli.config.json 的查找逻辑](#8-playwrightcliconfigjson-的查找逻辑)

---

## 1. Profile 与 CWD 的绑定关系

**行为**：`playwright-cli open --persistent` 不指定 `--profile` 时，user-data-dir 按 CWD 自动生成。

**实验证据**：

| 启动时 CWD | user-data-dir |
|---|---|
| `C:\Users\xxx\AI_Workspace` | `C:\Users\xxx\AppData\Local\ms-playwright\daemon\<hash>\ud-default-msedge` |
| `C:\Users\xxx\Downloads\Tool` | 另一个隔离的 profile 目录 |

**影响**：不同 CWD 启动的浏览器是完全独立的 profile——Cookie、登录态、扩展都不共享。脚本复制到新目录后，新 profile 没有 B站登录态，`player/wbi/v2` 不返回 AI 字幕。

**解决**：用 `--profile` 固定路径：

```powershell
$ProfileDir = Join-Path $env:LOCALAPPDATA 'bili-reader-profile'
playwright-cli open --persistent --browser edge --profile $ProfileDir --headed
```

---

## 2. Session 文件的 CWD 绑定

**行为**：`.playwright-cli` 目录下的 session 文件（`page-*.yml`、`console-*.log`）写入启动浏览器时的 CWD。后续 `run-code`、`list` 等命令也在当前 CWD 查找这些 session 文件。

**实验证据**：

从 `AI_Workspace` 启动浏览器 → session 写入 `AI_Workspace\.playwright-cli`。之后在 `Tool` 目录执行 `run-code` → 找 `Tool\.playwright-cli` → 没有 session → 报 `Browser 'default' is not open`。

**解决**：脚本中用 `Set-Location $ScriptDir` 确保启动和执行在同一个 CWD，退出时 `Set-Location $origPwd` 恢复：

```powershell
$origPwd = $PWD.Path
Set-Location $ScriptDir
try {
    # 所有 playwright-cli 操作
} finally {
    Set-Location $origPwd
}
```

---

## 3. 文件沙箱：run-code --filename 的访问控制

**行为**：`run-code --filename <path>` 只能访问浏览器启动时 CWD 及其子目录下的文件。

**实验证据**：

```
Error: File access denied: C:\Users\xxx\Downloads\Tool\.bili-tmp\test.js
is outside allowed roots. Allowed roots:
  C:\Users\xxx\AI_Workspace\.playwright-cli
  C:\Users\xxx\AI_Workspace
```

浏览器从 `AI_Workspace` 启动，但脚本文件在 `Downloads\Tool` → 被拒绝。错误信息中的 `Allowed roots` 清晰列出了允许的路径。

**解决**：确保 JS 脚本文件在浏览器启动时 CWD 的子目录下。便携化方案中，`Set-Location $ScriptDir` 统一了启动和执行的 CWD，JS 脚本写在 `$ScriptDir\.bili-tmp` 下，自然在允许范围内。

---

## 4. --headed 与 -WindowStyle Hidden 的冲突

**行为**：PowerShell 的 `Start-Process -WindowStyle Hidden` 会隐藏新进程的窗口。`--headed` 模式的 Edge 浏览器依赖窗口消息循环运行。两者叠加导致浏览器进程启动后立即退出。

**实验证据**：

```powershell
# PID 创建成功但浏览器立即退出
Start-Process playwright-cli.cmd -ArgumentList "open --persistent --browser edge --headed" -WindowStyle Hidden
# playwright-cli list → status: closed

# 去掉 -WindowStyle Hidden，正常启动
Start-Process playwright-cli.cmd -ArgumentList "open --persistent --browser edge --headed"
# playwright-cli list → status: open
```

**解决**：headed 模式不要加 `-WindowStyle Hidden`。如需静默运行，用无头模式（去掉 `--headed`），但无头模式下用户无法手动登录 B站。

---

## 5. 浏览器注册到 Daemon 的时序

**行为**：`Start-Process` 立即返回，但浏览器注册到 playwright daemon 需要额外时间。在注册完成前，`list` 显示 `status: closed`。

**实验证据**：固定等 5-6 秒在某些机器上不够（特别是首次启动 Edge 创建 profile 时），导致"浏览器启动失败"的误判。

**解决**：轮询 `list` 等待就绪，而非固定等待：

```powershell
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 2
    $list = & $cli list 2>&1
    if ($list -match 'status: open') { $ready = $true; break }
}
```

---

## 6. close-all 的清理范围

**行为**：`playwright-cli close-all` 关闭当前 daemon 下的所有浏览器实例，并清理 session。但不会终止残留的 Edge 进程。

**实验证据**：多次调试后 `list` 中出现十几个 `status: closed` 的旧条目。`close-all` 清理了 daemon 记录，但 Edge 的 profile 锁文件可能还在。下次 `open --profile` 同一路径时报 `Browser is already in use for <profile>`。

**解决**：必要时可在 `close-all` 后追加：

```powershell
Get-Process -Name msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
```

注意这会关闭所有 Edge 窗口，需谨慎使用。

---

## 7. --profile 参数的正确用法

**行为**：`--profile <path>` 指定浏览器 profile 目录。路径必须已存在（或由脚本创建）。首次使用时是空 profile，需要用户登录 B站。

```powershell
$ProfileDir = Join-Path $env:LOCALAPPDATA 'bili-reader-profile'
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

Start-Process playwright-cli.cmd -ArgumentList "open","--persistent","--browser","edge","--profile",$ProfileDir,"--headed"
```

**注意事项**：
- 同一 profile 同一时间只能有一个浏览器实例，否则报 `Browser is already in use`
- profile 路径建议放 `$env:LOCALAPPDATA`（Windows 惯例），不放脚本目录（避免污染）
- `--profile` 与 `--browser edge` 搭配时，profile 内会包含 Edge 专属数据

---

## 8. .playwright/cli.config.json 的查找逻辑

**行为**：playwright-cli 在 CWD 下的 `.playwright/cli.config.json` 查找浏览器配置。该文件指定使用哪个浏览器（如 `msedge`）。

**问题**：脚本复制到新目录后 CWD 下没有 `.playwright` 目录 → 找不到配置 → 回退到默认 chromium → 本机未安装独立 chromium → 启动失败或行为异常。

**配置内容**（使用 Edge 通道）：

```json
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "channel": "msedge"
    }
  }
}
```

**解决**：脚本启动时自动检测并生成：

```powershell
$pwConfigFile = Join-Path $ScriptDir '.playwright' 'cli.config.json'
if (-not (Test-Path $pwConfigFile)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $pwConfigFile) | Out-Null
    [System.IO.File]::WriteAllText($pwConfigFile, $defaultConfig, [System.Text.UTF8Encoding]::new($false))
}
```

注意写入时使用无 BOM 的 UTF-8（`[System.Text.UTF8Encoding]::new($false)`），否则 JSON 解析可能出错。
