---
id: task-06
title: 使用 perf_profile.py 记录前后性能对比并写验证结论
author: lmr
created_at: 2026-06-30 02:48:10
priority: P0
depends_on: [task-05]
blocks: []
requirement_ids: [FR-06]
decision_ids: [D-001@v1]
allowed_paths: [perf_profile.py, .sillyspec/changes/2026-06-29-perf-optimize/verify-result.md]
goal: >
  使用 perf_profile.py 记录同日期 step6/step7 前后耗时对比，并在 verify-result.md 写明性能结论。
implementation:
  - 在实现前记录基线 perf_profile 输出，重点保存 step6、step7、total。
  - 在 task-05 通过后用同日期再次运行 perf_profile。
  - 对比两次结果并注明网络、chromium、LLM 波动影响。
## 验收标准
acceptance:
  - verify-result.md 包含基线与优化后 step6/step7 耗时。
  - verify-result.md 包含加速结论或无法量化的明确原因。
  - perf_profile 命令退出码与输出路径被记录。
verify:
  - python3 perf_profile.py --date $(date +%Y-%m-%d) --dry-run
  - python3 perf_profile.py --date $(date +%Y-%m-%d)
constraints:
  - 不修改 perf_profile.py；仅使用它采集数据。
  - 必须用同一日期对比，减少外部变量。
  - 结论只写性能数据与环境说明，不写实现代码。
---
