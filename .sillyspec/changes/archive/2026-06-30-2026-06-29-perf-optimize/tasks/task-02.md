---
id: task-02
title: 改造 step6.py run() 使用线程池并保持输出顺序与失败占位
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: [task-01]
blocks: [task-05, task-06]
requirement_ids: [FR-01, FR-04]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths: [step6.py]
goal: >
  将 step6.py 的正文提取循环改为 ThreadPoolExecutor 并发，同时保持 Markdown 输出顺序和失败占位语义。
implementation:
  - 在 run() 使用 ThreadPoolExecutor 和 as_completed 提交 extract_article_worker。
  - 用 worker 返回的 index 回填 articles，按原 articles 顺序打印和写入。
  - 保留 output_path、dry-run 预览、成功计数和 Markdown 生成逻辑。
## 验收标准
acceptance:
  - run() 使用 STEP6_MAX_WORKERS 受限并发处理文章。
  - 2新闻_已审核.md 文章顺序与 1新闻_链接.md 一致。
  - 单篇失败仍写 [正文提取失败: ...] 且不阻断其他文章。
verify:
  - python3 -m py_compile step6.py
  - python3 step6.py --date $(date +%Y-%m-%d) --dry-run
constraints:
  - 不改 fetch_and_extract、extract_body、needs_chromium 行为。
  - 不引入 asyncio、Playwright、Selenium 或新第三方依赖。
  - 并发 worker 不直接写最终文件。
---
