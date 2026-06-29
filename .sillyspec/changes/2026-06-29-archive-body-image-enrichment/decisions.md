---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
doc_type: decisions
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# Decisions · Phase 14B Archive Body + Top Image Enrichment

## D-001@v1: Phase 14B 范围为全量正文 + top10 首图
- type: boundary
- priority: P0
- status: accepted
- source: user
- question: Phase14B 正文/图片补全的最小交付范围怎么定？
- answer: 所有归档文章都补正文；图片只给 top10 补首图。
- normalized_requirement: `archive_enrich` 必须尝试为指定日期全部 archive records 补 `body`；只有 `selected_in_top10=true` 的 records 才尝试补 `image_url` / `image_path`。
- impacts: [FR-01, FR-03, design §2, design §5]
- evidence: 用户回答“给所有文章补正文…只给top补图片”

## D-002@v1: 正文必须真实可验证，禁止 LLM 虚构
- type: risk
- priority: P0
- status: accepted
- source: user
- question: 归档正文是否可由 LLM 生成、润色或补全？
- answer: 不可以。正文必须经过验证、真实，不能有一点虚构成分，只能来自原页面提取。
- normalized_requirement: `body` 字段只能来自原始 URL 页面提取结果；不得调用 LLM 生成/改写/润色正文；提取失败必须写 `body_status="failed"` 与 `body_error`，不得写 fake body。
- impacts: [FR-02, design §5.3, design §8, verify-real-body]
- evidence: 用户原话“正文必须是经过验证的，真实的，不能是有一点虚构的成分”

## D-003@v1: 首图同时保存 URL 与本地文件
- type: data-model
- priority: P1
- status: accepted
- source: user
- question: 首图怎么保存？
- answer: URL + 本地文件都保存。
- normalized_requirement: 图片成功时 record 必须包含 `image_url` 与 `image_path`；图片下载到 `archive/images/YYYY-MM/<article_id>.<ext>`。
- impacts: [FR-04, design §5.4, design §8]
- evidence: 用户选择“C：URL + 本地文件都保存”

## D-004@v1: 采用独立 archive_enrich helper + CLI
- type: architecture
- priority: P1
- status: accepted
- source: user
- question: Phase14B 实现放在 step4、step6，还是独立 helper？
- answer: 选择独立 `archive_enrich.py` helper + CLI。
- normalized_requirement: 新增 `archive_enrich.py` 负责读取/更新 archive JSONL、补正文、补首图、CLI 补跑；`step4.py` 只做 best-effort 调用，不内联实现。
- impacts: [FR-05, design §5.1, design §6, task-01]
- evidence: 用户选择“方案B”

## D-005@v1: 正文补全 best-effort，不阻断日报
- type: compatibility
- priority: P0
- status: accepted
- source: user
- question: 正文全量补全失败或耗时过长时是否阻断日报？
- answer: 不阻断。默认 best-effort；失败或耗时过长时保留日报产出，之后通过 CLI 补跑。
- normalized_requirement: 自动路径必须 catch all exceptions，不得导致 `run_all.sh` exit 1；达到时间预算时停止剩余增强并保留已完成记录；CLI 必须支持补跑。
- impacts: [FR-06, FR-07, design §5.6, design §9]
- evidence: 用户选择“B：best-effort 不阻断日报，失败用 CLI 补跑”

## D-006@v1: 14A upsert 必须保留 14B 字段
- type: compatibility
- priority: P0
- status: accepted
- source: design-grill
- question: 14A `archive_articles` 重新 upsert 时会不会覆盖 14B 已补的 body/image 字段？
- answer: 当前代码会整条替换，必须修改为合并保留 enrichment 字段。
- normalized_requirement: 已存在 record 中的 `body*`、`image*` 和 14B `archive_status` 不得被 14A metadata upsert 清空；测试必须覆盖先 enrich 后重跑 archive 的场景。
- impacts: [FR-08, design §9, task-news-archive-merge]
- evidence: `news_archive.py:archive_articles` 当前 `existing[rid] = r`

## D-007@v1: 首图抓取单独获取 HTML，不改变 step6.fetch_and_extract 契约
- type: architecture
- priority: P1
- status: accepted
- source: design-grill
- question: `step6.fetch_and_extract` 只返回 body/error，图片提取需要 HTML，是否修改 step6 返回值？
- answer: 不改变 step6 契约；`archive_enrich` 为 top10 单独抓 HTML 提取首图。
- normalized_requirement: `step6.fetch_and_extract(url,title)` 继续返回 `(body, err)`；图片流程在 `archive_enrich.fetch_html_for_image` 内单独复用 step6 static/chromium 路由。
- impacts: [FR-04, design §7, task-image-fetch]
- evidence: `step6.py:fetch_and_extract` 当前返回 `(processed, None)` 或 `(None, err)`
