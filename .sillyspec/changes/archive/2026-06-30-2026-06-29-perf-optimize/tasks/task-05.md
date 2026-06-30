---
id: task-05
title: 验证 step6/step7 语法、dry-run、Markdown 契约与失败语义
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: [task-02, task-04]
blocks: [task-06]
requirement_ids: [FR-03, FR-04, FR-05]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths: [step6.py, step7.py, .sillyspec/changes/2026-06-29-perf-optimize/verify-result.md]
goal: >
  验证 step6/step7 并发改造后语法、dry-run、Markdown 契约、失败占位与 fallback 语义均保持兼容。
implementation:
  - 运行 py_compile 检查 step6.py 和 step7.py。
  - 分别运行 step6.py 与 step7.py dry-run，检查输出顺序与栏目顺序。
  - 将验证命令、结果和环境限制写入 verify-result.md。
## 验收标准
acceptance:
  - py_compile 通过。
  - step6 dry-run 可运行且正文输出顺序不漂移。
  - step7 dry-run 可运行且栏目顺序、fallback 语义不漂移。
verify:
  - python3 -m py_compile step6.py step7.py
  - python3 step6.py --date $(date +%Y-%m-%d) --dry-run
  - python3 step7.py --date $(date +%Y-%m-%d) --dry-run
constraints:
  - 本任务不改业务代码，只写 verify-result.md。
  - 若真实网络或 LLM 不可用，记录环境限制。
  - 不新增测试框架或依赖。
---
