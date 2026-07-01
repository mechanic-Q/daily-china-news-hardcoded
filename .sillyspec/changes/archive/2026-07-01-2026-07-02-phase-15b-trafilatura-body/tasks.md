---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-02-phase-15b-trafilatura-body
phase: 15b
status: brainstorm-skeleton
---

# Tasks · Phase 15B · trafilatura body extraction

> 待 plan 阶段展开。

- [ ] T-01 · 新增 trafilatura 依赖
  - 文件：`requirements.txt`
  - 覆盖：FR-01

- [ ] T-02 · 建立 golden set
  - 文件：`tests/fixtures/body_golden.jsonl`
  - 覆盖：FR-04

- [ ] T-03 · 重写 step6 正文提取核心
  - 文件：`step6.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-04

- [ ] T-04 · 新增 manual golden test
  - 文件：`tests/manual/test_15b_body_golden.py`
  - 覆盖：FR-01, FR-04

- [ ] T-05 · 验证 step6 与完整 run_all dry-run
  - 文件：无
  - 覆盖：全部
