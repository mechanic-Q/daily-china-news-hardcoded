---
id: task-07
title: 执行可用验证命令并记录结果；若 local.yaml 无 build/test/lint，则至少执行 import 检查、manual golden test、`step6.py --dry-run` 样本验证（覆盖：全部）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1]
allowed_paths: [.sillyspec/changes/2026-07-02-phase-15b-trafilatura-body/verification.md]
---
goal: 确认前 6 个任务产出正确：trafilatura 可导入、step6.py 语法正确、manual golden test 通过（≥18/20）、step6.py --dry-run 输出格式正常
implementation:
  - 按次运行 4 个验证命令，将结果追加写入 verification.md
  - 若某步失败，记录失败原因和错误输出，不做自动修复
  - 最终在 verification.md 头部汇总所有步骤通过/失败状态
acceptance:
  - trafilatura 导入成功（exit 0）
  - step6.py 语法无误（py_compile 通过）
  - golden test 通过率 ≥18/20，或低分有明确人工确认记录
  - dry-run 输出含标题/来源/时间/正文四类字段
verify:
  - python3 -c "import trafilatura"  # V1 — import 检查
  - python3 -m py_compile step6.py  # V2 — 语法检查
  - python3 tests/manual/test_15b_body_golden.py  # V3 — 人工 golden 回归
  - python3 step6.py --date 2026-06-25 --dry-run  # V4 — 格式验证
constraints:
  - local.yaml 中 build/test/lint 均为空，不发明额外 lint/typecheck
  - 不依赖外部 CI/SaaS
  - golden set fixture 已到位（task-02），manual test 脚本已到位（task-03）
  - 结果仅记入 allowed_paths 唯一文件
