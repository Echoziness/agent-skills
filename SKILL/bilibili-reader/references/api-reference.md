# B站 API 参考手册

## API 总览

| 用途 | 数据源 | 需要签名？ | 获取方式 | 分页方式 |
|---|---|---|---|---|
| 视频元数据 | `window.__INITIAL_STATE__` | — | `page.evaluate` 直读 | — |
| AI 字幕 URL | `api.bilibili.com/x/player/wbi/v2` | **是（Wbi）** | `page.on('response')` 拦截 | — |
| 字幕文本 | 字幕 CDN URL | — | `page.evaluate(fetch(url))` | — |
| 主评论 | `api.bilibili.com/x/v2/reply/main` | **否** | `page.evaluate(fetch(url))` | cursor |
| 子评论 | `api.bilibili.com/x/v2/reply/reply` | **否** | `page.evaluate(fetch(url))` | pn + ps |

## 1. 视频元数据：`window.__INITIAL_STATE__`

页面加载后直接在浏览器沙箱中读取，不需要任何 API 请求。

```javascript
const videoMeta = await page.evaluate(() => {
    const state = window.__INITIAL_STATE__;
    if (!state) return null;
    const videoData = state?.videoData || {};
    const stat = videoData?.stat || {};
    const owner = videoData?.owner || {};
    return {
        bvid: videoData?.bvid || '',
        aid: videoData?.aid || '',
        title: videoData?.title || '',
        owner_name: owner?.name || '',
        owner_mid: owner?.mid || '',
        view: stat?.view || 0,
        danmaku: stat?.danmaku || 0,
        reply: stat?.reply || 0,
        favorite: stat?.favorite || 0,
        coin: stat?.coin || 0,
        share: stat?.share || 0,
        like: stat?.like || 0,
        pubdate: videoData?.pubdate || 0,
        desc: videoData?.desc || '',
        duration: videoData?.duration || 0
    };
});
```

**关键字段**：`aid`（纯数字视频ID）是后续评论 API 的 `oid` 参数。`bvid` 是 URL 中的字母数字ID。

## 2. AI 字幕：拦截获取

字幕 URL 只能通过拦截 `player/wbi/v2` 响应获取。

### 拦截代码

```javascript
let subUrl = null;

const responseHandler = async (response) => {
    const url = response.url();
    try {
        if (url.includes('api.bilibili.com/x/player/wbi/v2')) {
            const json = await response.json();
            if (json.data?.subtitle?.subtitles?.length > 0) {
                subUrl = json.data.subtitle.subtitles[0].subtitle_url;
                // URL 以 // 开头需补 https:
                if (subUrl.startsWith('//')) subUrl = 'https:' + subUrl;
            }
        }
    } catch (e) {}
};

page.on('response', responseHandler);
await page.goto(videoUrl, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(4000);
if (!subUrl) await page.waitForTimeout(2000); // 字幕接口可能较慢
page.removeListener('response', responseHandler);
```

### 下载字幕文本

```javascript
let subtitlesText = '该视频无字幕（UP主未上传或AI未生成）';
if (subUrl) {
    const subtitles = await page.evaluate(async (url) => {
        try {
            const res = await fetch(url);
            const json = await res.json();
            return json.body; // [{content: "对话文本"}, ...]
        } catch (e) { return null; }
    }, subUrl);

    if (Array.isArray(subtitles) && subtitles.length > 0) {
        subtitlesText = subtitles.map(s => s.content).join(' ');
    }
}
```

## 3. 主评论 API：`reply/main`

### URL 结构

```
https://api.bilibili.com/x/v2/reply/main?oid={aid}&type=1&mode=3&pagination_str={encoded_json}&plat=1
```

### 参数说明

| 参数 | 值 | 说明 |
|---|---|---|
| `oid` | 视频的 `aid`（纯数字） | 不是 bvid |
| `type` | `1` | 固定值，表示视频 |
| `mode` | `3` | 3=热门排序 |
| `pagination_str` | URL 编码的 JSON | cursor 分页用 |
| `plat` | `1` | 固定值 |

### 分页逻辑（cursor 分页）

重要：不是传统的 pn/ps 分页，而是 cursor 游标分页。

**第一页**：`pagination_str={"offset":""}`（空字符串）

**后续页**：`pagination_str={"offset":"<上一页返回的next_offset>"}`

编码方式：`encodeURIComponent(JSON.stringify({offset: nextOffsetValue}))`

### 分页关键字段

```javascript
const cursor = result?.data?.cursor;
const nextOffset = cursor?.pagination_reply?.next_offset; // 下一页游标
const isEnd = cursor?.is_end; // 是否最后一页
```

**完整示例**：

```javascript
let nextOffset = '';
let pageNum = 0;
const MAX_PAGES = 5;

while (pageNum < MAX_PAGES) {
    const offsetParam = nextOffset
        ? encodeURIComponent(JSON.stringify({ offset: nextOffset }))
        : encodeURIComponent(JSON.stringify({ offset: '' }));

    const url = `https://api.bilibili.com/x/v2/reply/main?oid=${aid}&type=1&mode=3&pagination_str=${offsetParam}&plat=1`;

    const result = await page.evaluate(async (fetchUrl) => {
        try {
            const res = await fetch(fetchUrl, { credentials: 'include' });
            return await res.json();
        } catch (e) { return { code: -1 }; }
    }, url);

    if (!result || result.code !== 0) break;

    const replies = result?.data?.replies || [];
    if (replies.length === 0) break;

    // 处理每条评论...

    nextOffset = result?.data?.cursor?.pagination_reply?.next_offset || '';
    if (result?.data?.cursor?.is_end || !nextOffset) break;

    pageNum++;
    await page.waitForTimeout(300);
}
```

### 评论对象字段

| 字段 | 路径 | 说明 |
|---|---|---|
| 评论ID | `r.rpid_str` | 字符串类型，子评论查询用 |
| 用户名 | `r.member.uname` | |
| 内容 | `r.content.message` | |
| 点赞数 | `r.like` | |
| 子评论数 | `r.rcount` | 用于决定是否拉取子评论 |

> **注意**：评论列表不包含置顶评论（`top_replies` 数组），热门视频的置顶评论会被跳过。

## 4. 子评论 API：`reply/reply`

### URL 结构

```
https://api.bilibili.com/x/v2/reply/reply?oid={aid}&type=1&root={rpid_str}&ps=20&pn=1
```

### 参数说明

| 参数 | 值 | 说明 |
|---|---|---|
| `oid` | 视频的 `aid` | 同主评论 |
| `type` | `1` | 固定值 |
| `root` | 主评论的 `rpid_str` | **必须是字符串，不是数字** |
| `ps` | `20` | 每页条数，最大20 |
| `pn` | `1, 2, 3...` | 传统页码分页 |

### 分页逻辑（传统 pn/ps）

```javascript
const totalPages = Math.ceil((subResult?.data?.page?.count || 0) / 20);
// pn 从 1 开始，到 totalPages
```

### 完整示例

```javascript
for (let i = 0; i < commentsWithSubs.length && i < 20; i++) {
    const c = commentsWithSubs[i];
    let pn = 1;

    while (pn <= 3) { // 最多翻3页
        const url = `https://api.bilibili.com/x/v2/reply/reply?oid=${aid}&type=1&root=${c.rpid}&ps=20&pn=${pn}`;

        const result = await page.evaluate(async (fetchUrl) => {
            try {
                const res = await fetch(fetchUrl, { credentials: 'include' });
                return await res.json();
            } catch (e) { return { code: -1 }; }
        }, url);

        if (!result || result.code !== 0) break;

        const replies = result?.data?.replies || [];
        // 处理子评论...

        const totalPages = Math.ceil((result?.data?.page?.count || 0) / 20);
        if (pn >= totalPages) break;
        pn++;
        await page.waitForTimeout(200);
    }
}
```