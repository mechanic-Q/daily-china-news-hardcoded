---
author: lmr
created_at: 2026-06-27 15:55:00
schema_version: 1
doc_type: tasks
change_id: 2026-06-27-column-scoring-v2
phase: 13
---

# Tasks · Phase 13 栏目评分 v2

任务粒度仅到"做什么 + 改哪些文件 + 覆盖哪些 FR/D"，具体步骤、伪代码、检查点在 plan 阶段展开。

## Wave 1 — 常量同步（基础设施）

### task-01: COLUMN_ORDER 三处同步加 🤖
- 文件：`step4.py` / `step7.py` / `step8.py`
- 覆盖：FR-05, D-012@v1, D-017@v1
- 验收：AC-07

### task-02: llm.yaml 新增 column-score call site
- 文件：`llm.yaml`
- 覆盖：FR-10, D-002@v1, D-008@v1
- 验收：AC-06

## Wave 2 — 关键词词典调整

### task-03: CATEGORY_KEYWORDS 扩 🤖 词典 + 调 🚀
- 文件：`step4.py`（CATEGORY_KEYWORDS 字典）
- 覆盖：FR-09, D-013@v1, D-014@v1
- 验收：AC-12
- 注：保留其他 7 栏词典不动；新增 🤖 至少 30 词条；🚀 剥离 AI/智能制造类、新增 CPU/OS 类

## Wave 3 — 核心评分链（新逻辑）

### task-04: 实现 score_signals + Schema 校验
- 文件：`step4.py`（新增 `_build_score_prompt` / `score_signals` / `_validate_signals` / `_strip_think` / `_strip_codefence`）
- 覆盖：FR-01, FR-02, D-002@v1, D-011@v1, D-018@v1, D-019@v1
- 验收：AC-03

### task-05: 实现 aggregate_scores
- 文件：`step4.py`（新增 `aggregate_scores`，含 AGG_RELEV_BASE/AGG_IMP_W/AGG_TIME_W 常量）
- 覆盖：FR-03, D-003@v1, D-007@v1
- 验收：AC-04

### task-06: 实现 assign_category（方案 X 抢占）
- 文件：`step4.py`（新增 `assign_category`、WORLD_CLASS_THRESHOLD 常量）
- 覆盖：FR-04, D-015@v1
- 验收：AC-09, AC-10

## Wave 4 — 集成与降级

### task-07: 重写 run() 评分链路
- 文件：`step4.py`（修改 `run()` 中 Phase 1-3 逻辑，替换为 score_signals → aggregate → assign_category；保留 legacy_path 作降级）
- 覆盖：FR-01, FR-07, FR-08, D-004@v1, D-006@v1, D-009@v1
- 验收：AC-01, AC-02, AC-05

### task-08: 空栏目消失 — run() 输出逻辑
- 文件：`step4.py`（`run()` 末尾写 md 时跳过空栏目）
- 覆盖：FR-06, D-016@v1
- 验收：AC-11

## Wave 5 — 测试与验证

### task-09: 新增 tests/test_column_scoring.py
- 文件：`tests/test_column_scoring.py`（新增）
- 覆盖：FR-11，全部 AC
- 验收：脚本可独立 `python3 tests/test_column_scoring.py` 跑通

### task-10: dry-run 集成验证
- 文件：无（仅运行）
- 命令：
  - `python3 step4.py --date 2026-06-25 --dry-run`
  - `python3 step4.py --date 2026-06-26 --dry-run`
  - `time python3 step4.py --date <today>`
- 覆盖：S-02, S-08
- 验收：AC-01, AC-05

### task-11: 风格一致性扫描
- 文件：无（仅扫描）
- 命令：`rg "^from typing\|-> (dict|str|int|None|list|tuple|bool)" step4.py`
- 覆盖：D-010@v1
- 验收：AC-08

- [x] ql-20260704-002-a4d1 强制采集见报/发布日期为当天的新闻
- [x] ql-20260704-003-ef92 Step7 新闻概述正文删除习近平三字
