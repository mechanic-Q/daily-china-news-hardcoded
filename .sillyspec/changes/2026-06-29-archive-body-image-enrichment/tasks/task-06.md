---
id: task-06
title: 实现 JSONL enrich 读写与统计（覆盖：FR-05, FR-06, FR-09, D-004@v1, D-005@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-04, task-05]
blocks: [task-07, task-08]
requirement_ids: [FR-05, FR-06, FR-09]
decision_ids: [D-004@v1, D-005@v1]
allowed_paths:
  - archive_enrich.py
  - tests/test_archive_enrich.py
goal: >
  串联正文和首图补全，完成 archive JSONL 读写、统计、dry-run、missing-only、时间预算和 best-effort 包装。
implementation:
  - 实现 enrich_records，按 date 处理 records 并返回 updated_records/stats
  - 实现 max_seconds 预算，超时将剩余待处理项标记 skipped
  - 实现 enrich_archive，读取 month JSONL、筛选日期、写回文件
  - 实现 enrich_archive_best_effort，catch all 后只打印 warning
  - main 解析 CLI 并调用 enrich_archive
acceptance:
  - --dry-run 只打印统计，不写 JSONL，不下载图片
  - --missing-only 跳过已 extracted/downloaded 的记录
  - --max-seconds 超时后保留已完成结果并标记剩余 skipped
  - best_effort 内异常不向调用方抛出
verify:
  - python3 tests/test_archive_enrich.py
  - python3 archive_enrich.py --date 2026-06-29 --dry-run
constraints:
  - 不修改 news_archive.py 或 step4.py
  - 不新增第三方依赖
  - enrich_records 保持可测试，不直接读取 sys.argv
---
