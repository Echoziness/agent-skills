# 手动分步执行指南

当 `br.ps1` 脚本不可用或需要调试时，按以下步骤手动操作。

## 前置条件

- Node.js + `npm install -g @playwright/cli`
- Microsoft Edge 浏览器
- B站账号（首次需登录）

## 步骤 1：创建工作目录和配置

```powershell
$WorkDir = 'C:\path\to\work'
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Set-Location $WorkDir
```

创建 `.playwright/cli.config.json`：

```powershell
New-Item -ItemType Directory -Force -Path '.playwright' | Out-Null
@'
{ "browser": { "browserName": "chromium", "launchOptions": { "channel": "msedge" } } }
'@ | Set-Content -Path '.playwright\cli.config.json' -Encoding UTF8
```

> 此配置指定使用 Edge 浏览器。缺少此文件会导致 playwright-cli 回退到默认 chromium 而启动失败。

## 步骤 2：启动浏览器

```powershell
playwright-cli close-all 2>$null
Start-Sleep -Seconds 2

$ProfileDir = Join-Path $env:LOCALAPPDATA 'bili-reader-profile'
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

Start-Process playwright-cli.cmd -ArgumentList "open --persistent --browser edge --profile `"$ProfileDir`" --headed"

# 轮询等待就绪（最多 20 秒）
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 2
    if ((playwright-cli list 2>&1) -match 'status: open') { break }
}
```

> ⚠️ `close-all` 会关闭所有 Edge 窗口，执行前必须告知用户保存工作。

关键点：
- `--profile` 固定路径，避免换目录丢失登录态
- `Set-Location $WorkDir` 确保 `.playwright` 配置和 session 在同一目录
- `--headed` 模式允许用户手动登录 B站

## 步骤 3：检测登录状态

```powershell
$checkJs = @'
async (page) => {
    const cookies = await page.context().cookies('https://www.bilibili.com');
    return { hasLogin: cookies.some(c => c.name === 'DedeUserID') };
}
'@
[System.IO.File]::WriteAllText('.\check_login.js', $checkJs, [System.Text.UTF8Encoding]::new($false))

playwright-cli run-code --raw --filename .\check_login.js
```

返回 `{"hasLogin":true}` 表示已登录。未登录时需导航到 `https://passport.bilibili.com/login` 让用户手动登录。

## 步骤 4：执行数据提取

将 JS 提取脚本（见下方模板）保存为 `.js` 文件，替换 `__VIDEO_URL__` 为实际视频链接。

**⚠️ 脚本文件必须在工作目录或其子目录下**（`run-code --filename` 的文件沙箱限制）。

```powershell
[System.IO.File]::WriteAllText('.\bili_extract_BVxxxxxx.js', $jsContent, [System.Text.UTF8Encoding]::new($false))

$raw = playwright-cli run-code --raw --filename .\bili_extract_BVxxxxxx.js 2>&1
$out = $raw | ConvertFrom-Json -ErrorAction Stop
```

## 步骤 5：保存结果

```powershell
$bvid = 'BVxxxxxx'
$out.subtitles | Out-File -FilePath ".\$bvid`_subs.txt" -Encoding utf8
$out.comments | ConvertTo-Json -Depth 5 | Out-File -FilePath ".\$bvid`_comments.json" -Encoding utf8
$out.video | ConvertTo-Json -Depth 3 | Out-File -FilePath ".\$bvid`_meta.json" -Encoding utf8
```

## 步骤 6：清理

```powershell
playwright-cli close-all
Set-Location $origPwd
```

---

## JS 提取脚本模板

> 与 `scripts/br.ps1` 内嵌的 `$jsTemplate` 一致，仅将 `__VIDEO_URL__` 标记为待替换占位符。

```javascript
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
```

使用时将 `__VIDEO_URL__` 替换为实际的 B站视频链接。