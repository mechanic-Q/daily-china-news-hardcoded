---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
doc_type: tasks
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# Tasks

## Wave 1 — Schema + preservation

### task-01: news_archive schema v2 与 IMAGES_DIR
- 文件路径：`news_archive.py`
- 覆盖：FR-09, D-006@v1
- 内容：`SCHEMA_VERSION=2`，新增/导出 `IMAGES_DIR`

### task-02: 14A upsert 保留 14B enrichment 字段
- 文件路径：`news_archive.py`
- 覆盖：FR-07, D-006@v1
- 内容：修改 `archive_articles` 合并逻辑，保留已有 `body*` / `image*` 字段

## Wave 2 — archive_enrich core

### task-03: 新增 archive_enrich.py CLI 与路径工具
- 文件路径：`archive_enrich.py`
- 覆盖：FR-05, FR-09, D-004@v1
- 内容：手写 `parse_args` 支持 `--date` / `--missing-only` / `--dry-run` / `--max-seconds`；实现 `image_month_dir`

### task-04: 实现正文补全状态机
- 文件路径：`archive_enrich.py`
- 覆盖：FR-01, FR-02, D-001@v1, D-002@v1
- 内容：`should_enrich_body` / `enrich_body`，复用 `step6.fetch_and_extract`，失败只写 status/error

### task-05: 实现首图提取与下载
- 文件路径：`archive_enrich.py`
- 覆盖：FR-03, FR-04, FR-08, D-003@v1, D-007@v1
- 内容：`fetch_html_for_image` / `extract_first_image_url` / `download_image` / `enrich_image`

### task-06: 实现 JSONL enrich 读写与统计
- 文件路径：`archive_enrich.py`
- 覆盖：FR-05, FR-06, FR-09, D-004@v1, D-005@v1
- 内容：`enrich_records` / `enrich_archive` / `enrich_archive_best_effort`，支持 missing-only、dry-run、max-seconds

## Wave 3 — pipeline integration

### task-07: step4 接入 archive_enrich best-effort
- 文件路径：`step4.py`
- 覆盖：FR-06, D-005@v1
- 内容：14A `archive_articles_best_effort` 后调用 `archive_enrich.enrich_archive_best_effort`

## Wave 4 — Tests

### task-08: 新增 tests/test_archive_enrich.py
- 文件路径：`tests/test_archive_enrich.py`
- 覆盖：FR-01 ~ FR-06, FR-08, FR-09, D-001@v1 ~ D-005@v1, D-007@v1
- 内容：正文成功/失败、禁止 fake body、top10 图片、非 top10 not_selected、dry-run、missing-only、best-effort、max-seconds

### task-09: 扩展 tests/test_news_archive.py
- 文件路径：`tests/test_news_archive.py`
- 覆盖：FR-07, FR-09, D-006@v1
- 内容：14A upsert 不覆盖已存在 body/image 字段；schema_version v2 兼容

### task-10: 运行验证命令
- 文件路径：无
- 覆盖：FR-01 ~ FR-09
- 内容：执行 `python3 tests/test_news_archive.py`、`python3 tests/test_archive_enrich.py`；如可行，执行 `python3 archive_enrich.py --date <test-date> --dry-run`
