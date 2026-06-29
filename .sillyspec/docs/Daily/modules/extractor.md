---
schema_version: 1
doc_type: module-card
module_id: extractor
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# extractor

## 定位
- 负责：读取上游精选 URL 列表 → 单篇正文 HTML 抓取（双通道）→ 5 层策略链正文提取 → 文本后处理与污染检测 → 写入审核稿
- 不负责：URL 候选选择与去重（classifier / step4）；摘要与日报生成（summarizer / step7）；正文 LLM 改写或润色

## 契约摘要
- 上游输入：`1新闻_链接.md`（10 条经 classifier 精选的 URL）
- 下游输出：`2新闻_已审核.md`（标题 + 正文纯文本）
- 抓取双通道：
  - 静态：`fetch_html_static(url)` — urllib 直取
  - JS 渲染：`chromium_dom(url)` — `chromium --dump-dom`，120s 超时 + `TimeoutExpired` 捕获
- 路由规则：`needs_chromium(url)` 命中 → 走 chromium，否则 urllib
- 5 层提取策略，前一层失败回退下一层
- 后处理：去版权 / ICP / 登录注册 / 视频 UI 残片 / CAS 模板尾部
- 污染检测：识别 CSS/JS 残片、导航集合、`enpproperty` 标记、地址+邮编模板；命中则尝试退回更激进清洗再判一次

## 关键逻辑

```
parse 1新闻_链接.md → [(title, url), ...]
for (title, url) in items:
    html = chromium_dom(url) if needs_chromium(url) else fetch_html_static(url)
    if not html or len(html) < 500: skip
    body = extract_body(html, url)         # 5 层回退
    text = _postprocess_text(body)
    if _is_contaminated(text):
        html2 = _aggressive_clean(html, url)
        body2 = extract_body(html2, url)
        text  = _postprocess_text(body2)
        if _is_contaminated(text): skip
    append (title, text) → 2新闻_已审核.md
```

5 层提取（`extract_body` 内部，step6.py:67）：
1. **TRS_Editor** — `<div class="TRS_Editor">…</div>`（政府站常用）
2. **语义/通用容器** 循环匹配：`<article>` / `class="article-content"` / `class="content"` / `class="detail"` / `class="main-content"` / `id="ozoom"`
3. **ckxx 特例 A** — `ckxxapp` / `cankaoxiaoxi` 命中时抓 `var contentTxt = "…"`（JS 字面量内嵌正文）
4. **ckxx 特例 B** — 同站点关键词锚定（`据美国《`/`据路透社`/`参考消息网`…）+ 终止 marker（`责任编辑` / `";` / `编译/`）截断
5. **`<p>` 回退** — 收集所有段落，过滤 `EXCLUDE_PARAS` 噪声，长度 >20 的段落拼接

`needs_chromium` 命中域名（step6.py:205）：`cctv.com`、`military.cctv`、`cnnc.com.cn`、`news.cctv`

`_is_contaminated` 判定信号（step6.py:172）：
- CSS 残片：`font-family` / `margin:` / `padding:` / `line-height:` / `border-spacing`
- JS 残片：`var ih =` / `var p =` / `document.getElementById` / `console.log`
- 导航集合：`日报`+`周报`+`杂志` 三词 100 字符内共现（捕获站点导航条被错当正文）
- 标记残留：`enpproperty-->`（人民网模板未剥干净）
- 单位尾部：`地址：` + `邮编：` 200 字符内共现（中科院系站点的页脚）

## 模块边界与外部依赖

- 标准库：`re`、`urllib.request`、`subprocess`、`html`（用于 `html.unescape`）
- 外部二进制：`chromium`（`--dump-dom --headless --no-sandbox`），缺失则 chromium 通道彻底失效，触发上层短长度兜底
- 文件 I/O：
  - 读：项目根 `1新闻_链接.md`
  - 写：项目根 `2新闻_已审核.md`（覆盖式，每日全量重写）
- 编码假设：上游 markdown 与下游写入均按 UTF-8 处理；远端 HTML 在 `fetch_html_static` 中按响应头/`utf-8` 兜底解码

## 注意事项
- 本模块**无 LLM 调用**，纯规则提取，速度与正确性都依赖 5 层策略与污染检测的覆盖度
- `fetch_and_extract` 同时被 archiver 模块（`archive_enrich.enrich_body`）调用用于归档正文补全；修改签名或返回值时需同步更新 archiver
- chromium 子进程 120s 超时；超时返回空串而非异常，由上层 `len(html) < 500` 兜底跳过
- `_aggressive_clean` 对 ckxx 系站点保持原 HTML（避免破坏 `var contentTxt` 字面量）
- 后处理顺序敏感：先剥视频 UI → 再剥 enpproperty 时间戳尾部 → 再剥 CAS 地址尾部 → 最后空白归一与按句去重
- 修改时需同步检查的下游：summarizer (step7) 读 `2新闻_已审核.md`，对格式（标题行 + 正文块）有解析约定
- 新增源站若 JS 渲染才出正文，需追加到 `needs_chromium` 域名列表；新增容器选择器请插入到第 2 层 `for pat in […]` 中而非新建分支

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
