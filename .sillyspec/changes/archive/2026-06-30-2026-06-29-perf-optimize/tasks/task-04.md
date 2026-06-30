---
id: task-04
title: 改造 step7.py run() 使用线程池并保持栏目顺序与 fallback 语义
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: [task-03]
blocks: [task-05, task-06]
requirement_ids: [FR-02, FR-04]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths: [step7.py]
goal: >
  将 step7.py 的摘要循环改为 ThreadPoolExecutor 并发，同时保持 COLUMN_ORDER 输出和 fallback 行为。
implementation:
  - 在 run() 使用 ThreadPoolExecutor 和 as_completed 提交 summarize_article_worker。
  - 用 worker 返回的 index 回填 matched 的 summary 与 fallback 字段。
  - 保留 COLUMN_ORDER 分栏目输出和 3新闻_概述.md 写入逻辑。
## 验收标准
acceptance:
  - run() 使用 STEP7_MAX_WORKERS 受限并发处理 matched。
  - 3新闻_概述.md 仍按 COLUMN_ORDER 分栏目输出。
  - 单篇摘要失败仍走 fallback_summarize 且不阻断其他文章。
verify:
  - python3 -m py_compile step7.py
  - python3 step7.py --date $(date +%Y-%m-%d) --dry-run
constraints:
  - 不改 parse_1news、parse_2news、llm_summarize、fallback_summarize 签名。
  - 不修改 Markdown 格式、COLUMN_ORDER 或 run_all.sh。
  - 不引入 asyncio 或新第三方依赖。
---
