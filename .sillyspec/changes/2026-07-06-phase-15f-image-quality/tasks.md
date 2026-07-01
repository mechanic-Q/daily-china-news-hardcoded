---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: tasks
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: brainstorm-skeleton
---

# Tasks · Phase 15F · image quality

> 待 plan 阶段展开。

- [ ] T-01 · 定义图片候选提取顺序
  - 文件：`archive_enrich.py`
  - 覆盖：FR-01

- [ ] T-02 · 实现 URL/路径黑名单过滤
  - 文件：`archive_enrich.py`
  - 覆盖：FR-02

- [ ] T-03 · 实现 Pillow 尺寸校验与小图删除
  - 文件：`archive_enrich.py`
  - 覆盖：FR-02, FR-04

- [ ] T-04 · 保持 image_status 兼容
  - 文件：`archive_enrich.py`
  - 覆盖：FR-03

- [ ] T-05 · manual top10 图片抽样脚本
  - 文件：`tests/manual/test_15f_image_sample.py`
  - 覆盖：全部
