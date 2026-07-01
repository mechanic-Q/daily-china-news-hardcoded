---
id: task-03
title: 新增 manual golden 回归脚本，输出相似度、失败样本与 diff（覆盖：FR-01, FR-04, D-004@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on:
  - task-02
  - task-04
  - task-05
blocks:
  - task-07
requirement_ids:
  - FR-01
  - FR-04
decision_ids:
  - D-004@v1
allowed_paths:
  - tests/manual/test_15b_body_golden.py
---
goal: 在 tests/manual/ 下新增回归脚本，加载 body_golden.jsonl 20 条样本，调用 step6.fetch_and_extract(url, title)，输出 SequenceMatcher 相似度、失败样本与 unified diff，支撑 AC-03
implementation:
  - 沿用 test_15a_diff_smoke.py 的 shebang + argparse CLI 风格
  - 读取 tests/fixtures/body_golden.jsonl（source, title, url, old_body），保持文件行序
  - 对每条调用 step6.fetch_and_extract(url, title) → (None, reason) 标记提取失败 ratio=0； (body, None) 用 SequenceMatcher 算 ratio
  - 逐条输出 [序号/20] [source] ratio=0.xxxx [status]；汇总通过数/总数、平均 ratio；ratio<0.85 或提取失败的样本打印 unified diff（context_lines=3）+ 失败原因；退出码 0
acceptance:
  - python3 tests/manual/test_15b_body_golden.py 无报错退出
  - 输出包含 20 条逐条 ratio 和汇总平均 ratio
  - 低分样本（ratio<0.85）打印 unified diff
  - 失败样本（返回 None）打印 URL 与失败原因
verify:
  - python3 tests/manual/test_15b_body_golden.py
constraints:
  - 仅允许修改 tests/manual/test_15b_body_golden.py，不修改 step6.py、body_golden.jsonl、run_all.sh 或任何 production 文件
  - 只调用 step6.fetch_and_extract(url, title) 公开接口，不导入内部函数
  - 不修改 sys.path；假定从项目根目录 python3 tests/manual/... 运行时 import step6 可用
  - 不引入 pytest/unittest 等测试框架；纯脚本手工执行
