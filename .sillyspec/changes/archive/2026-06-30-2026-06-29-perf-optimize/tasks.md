---
author: lmr
created_at: 2026-06-30 01:29:41
change: 2026-06-29-perf-optimize
doc_type: tasks
---

# Tasks

- task-01: 为 `step6.py` 新增并发常量与单篇正文提取 worker（覆盖 FR-01, FR-05, D-002@v1, D-004@v1）
- task-02: 改造 `step6.py run()` 使用 ThreadPoolExecutor 并保持输出顺序与失败占位（覆盖 FR-01, FR-04, D-001@v1, D-003@v1）
- task-03: 为 `step7.py` 新增并发常量与单篇摘要 worker（覆盖 FR-02, FR-05, D-002@v1, D-004@v1）
- task-04: 改造 `step7.py run()` 使用 ThreadPoolExecutor 并保持栏目顺序与 fallback 语义（覆盖 FR-02, FR-04, D-001@v1, D-003@v1）
- task-05: 验证 step6/step7 语法、dry-run、Markdown 契约与失败语义（覆盖 FR-03, FR-04, FR-05）
- task-06: 使用 `perf_profile.py` 记录前后性能对比并写验证结论（覆盖 FR-06, D-001@v1）
