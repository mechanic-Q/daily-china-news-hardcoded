---
author: lmr
created_at: 2026-06-27 20:53:53
schema_version: 1
doc_type: tasks
change_id: 2026-06-27-news-archive-core
phase: 14A
---

# Tasks

## Wave 1 — Archive helper

### task-01: 新增 news_archive.py 常量与 URL/id 工具
- 文件路径：`news_archive.py`
- 覆盖：FR-03, D-002@v1
- 内容：`BASE_DIR` / `ARCHIVE_DIR` / `ARTICLES_DIR` / `SCHEMA_VERSION` / `normalize_url` / `article_id` / `month_path`

### task-02: 新增 news_archive.py record 构造
- 文件路径：`news_archive.py`
- 覆盖：FR-02, FR-08, D-002@v1, D-009@v1
- 内容：`infer_source` / `build_record`，不 import step4

### task-03: 新增 news_archive.py JSONL load/write/upsert
- 文件路径：`news_archive.py`
- 覆盖：FR-04, D-008@v1
- 内容：`load_month_records` / `write_month_records` / `archive_articles`，支持幂等 upsert、保留 archived_at、刷新 updated_at

### task-04: 新增 news_archive.py best-effort wrapper
- 文件路径：`news_archive.py`
- 覆盖：FR-05, D-003@v1, D-006@v1, D-007@v1
- 内容：`archive_articles_best_effort` 捕获所有异常，打印 warning，不 raise

## Wave 2 — step4 integration

### task-05: step4 提取 build_classification_result(today)
- 文件路径：`step4.py`
- 覆盖：FR-06, D-010@v1
- 内容：把现有/Phase13 分类逻辑提取为纯数据函数，返回 `(classified, selected)`，不写文件、不触发 archive

### task-06: step4.run() 接入 build_classification_result 与归档调用
- 文件路径：`step4.py`
- 覆盖：FR-05, FR-06, D-003@v1, D-006@v1, D-007@v1
- 内容：`run()` 复用 `build_classification_result`，保留原写 `1新闻_链接.md` 行为，并 best-effort 调 `news_archive.archive_articles_best_effort`

## Wave 3 — Backfill CLI

### task-07: 新增 archive_news.py CLI
- 文件路径：`archive_news.py`
- 覆盖：FR-07, D-004@v1, D-010@v1
- 内容：手写 `parse_args` 支持 `--date` / `--dry-run`，调用 `step4.build_classification_result` + `news_archive.archive_articles`

## Wave 4 — Tests

### task-08: 新增 tests/test_news_archive.py
- 文件路径：`tests/test_news_archive.py`
- 覆盖：FR-09, D-001@v1 ~ D-010@v1
- 内容：测试 URL normalize、id 稳定性、record 字段、selected_in_top10、JSONL upsert、archived_at/updated_at、dry-run、best-effort

### task-09: 运行静态/单元验证
- 文件路径：无
- 覆盖：FR-09
- 内容：执行 `python3 tests/test_news_archive.py`；确认 `run_all.sh` 无 diff；检查 `rg "from step4" news_archive.py` 为空；检查 `rg "->" news_archive.py archive_news.py` 无 type hints
