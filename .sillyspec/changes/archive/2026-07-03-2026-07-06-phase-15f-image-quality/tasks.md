---
author: lmr
created_at: 2026-07-03 14:44:13
schema_version: 1
doc_type: tasks
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: design-confirmed
---

# Tasks · Phase 15F · disable automatic image collection

> 待 plan 阶段展开。

- [ ] T-01 · 为 `archive_enrich` 调用链增加图片开关
  - 文件：`archive_enrich.py`
  - 覆盖：FR-01, FR-02, FR-03
  - 覆盖决策：D-001@v1, D-002@v2

- [ ] T-02 · 在 `step4.py` 自动流程禁用图片增强
  - 文件：`step4.py`
  - 覆盖：FR-01, FR-02
  - 覆盖决策：D-001@v1, D-002@v2

- [ ] T-03 · 增加 body-only 行为回归测试
  - 文件：`tests/test_archive_enrich.py`
  - 覆盖：FR-01, FR-02, FR-03
  - 覆盖决策：D-001@v1, D-002@v2
