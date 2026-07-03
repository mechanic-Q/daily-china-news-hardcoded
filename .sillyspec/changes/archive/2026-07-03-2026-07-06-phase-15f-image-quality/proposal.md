---
author: lmr
created_at: 2026-07-03 14:44:13
schema_version: 1
doc_type: proposal
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
depends_on:
  - 2026-07-01-phase-15a-common-lib
  - 2026-07-02-phase-15b-trafilatura-body
status: design-confirmed
---

# Proposal · Phase 15F · disable automatic image collection

## 动机

当前 `step4.py` 在写入精选新闻后调用 `archive_enrich.enrich_archive_best_effort()`。该 best-effort 流程会补正文，也会为 top10 新闻抽取图片 URL、下载图片并写入 `archive/images/YYYY-MM/`。

现在归档仍需要正文增强，但不再需要自动收集图片。继续下载图片会增加网络请求、磁盘写入和 180s 自动归档预算消耗，还会保留用户当前不想使用的图片资产。

## 关键问题

1. `archive_enrich.enrich_archive_best_effort()` 同时包含正文增强和图片增强，`step4.py` 无法只启用正文。
2. 直接删除 `step4.py` 的归档增强调用会同时关闭正文增强，不符合目标。
3. 全局禁用 `should_enrich_image()` 会影响 `archive_enrich.py` 直接 CLI 行为，破坏兼容。

## 变更范围

- 给 `archive_enrich.enrich_records()`、`enrich_archive()`、`enrich_archive_best_effort()` 增加 `include_images=True` 参数。
- `include_images=False` 时跳过图片 URL 提取、图片下载和图片字段更新分支。
- `step4.py` 自动流程调用 `enrich_archive_best_effort(..., include_images=False)`。

## 不在范围内

- 不删除历史 `image_url`、`image_path` 或本地图片文件。
- 不改 `archive/articles/YYYY-MM.jsonl` schema。
- 不新增 `image_status` 状态。
- 不禁用 `python3 archive_enrich.py --date ...` 的默认图片增强能力。
- 不改月报图片统计展示逻辑。

## 成功标准

- `step4.py` 自动流程仍执行正文归档增强。
- `step4.py` 自动流程不再触发 `extract_first_image_url()`、`download_image()` 或 `archive/images/YYYY-MM/` 新图片写入。
- `archive_enrich.py` 直接 CLI 默认行为保持兼容，仍可在显式运行时收集图片。
- 现有 archive enrichment 单测继续通过。
