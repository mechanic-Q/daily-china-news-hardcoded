---
id: task-06
title: 验证 `fetch_and_extract` 签名、返回语义与 `2新闻_已审核.md` 格式不变（覆盖：FR-04, D-003@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on:
  - task-04
  - task-05
blocks:
  - task-07
requirement_ids:
  - FR-04
decision_ids:
  - D-003@v1
allowed_paths:
  - step6.py
  - tests/manual/test_15b_body_golden.py
---

goal: |
  确保 task-04/task-05 完成后 `fetch_and_extract` 接口与 `2新闻_已审核.md` 输出格式不变，下游无修改。
implementation:
  - 签名检查：`def fetch_and_extract(url, title)` 保持双参数，无 *args/**kwargs，无新增必选参数。
  - 返回语义检查：`return (body, None)` 成功 / `return (None, reason)` 失败不变，类型 `(str|None, str|None)`。
  - 输出格式检查：step6.py run() 输出 markdown 仍含 `## 【{src}】{title}` / `来源：` / `发布时间：` / `正文：` 四字段，次序不变，step7.parse_2news() 可正常解析。
  - 下游导入验证：`archive_enrich.py` 中 `from step6 import fetch_and_extract` 正常导入使用。
acceptance:
  - AC-04: `fetch_and_extract(url, title)` 仍返回 `(body, None)` 或 `(None, reason)`，调用点无需修改。
  - AC-05: `python3 step6.py --date <可用样本日期> --dry-run` 输出仍含标题/来源/发布时间/正文四字段。
verify:
  - python3 -c "import inspect, step6; assert list(inspect.signature(step6.fetch_and_extract).parameters)==['url','title']"
  - python3 -c "from step6 import fetch_and_extract"
  - python3 step6.py --date 2026-06-07 --dry-run
constraints:
  - 不改 `fetch_and_extract` 之外函数的调用接口。
  - 不改 `2新闻_已审核.md` 的字段、次序和分隔符。
  - 不改 `run_all.sh` 编排（NG-01）。
  - `allowed_paths` 之外的代码不因本任务修改。
