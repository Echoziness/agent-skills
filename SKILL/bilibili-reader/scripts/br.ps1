param(
    [Parameter(HelpMessage='B站视频完整链接')]
    [string]$Url
)

$ErrorActionPreference = 'Stop'
chcp 65001 >$null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ──────────────────────────────────────────────
#  路径定义：基于脚本所在目录 + 固定浏览器 profile
# ──────────────────────────────────────────────
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
$OutDir = Join-Path $ScriptDir 'bili-data'
$TmpDir = Join-Path $ScriptDir '.bili-tmp'
$PwConfigDir = Join-Path $ScriptDir '.playwright'
$ProfileDir = Join-Path $env:LOCALAPPDATA 'bili-reader-profile'

New-Item -ItemType Directory -Force -Path $OutDir, $TmpDir, $ProfileDir | Out-Null

# ──────────────────────────────────────────────
#  确保 playwright-cli 配置存在（CWD 相对查找）
# ──────────────────────────────────────────────
$pwConfigFile = Join-Path $PwConfigDir 'cli.config.json'
if (-not (Test-Path $pwConfigFile)) {
    New-Item -ItemType Directory -Force -Path $PwConfigDir | Out-Null
    $defaultConfig = @'
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "channel": "msedge"
    }
  }
}
'@
    [System.IO.File]::WriteAllText($pwConfigFile, $defaultConfig, [System.Text.UTF8Encoding]::new($false))
    Write-Host "[初始化] 已创建 Playwright 浏览器配置 (.playwright/cli.config.json)" -ForegroundColor Yellow
}

# 切换到脚本目录，让 playwright-cli 找到 .playwright 配置和 session
$origPwd = $PWD.Path
Set-Location $ScriptDir

# ──────────────────────────────────────────────
#  检查 playwright-cli 是否可用
# ──────────────────────────────────────────────
$cli = 'playwright-cli.cmd'
if (-not (Get-Command $cli -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未找到 playwright-cli，请先安装:" -ForegroundColor Red
    Write-Host "  npm install -g @playwright/cli" -ForegroundColor Yellow
    Set-Location $origPwd
    if (-not $Url) { Read-Host '按回车键退出' }
    exit 1
}

# ──────────────────────────────────────────────
#  内嵌 JS 提取模板（单引号 here-string，不展开变量）
# ──────────────────────────────────────────────
$jsTemplate = @'
async (page) => {
    let subUrl = null;
    let wbiDebug = { called: false, subtitlesCount: -1, error: null };
    const responseHandler = async (response) => {
        const url = response.url();
        try {
            if (url.includes('api.bilibili.com/x/player/wbi/v2')) {
                wbiDebug.called = true;
                const json = await response.json();
                const subs = json.data?.subtitle?.subtitles || [];
                wbiDebug.subtitlesCount = subs.length;
                if (subs.length > 0) {
                    subUrl = subs[0].subtitle_url;
                    if (subUrl.startsWith('//')) subUrl = 'https:' + subUrl;
                }
            }
        } catch (e) { wbiDebug.error = e.message; }
    };

    page.on('response', responseHandler);
    await page.goto('__VIDEO_URL__', { waitUntil: 'domcontentloaded' });
    for (let i = 0; i < 15; i++) {
        await page.waitForTimeout(2000);
        if (subUrl) break;
    }
    page.removeListener('response', responseHandler);

    const videoMeta = await page.evaluate(() => {
        const state = window.__INITIAL_STATE__;
        if (!state) return null;
        const videoData = state?.videoData || {};
        const stat = videoData?.stat || {};
        const owner = videoData?.owner || {};
        return {
            bvid: videoData?.bvid || '', aid: videoData?.aid || '',
            title: videoData?.title || '', owner_name: owner?.name || '',
            owner_mid: owner?.mid || '', view: stat?.view || 0,
            danmaku: stat?.danmaku || 0, reply: stat?.reply || 0,
            favorite: stat?.favorite || 0, coin: stat?.coin || 0,
            share: stat?.share || 0, like: stat?.like || 0,
            pubdate: videoData?.pubdate || 0, desc: videoData?.desc || '',
            duration: videoData?.duration || 0
        };
    });

    let subtitlesText = '该视频无字幕（UP主未上传或AI未生成）';
    if (subUrl) {
        const subtitles = await page.evaluate(async (url) => {
            try { const res = await fetch(url); const json = await res.json(); return json.body; }
            catch (e) { return null; }
        }, subUrl);
        if (Array.isArray(subtitles) && subtitles.length > 0) {
            subtitlesText = subtitles.map(s => s.content.trim()).join('\n');
        }
    }

    const oid = String(videoMeta?.aid || '');
    const allMainComments = [];
    if (oid) {
        let nextOffset = '', pageNum = 0;
        while (pageNum < 5) {
            const offsetParam = nextOffset
                ? encodeURIComponent(JSON.stringify({ offset: nextOffset }))
                : encodeURIComponent(JSON.stringify({ offset: '' }));
            const mainUrl = `https://api.bilibili.com/x/v2/reply/main?oid=${oid}&type=1&mode=3&pagination_str=${offsetParam}&plat=1`;
            const mainResult = await page.evaluate(async (fetchUrl) => {
                try { const res = await fetch(fetchUrl, { credentials: 'include' }); return await res.json(); }
                catch (e) { return { code: -1, error: e.message }; }
            }, mainUrl);
            if (!mainResult || mainResult.code !== 0) break;
            const replies = mainResult?.data?.replies || [];
            if (replies.length === 0) break;
            for (const r of replies) {
                allMainComments.push({
                    rpid: r?.rpid_str || String(r?.rpid || ''),
                    user: r?.member?.uname || '',
                    text: (r?.content?.message || '').replace(/\s+/g, ' ').trim(),
                    likes: r?.like || 0, sub_replies_count: r?.rcount || 0
                });
            }
            const cursor = mainResult?.data?.cursor;
            nextOffset = cursor?.pagination_reply?.next_offset || '';
            if (cursor?.is_end || !nextOffset) break;
            pageNum++;
            await page.waitForTimeout(300);
        }

        const commentsWithSubs = allMainComments.filter(c => c.sub_replies_count > 0);
        const maxSubFetch = Math.min(commentsWithSubs.length, 20);
        const subCommentsByRoot = {};
        for (let i = 0; i < maxSubFetch; i++) {
            const c = commentsWithSubs[i];
            const subFetchUrl = `https://api.bilibili.com/x/v2/reply/reply?oid=${oid}&type=1&root=${c.rpid}&ps=5&pn=1`;
            const subResult = await page.evaluate(async (fetchUrl) => {
                try { const res = await fetch(fetchUrl, { credentials: 'include' }); return await res.json(); }
                catch (e) { return { code: -1, error: e.message }; }
            }, subFetchUrl);
            if (!subResult || subResult.code !== 0) continue;
            const subReplies = (subResult?.data?.replies || []).slice(0, 5);
            subCommentsByRoot[c.rpid] = subReplies.map(r => ({
                user: r?.member?.uname || '',
                text: (r?.content?.message || '').replace(/\s+/g, ' ').trim(),
                likes: r?.like || 0
            }));
            await page.waitForTimeout(200);
        }
        for (const c of allMainComments) {
            c.sub_replies = subCommentsByRoot[c.rpid] || [];
        }
    }

    return {
        video: videoMeta, subtitles: subtitlesText, comments: allMainComments,
        meta: { subtitleFound: Boolean(subUrl), commentsCount: allMainComments.length, wbiDebug }
    };
}
'@

# ──────────────────────────────────────────────
#  浏览器管理
# ──────────────────────────────────────────────
function Ensure-Browser {
    Write-Host "[注意] 即将关闭所有 Edge 浏览器窗口，请提前保存工作" -ForegroundColor Yellow
    & $cli close-all 2>&1 | Out-Null
    Start-Sleep -Seconds 2

    Write-Host "启动浏览器..." -ForegroundColor Yellow
    $argStr = "open --persistent --browser edge --profile `"$ProfileDir`" --headed"
    Start-Process $cli -ArgumentList $argStr

    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 2
        $list = & $cli list 2>&1
        if ($list -match 'status: open') { $ready = $true; break }
        Write-Host "  等待浏览器就绪..." -ForegroundColor DarkGray
    }

    if (-not $ready) {
        Write-Host "[错误] 浏览器启动失败" -ForegroundColor Red
        return $false
    }
    return $true
}

function Test-BiliLogin {
    $checkFile = Join-Path $TmpDir '_check_login.js'
    $checkJs = @'
async (page) => {
    const cookies = await page.context().cookies('https://www.bilibili.com');
    return { hasLogin: cookies.some(c => c.name === 'DedeUserID') };
}
'@
    [System.IO.File]::WriteAllText($checkFile, $checkJs, [System.Text.UTF8Encoding]::new($false))

    $raw = & $cli run-code --raw --filename $checkFile 2>&1
    try {
        $result = $raw | ConvertFrom-Json -ErrorAction Stop
        return ($result.hasLogin -eq $true)
    } catch {
        return $false
    }
}

function Ensure-BiliLogin {
    if (Test-BiliLogin) { return }

    Write-Host ""
    Write-Host "[提示] 获取AI字幕需要登录B站，请在浏览器窗口中登录" -ForegroundColor Yellow
    & $cli goto 'https://passport.bilibili.com/login' 2>&1 | Out-Null
    Write-Host "  登录完成后回到此处按回车继续" -ForegroundColor Yellow
    Read-Host

    if (Test-BiliLogin) {
        Write-Host "[成功] B站登录完成" -ForegroundColor Green
    } else {
        Write-Host "[警告] 未检测到登录，AI字幕可能无法获取" -ForegroundColor Yellow
        Write-Host "  稍后可在浏览器中登录后重新运行脚本" -ForegroundColor Yellow
    }
}

function Extract-BiliVideo {
    param([string]$VideoUrl)

    if ($VideoUrl -notmatch '(BV[a-zA-Z0-9]+)') {
        Write-Host "[错误] 无法从URL提取BVID" -ForegroundColor Red
        return
    }
    $bvid = $Matches[1]
    Write-Host ""
    Write-Host "[$bvid] 提取中..." -ForegroundColor Cyan

    $js = $jsTemplate -replace '__VIDEO_URL__', $VideoUrl
    $jsPath = Join-Path $TmpDir "bili_extract_$bvid.js"
    [System.IO.File]::WriteAllText($jsPath, $js, [System.Text.UTF8Encoding]::new($false))

    $raw = & $cli run-code --raw --filename $jsPath 2>&1
    if ([string]::IsNullOrWhiteSpace($raw)) {
        Write-Host "[失败] playwright-cli 输出为空" -ForegroundColor Red
        return
    }

    try {
        $out = $raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Write-Host "[失败] JSON解析出错: $($_.Exception.Message)" -ForegroundColor Red
        return
    }

    if ($out.error) {
        Write-Host "[失败] 脚本报错: $($out.error)" -ForegroundColor Red
        return
    }

    $subsFile     = Join-Path $OutDir "${bvid}_subs.txt"
    $commentsFile = Join-Path $OutDir "${bvid}_comments.json"
    $metaFile     = Join-Path $OutDir "${bvid}_meta.json"

    $out.subtitles | Out-File -FilePath $subsFile -Encoding utf8
    $out.comments | ConvertTo-Json -Depth 5 | Out-File -FilePath $commentsFile -Encoding utf8
    $out.video | ConvertTo-Json -Depth 3 | Out-File -FilePath $metaFile -Encoding utf8

    Write-Host "[完成] $($out.video.title)" -ForegroundColor Green
    Write-Host "  UP主: $($out.video.owner_name)  播放: $($out.video.view)  弹幕: $($out.video.danmaku)  点赞: $($out.video.like)"
    Write-Host "  字幕: $(if($out.meta.subtitleFound){'已获取'}else{'无字幕'})  评论: $($out.meta.commentsCount) 条"
    if (-not $out.meta.subtitleFound) {
        $dbg = $out.meta.wbiDebug
        Write-Host "  [调试] WBI调用: $($dbg.called), 字幕数: $($dbg.subtitlesCount), 错误: $($dbg.error)" -ForegroundColor DarkGray
    }
    Write-Host "  文件: ${bvid}_subs.txt | ${bvid}_comments.json | ${bvid}_meta.json"
    Write-Host ""
}

# ──────────────────────────────────────────────
#  入口：带 -Url 参数 → 单次执行；无参数 → 交互循环
# ──────────────────────────────────────────────
try {
    if (-not (Ensure-Browser)) {
        Set-Location $origPwd
        exit 1
    }
    Ensure-BiliLogin

    if ($Url) {
        Extract-BiliVideo $Url
    } else {
        Write-Host "=== B站视频信息提取 ===" -ForegroundColor Yellow
        Write-Host "  数据目录: $OutDir" -ForegroundColor DarkGray
        Write-Host ""
        while ($true) {
            $userInput = Read-Host '输入B站视频链接 (q退出)'
            if ($userInput -match '^[qQ]$') { break }
            if ([string]::IsNullOrWhiteSpace($userInput)) { continue }
            Extract-BiliVideo $userInput
        }
        Write-Host ""
        Write-Host '再见!'
    }
} finally {
    Write-Host "[注意] 即将关闭所有 Edge 浏览器窗口" -ForegroundColor Yellow
    & $cli close-all 2>&1 | Out-Null
    Write-Host "再见!"
    Set-Location $origPwd
}
