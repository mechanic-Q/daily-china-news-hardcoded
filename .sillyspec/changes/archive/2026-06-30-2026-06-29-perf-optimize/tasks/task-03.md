---
id: task-03
title: 为 step7.py 新增并发常量与单篇摘要 worker
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: []
blocks: [task-04]
requirement_ids: [FR-02, FR-05]
decision_ids: [D-002@v1, D-004@v1]
allowed_paths: [step7.py]
goal: >
  在 step7.py 中新增保守并发常量和单篇摘要 worker，保留 LLM 重试与 fallback 语义。
implementation:
  - 在模块常量区新增 STEP7_MAX_WORKERS = 3。
  - 新增 summarize_article_worker(index, article)。
  - worker 调用 llm_summarize；空结果时调用 fallback_summarize 并返回 fallback 标记。
## 验收标准
acceptance:
  - STEP7_MAX_WORKERS 存在且值为 3。
  - summarize_article_worker 返回 index、summary、fallback 三元组。
  - llm_summarize 和 fallback_summarize 签名未变。
verify:
  - python3 -m py_compile step7.py
  - python3 step7.py --date $(date +%Y-%m-%d) --dry-run
constraints:
  - worker 不写文件、不修改 COLUMN_ORDER、不打印全局进度。
  - 不新增依赖，不改 LLM prompt、重试次数或 fallback 规则。
  - task-04 才改 run() 调度逻辑。
---
