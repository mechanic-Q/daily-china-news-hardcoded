---
id: task-03
title: compute_stats + top_keywords
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-02]
blocks: [task-04, task-05, task-07, task-08, task-09]
requirement_ids: [FR-03]
decision_ids: [D-002@v1, D-006@v1]
allowed_paths: [monthly_report.py]
goal: >
  一次遍历 records 聚合月度统计，关键词命中用 step4 既有 CATEGORY_KEYWORDS 词库，不引入 jieba。
implementation:
  - compute_stats(records, month) 一次遍历输出 dict 含 month/total_records/by_column/by_source/by_date/body_coverage/image_coverage/top_keywords
  - by_column / by_source 按计数倒序排序后转 dict
  - body_coverage = {extracted, failed, missing, skipped} 4 keys
  - image_coverage = {downloaded, not_selected, not_found, failed, missing, skipped} 6 keys
  - top_keywords(records, limit=20) 从 step4.CATEGORY_KEYWORDS 收集扁平词集合，在 title + body[:BODY_SNIPPET_CHARS] 上做子串命中计数，按计数倒序取前 limit
  - 从 step4 导入 CATEGORY_KEYWORDS 字典；导入失败用空词典并 print warning（不致命）
acceptance:
  - compute_stats 输出 dict 含上述 8 键
  - by_column / by_source 倒序
  - top_keywords 命中数全为正整数
  - 不修改输入 record
verify:
  - 单测构造 5 条 record → 验证 stats 字段、计数、排序
constraints:
  - 不调 LLM
  - 不引入 jieba/pandas/numpy
  - 不修改 record
  - 词库导入失败仍能继续（top_keywords 返回空）
