---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
status: brainstorm-skeleton
---

# Tasks · Phase 15E · LLM batching

> 待 plan 阶段展开。

- [ ] T-01 · 加入 LLM 调用计数/基线脚本
  - 文件：`tests/manual/test_15e_llm_call_count.py`
  - 覆盖：FR-01, FR-02, FR-03

- [ ] T-02 · step4 高置信度直通
  - 文件：`step4.py`
  - 覆盖：FR-01

- [ ] T-03 · step4 批量涉华判断
  - 文件：`step4.py`
  - 覆盖：FR-02, FR-04

- [ ] T-04 · step4 批量栏目分类/评分
  - 文件：`step4.py`
  - 覆盖：FR-03, FR-04

- [ ] T-05 · step7 摘要并发
  - 文件：`step7.py`
  - 覆盖：FR-05

- [ ] T-06 · 输出差异对比与验证
  - 文件：无
  - 覆盖：全部
