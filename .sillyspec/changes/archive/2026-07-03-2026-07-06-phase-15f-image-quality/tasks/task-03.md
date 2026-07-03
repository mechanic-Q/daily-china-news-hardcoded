---
id: task-03
title: 增加 archive enrichment 回归测试
author: lmr
created_at: 2026-07-03 14:47:33
priority: P0
depends_on: [task-01, task-02]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-001@v1, D-002@v2]
allowed_paths:
  - tests/test_archive_enrich.py
goal: >
  添加回归测试，证明 include_images=False 跳过图片增强但保留正文增强，默认 True 仍调用图片分支。
implementation:
  - 在 TestEnrichRecords 增加 body-only mock 测试。
  - 在 TestEnrichRecords 增加默认图片分支 mock 测试。
  - 在 TestEnrichArchiveBestEffort 增加 include_images 参数透传测试。
acceptance:
  - include_images=False 跳过 enrich_image 并调用 enrich_body。
  - 默认路径调用 enrich_image，include_images 通过 best_effort 传到 enrich_archive。
verify:
  - python3 -m unittest discover -s tests -p 'test_archive_enrich.py' -v
constraints:
  - 只使用 unittest/unittest.mock，不引入新测试框架。
  - 不触网，不写真实 archive/images。
---
## Acceptance
- See frontmatter acceptance.
## Verify
- See frontmatter verify.
