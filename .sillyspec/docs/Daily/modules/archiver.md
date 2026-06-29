---
schema_version: 1
doc_type: module-card
module_id: archiver
author: lmr
created_at: 2026-06-29 16:22:00
source_commit: cbc7312
---

# archiver

## 定位
- 负责：新闻归档持久化（JSONL）+ 归档正文补全 + 首图提取下载
- 不负责：日报流水线核心流程（collector → classifier → extractor → summarizer → renderer）

## 契约摘要
- 输入：`0新闻_粗筛.md`（collector 产出，用于 step1_3 完成时归档）；`news_archive.py` JSONL 存档
- 输出：`archive/articles/YYYY-MM.jsonl`（归档记录，含正文、首图、状态追踪）
- 归档记录 schema v2：`id`、`date`、`url`、`title`、`source`、`category`、`body`、`body_source_url`、`body_status`(missing/extracted/failed/skipped)、`body_extracted_at`、`body_error`、`image_url`、`image_path`、`image_status`(not_selected/not_found/downloaded/failed/skipped)、`image_downloaded_at`、`image_error`、`archive_status`(metadata-only/body-enriched/body-image-enriched/body-failed)、`archived_at`、`schema_version`
- 正文补全来源：`step6.fetch_and_extract`（真实抓取，禁 LLM）
- 首图提取来源：独立 HTML 请求 + OG/twitter/img 标签解析 + urllib 下载

## 关键逻辑

```
news_archive.py:
  archive_articles(records) → JSONL upsert（14B 字段独立合并）
  archive_articles_best_effort(records) → 静默吞异常
  month_path(today_str) → archive/articles/YYYY-MM.jsonl

archive_enrich.py:
  should_enrich_body(record, missing_only) → bool 判定
  enrich_body(url, today_str) → {body, body_status, body_source_url, body_extracted_at, error}
  enrich_image(record, today_str) → {image_url, image_path, image_status, ...}
  enrich_records(records, today_str) → [updated_records], {stats}（主聚合函数）
  enrich_archive(today_str, missing_only, ...) → 读 JSONL → enrich_records → 写回
  enrich_archive_best_effort(today_str, ...) → 180s 预算内静默跑
```

## 注意事项
- 正文补全仅在 `archive_articles` 完成之后调用（通过 step4 run() 尾部的 try/except）
- 首图仅补 top10 文章；非 top10 自动 `image_status=not_selected`
- `download_image` 按 Content-Type 映射扩展名，`image_path` 以最终写入路径为准
- `max_seconds=0` 表示无限制，`max_seconds>0` 时超出精度跳过剩余
- 不影响 `1新闻_链接.md` / `2新闻_已审核.md` / `3新闻_概述.md` / HTML / PNG 格式

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
