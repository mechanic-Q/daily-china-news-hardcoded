---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-03-phase-15c-async-fetch
phase: 15c
status: brainstorm-skeleton
---

# Tasks · Phase 15C · async fetch performance

> 待 plan 阶段展开。

- [ ] T-01 · 新增 httpx/tenacity 依赖
  - 文件：`requirements.txt`
  - 覆盖：FR-01, FR-02

- [ ] T-02 · 建立 step1 timing baseline
  - 文件：`tests/manual/test_15c_step1_timing.py`
  - 覆盖：FR-04

- [ ] T-03 · 改造批量 HTTP 请求为受控并发
  - 文件：`step1_3.py`
  - 覆盖：FR-01, FR-02

- [ ] T-04 · 实现 static-first Chromium fallback
  - 文件：`step1_3.py`, `daily/http.py`（如需）
  - 覆盖：FR-03

- [ ] T-05 · 验证输出格式与耗时
  - 文件：无
  - 覆盖：全部
