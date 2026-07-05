---
schema_version: 1
doc_type: module-card
module_id: extractor
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
updated_at: 2026-07-02 01:33:35
---

# extractor

## 定位
- 负责：读取上游精选 URL 列表 → 单篇正文 HTML 抓取（双通道）→ trafilatura 正文抽取 + SITE_POSTPROCESS 站点后处理 → 文本后处理与污染检测 → 写入审核稿
- 不负责：URL 候选选择与去重（classifier / step4）；摘要与日报生成（summarizer / step7）；正文 LLM 改写或润色

## 契约摘要
- 上游输入：`1新闻_链接.md`（10 条经 classifier 精选的 URL，含 `发布时间：YYYY-MM-DD`）
- 下游输出：`2新闻_已审核.md`（标题 + 正文纯文本）
- 抓取双通道：
  - 静态：`fetch_html_static(url)` — urllib 直取
  - JS 渲染：`chromium_dom(url)` — `chromium --dump-dom`，120s 超时 + `TimeoutExpired` 捕获
- 路由规则：`needs_chromium(url)` 命中 → 优先 chromium（失败→静态），否则优先静态（失败→重试→chromium）；所有方法失败时 pipeline fail closed
- 正文抽取：`trafilatura.extract` 优先，`ckxxapp`/`cankaoxiaoxi` JS 字面量页退回到 `_extract_ckxx_content_txt` fallback
- 站点后处理：`SITE_POSTPROCESS` registry 按 URL 匹配 CAS/People/CCTV 专用清理函数，再执行通用清理（HTML unescape、视频 UI 残片剥离、空白归一、重复句去重）
- 污染检测：识别 CSS/JS 残片、导航集合、`enpproperty` 标记、地址+邮编模板；命中则尝试退回更激进清洗再判一次

## 关键逻辑

```
parse 1新闻_链接.md → [(title, url), ...]
for (title, url) in items:
    html = chromium_dom(url) if needs_chromium(url) else fetch_html_static(url)
    if not html or len(html) < 500: skip
    body = extract_body(html, url)         # trafilatura.extract → ckxx fallback
    text = _postprocess_text(body, url)    # SITE_POSTPROCESS → general clean
    if _is_contaminated(text):
        html2 = _aggressive_clean(html, url)
        body2 = extract_body(html2, url)
        text  = _postprocess_text(body2, url)
        if _is_contaminated(text): skip
    append (title, published_at, text) → 2新闻_已审核.md
```

正文抽取（`extract_body` 内部，step6.py:55）：
1. **trafilatura** — `tf_extract(html, output_format="txt", include_comments=False, include_tables=False, favor_precision=True)` 通用正文抽取
2. **ckxx fallback** — url 含 `ckxxapp`/`cankaoxiaoxi` 时回退到 `_extract_ckxx_content_txt(html)`，先抓 `var contentTxt = "…"` JS 字面量，再按关键词锚定截断（`据美国《`/`据路透社`/`参考消息网`…）
3. 若都空 → 返回 None

站点后处理（`_postprocess_text`）：
- `SITE_POSTPROCESS` registry 按 URL 匹配：
  - `people.com.cn` → `_people_postprocess`：剥离 `enpproperty` 时间戳尾部
  - `cas.cn` → `_cas_postprocess`：剥离地址/邮编/电话页脚 + "贯彻落实"模板头
  - `cctv.com` / `military.cctv` → `_cctv_postprocess`：剥离播放器 UI 残片（静音/全屏/ADCountdown/加载进度/高清画质/续播/跳过广告等）
- 通用清理：HTML unescape → 视频播放器模板 → 空白归一 → 重复句去重

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
- 本模块**无 LLM 调用**，纯规则 + trafilatura 提取
- `fetch_and_extract` 同时被 archiver 模块（`archive_enrich.enrich_body`）调用用于归档正文补全；修改签名或返回值时需同步更新 archiver
- chromium 子进程 120s 超时；超时返回空串而非异常，由上层 `len(html) < 500` 兜底跳过
- `_aggressive_clean` 对 ckxx 系站点保持原 HTML（避免破坏 `var contentTxt` 字面量）
- 后处理顺序敏感：站点清理先于通用清理（先 `SITE_POSTPROCESS` 再通用 UI 剥离 → 空白归一 → 去重）
- 修改时需同步检查的下游：summarizer (step7) 读 `2新闻_已审核.md`，对格式（标题行 + 正文块）有解析约定
- 新增源站若 JS 渲染才出正文，需追加到 `needs_chromium` 域名列表；新增站点后处理，追加到 `SITE_POSTPROCESS` registry
- CAS 正文仍可能包含页眉/导航噪声（如"主要职责/办院方针"），后续需加强对 CAS 站点的正确定位剥离

## 人工备注

<!-- MANUAL_NOTES_START -->

## 变更索引

- ql-20260704-002-a4d1 | 强制采集见报/发布日期为当天的新闻
- ql-20260705-001-b3e8 | Step6/7 正文提取必须成功，失败则 pipeline fail closed

<!-- MANUAL_NOTES_END -->
