---
id: task-04
title: pick_top_per_column 排序键
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-02, task-03]
blocks: [task-05, task-07, task-08, task-09]
requirement_ids: [FR-04]
decision_ids: [D-002@v1]
allowed_paths: [monthly_report.py]
goal: >
  按栏目分组挑选每栏目 top_n 条代表新闻，四级排序键确定优先级。
implementation:
  - pick_top_per_column(records, top_n) → dict[column] = list[record]
  - 按 record["column"] 分组（空 column 归入 "(未分类)"）
  - 排序键（降序）：(selected_in_top10 True 优先, aggregate_score 数值高优先, body_status=='extracted' 优先, archived_at 倒序)
  - 每组取前 top_n
  - 输出按 COLUMN_ORDER 顺序排列；不在 COLUMN_ORDER 的栏目追加在末尾
acceptance:
  - 同一栏目结果长度 ≤ top_n
  - 空栏目返回 [] 但保留 key
  - 输入 records 不被修改
  - 输出顺序：COLUMN_ORDER 优先，外部栏目追加
verify:
  - 单测：构造 3 栏目 ×5 篇 → top_n=2 → 每栏目 2 篇；排序键互换样本
constraints:
  - 不修改 record
  - 不调 LLM/IO
  - 不依赖 step8/step4
