---
id: task-01
title: 为 step6.py 新增并发常量与单篇正文提取 worker
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: []
blocks: [task-02]
requirement_ids: [FR-01, FR-05]
decision_ids: [D-002@v1, D-004@v1]
allowed_paths: [step6.py]
goal: >
  在 step6.py 中新增保守并发常量和单篇正文提取 worker，供后续 run() 并发调度复用。
implementation:
  - 在模块常量区新增 STEP6_MAX_WORKERS = 4。
  - 在 fetch_and_extract() 之后新增 extract_article_worker(index, article)。
  - worker 调用 fetch_and_extract(article['url'], article['title']) 并返回 index、body、err。
## 验收标准
acceptance:
  - STEP6_MAX_WORKERS 存在且值为 4。
  - extract_article_worker 返回 index、body、err 三元组。
  - fetch_and_extract() 签名和返回值未变。
verify:
  - python3 -m py_compile step6.py
  - python3 step6.py --date $(date +%Y-%m-%d) --dry-run
constraints:
  - 不修改 run() 主循环；task-02 负责调度改造。
  - 不修改 fetch_and_extract、extract_body、needs_chromium 签名。
  - worker 不写文件、不打印进度、只返回结果。
---
