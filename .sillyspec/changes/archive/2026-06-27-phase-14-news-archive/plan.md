---
author: lmr
created_at: 2026-06-28 02:10:23
schema_version: 1
doc_type: plan
change_id: 2026-06-27-news-archive-core
phase: 14A
plan_level: full
---

# 实现计划 · Phase 14A News Archive Core

## Wave 1 — Archive helper（无依赖，4 个 task 并行）

- [x] task-01: 新增 news_archive.py 常量与 URL/id 工具（覆盖：FR-03, D-002@v1）
- [x] task-02: 新增 news_archive.py record 构造（覆盖：FR-02, FR-08, D-002@v1, D-009@v1）
- [x] task-03: 新增 news_archive.py JSONL load/write/upsert（覆盖：FR-04, D-008@v1）
- [x] task-04: 新增 news_archive.py best-effort wrapper（覆盖：FR-05, D-003@v1, D-006@v1, D-007@v1）

## Wave 2 — step4 集成（依赖 Wave 1 全部完成）

- [x] task-05: step4 提取 build_classification_result(today)（覆盖：FR-06, D-010@v1）
- [x] task-06: step4.run() 接入 build_classification_result 与归档调用（覆盖：FR-05, FR-06, D-003@v1, D-006@v1, D-007@v1）

## Wave 3 — Backfill CLI（依赖 Wave 2）

- [x] task-07: 新增 archive_news.py CLI（覆盖：FR-07, D-004@v1, D-010@v1）

## Wave 4 — 测试与验证（依赖 Wave 1-3 全部完成）

- [x] task-08: 新增 tests/test_news_archive.py（覆盖：FR-09, D-001@v1 ~ D-010@v1）
- [x] task-09: 运行静态/单元验证（覆盖：FR-09）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|------|------|------|--------|------|-----------|------|
| task-01 | news_archive 常量/URL/id 工具 | W1 | P0 | — | FR-03, D-002@v1 | BASE_DIR/ARCHIVE_DIR/ARTICLES_DIR/SCHEMA_VERSION/normalize_url/article_id/month_path |
| task-02 | news_archive record 构造 | W1 | P0 | — | FR-02, FR-08, D-002@v1, D-009@v1 | infer_source/build_record，不 import step4 |
| task-03 | news_archive JSONL load/write/upsert | W1 | P0 | task-01 | FR-04, D-008@v1 | load_month_records/write_month_records/archive_articles，幂等 upsert |
| task-04 | news_archive best-effort wrapper | W1 | P0 | task-01,02,03 | FR-05, D-003@v1, D-006@v1, D-007@v1 | archive_articles_best_effort 捕所有异常不 raise |
| task-05 | step4 build_classification_result | W2 | P0 | task-01~04 | FR-06, D-010@v1 | 提取纯数据函数返回 (classified, selected) |
| task-06 | step4.run() 接入归档 | W2 | P0 | task-05 | FR-05, FR-06, D-003@v1, D-006@v1, D-007@v1 | run() 复用 build_classification_result，best-effort 调归档 |
| task-07 | archive_news.py CLI | W3 | P1 | task-05 | FR-07, D-004@v1, D-010@v1 | 独立补跑 --date/--dry-run，不写 1新闻_链接.md |
| task-08 | tests/test_news_archive.py | W4 | P0 | task-01~07 | FR-09, D-001~D-010 | URL normalize/id 稳定/record 字段/selected_in_top10/upsert/best-effort |
| task-09 | 静态/单元验证 | W4 | P2 | task-08 | FR-09 | python3 tests/test_news_archive.py；rg 检查 import step4/type hints |

## 关键路径

`task-01 → task-03 → task-04 → task-05 → task-06 → task-08 → task-09`（7 步，关键路径）

## 全局验收标准

- `news_archive.py` 不含 `import step4`
- `news_archive.py` / `archive_news.py` 无 type hints
- 同 URL 重复补跑幂等（archived_at 不变，updated_at 刷新）
- 归档失败不阻断 step4 或 run_all.sh
- `archive_news.py --date YYYY-MM-DD --dry-run` 可独立运行
- `python3 tests/test_news_archive.py` 全部通过
- `run_all.sh` 无 diff

## 覆盖矩阵

| 决策 ID | 覆盖任务 | 验收证据 |
|---------|----------|----------|
| D-001@v1 | task-01~09 | Phase 14A 总范围（不做正文/图片/月报） |
| D-002@v1 | task-01, task-02 | metadata-only record schema |
| D-003@v1 | task-04, task-06 | best-effort 不阻断日报 |
| D-004@v1 | task-07 | archive_news.py --date 独立补跑 |
| D-005@v1 | (前置) | Phase 13 代码已落地 (commit 04a2180) |
| D-006@v1 | task-04, task-06 | helper module 方案 B |
| D-007@v1 | task-04, task-06 | 不改 run_all.sh |
| D-008@v1 | task-03 | archived_at 保留 + updated_at 刷新 |
| D-009@v1 | task-02 | news_archive 不 import step4 |
| D-010@v1 | task-05, task-07 | build_classification_result 共享函数 |
