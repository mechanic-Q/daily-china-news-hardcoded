---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
doc_type: proposal
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# Proposal

## 动机

Phase 14A 已经把所有合格新闻保存为月度 JSONL，但只保存 metadata + score/signals。这个骨架能证明“新闻没有丢”，但还不能支撑长期知识资产：没有正文，就无法验证新闻原文；没有首图，未来做月报或回顾展示时素材不足。

Phase 14B 要把 archive 从 metadata 层推进到内容层：所有文章补真实正文，top10 文章补首图。正文必须来自原始网页提取，不允许 LLM 生成、改写、润色或补写。

## 关键问题

### 1. metadata-only 不能支撑长期回溯

标题、URL、栏目和评分只能说明一篇文章被选中或归档过，不能保留事实内容。未来月报、趋势分析或人工复核都需要能看到原文正文。

### 2. 正文真实性比完整率更重要

用户明确要求正文不能有任何虚构成分。因此 Phase 14B 不能为了完整率使用 LLM 补全。提取失败时必须记录失败状态和错误原因，而不是生成一个看似合理的正文。

### 3. 图片只服务展示层，不应扩大范围

首图有展示价值，但图片抓取失败率高、站点差异大。只给 top10 抓首图，既满足日报/回顾展示需求，也避免对全部归档文章做高成本图片抓取。

## 变更范围

本次做 Phase 14B：

- 新增 `archive_enrich.py`：读取/更新 archive JSONL，为指定日期记录补正文与 top10 首图
- 正文：所有归档文章调用 `step6.fetch_and_extract(url, title)` 获取真实页面正文
- 图片：仅 `selected_in_top10=true` 的记录提取首图 URL 并下载到 `archive/images/YYYY-MM/`
- JSONL schema 升级到 v2，新增 `body_*` 和 `image_*` 字段
- 修改 `news_archive.py`：14A upsert 时保留已有 14B enrichment 字段，避免覆盖正文/图片
- 修改 `step4.py`：14A 归档后 best-effort 触发 archive enrichment，不阻断日报
- 新增测试覆盖正文状态、图片提取、dry-run、missing-only、best-effort 与 14A upsert 保留 14B 字段

## 不在范围内（显式清单）

- 不抓取多图
- 不给非 top10 文章抓图
- 不用 LLM 生成、改写、润色、补写正文
- 不做 OCR
- 不生成月报（14C）
- 不做查询 UI / 搜索 UI / 统计报表
- 不引入 SQLite / DuckDB / 外部数据库
- 不新增第三方依赖
- 不修改 `run_all.sh`
- 不改变日报中间产物和 HTML/PNG 格式

## 成功标准（可验证）

- `archive_enrich.py --date YYYY-MM-DD` 能读取月度 JSONL 并补指定日期记录
- 所有归档文章都尝试补正文；成功时写 `body_status="extracted"` 和真实 `body`
- 正文提取失败时只写 `body_status="failed"` 和 `body_error`，不写虚构正文
- 代码中不调用 LLM 生成/改写正文
- 只有 top10 记录尝试补首图；非 top10 记录为 `image_status="not_selected"`
- 图片成功时同时写 `image_url` 和 `image_path`
- `--dry-run` 不写 JSONL、不下载图片
- `--missing-only` 跳过已成功补全的正文/图片
- `step4.py` 自动触发 enrichment 失败时不影响 `1新闻_链接.md` 和日报主流程
- 14A `archive_articles` 重新 upsert 不会清空已有 14B 字段
