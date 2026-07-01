---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
status: brainstorm-skeleton
---

# Tasks · Phase 15D · source health monitoring

> 待 plan 阶段展开。

- [ ] T-01 · 定义 health JSONL helper
  - 文件：`step1_3.py` 或新 `daily/source_health.py`（正式 brainstorm 决策）
  - 覆盖：FR-01

- [ ] T-02 · step1_3 写入 health 并显示 banner
  - 文件：`step1_3.py`
  - 覆盖：FR-01, FR-02

- [ ] T-03 · monthly_report 读取并渲染 health stats
  - 文件：`monthly_report.py`
  - 覆盖：FR-03

- [ ] T-04 · monthly_report 接入 llm_client
  - 文件：`monthly_report.py`, `llm.yaml`
  - 覆盖：FR-04

- [ ] T-05 · manual health test
  - 文件：`tests/manual/test_15d_source_health.py`
  - 覆盖：全部
