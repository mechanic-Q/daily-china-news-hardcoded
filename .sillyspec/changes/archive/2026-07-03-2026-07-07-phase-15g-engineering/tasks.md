---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
status: brainstorm-skeleton
---

# Tasks · Phase 15G · engineering hardening

> 待 plan 阶段展开。

- [ ] T-01 · 确认 logging 工具并接入
  - 文件：`requirements.txt`, `daily/logging.py`（如需要）, 多个 step
  - 覆盖：FR-01

- [ ] T-02 · LLM 异常脱敏
  - 文件：`llm_client.py`
  - 覆盖：FR-02

- [ ] T-03 · Archive schema migration
  - 文件：`news_archive.py`, `tests/test_news_archive.py`
  - 覆盖：FR-03

- [ ] T-04 · 扩充关键单元测试
  - 文件：`tests/*.py`
  - 覆盖：全部

- [ ] T-05 · GitHub Actions CI
  - 文件：`.github/workflows/test.yml`
  - 覆盖：FR-04
