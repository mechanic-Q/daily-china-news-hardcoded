---
id: task-02
title: 在 step4.py 自动流程禁用图片增强
author: lmr
created_at: 2026-07-03 14:47:33
priority: P0
depends_on: [task-01]
blocks: []
requirement_ids: [FR-01, FR-02]
decision_ids: [D-001@v1, D-002@v2]
allowed_paths:
  - step4.py
goal: >
  让 step4 自动归档增强传 include_images=False，不再下载图片但继续正文增强。
implementation:
  - 修改 step4.py 尾部 archive_enrich.enrich_archive_best_effort 调用。
  - 在调用中增加 include_images=False。
  - 保留现有 try/except 结构和调用顺序。
acceptance:
  - step4.py 调用传 include_images=False。
  - archive_articles_best_effort 调用不变，正文归档增强仍执行。
verify:
  - python3 -m unittest discover -s tests -p 'test_archive_enrich.py' -v
constraints:
  - 不删除 archive_articles_best_effort。
  - 不跳过正文增强，不修改 run_all.sh。
---
## Acceptance
- See frontmatter acceptance.
## Verify
- See frontmatter verify.
