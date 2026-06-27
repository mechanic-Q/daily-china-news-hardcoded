---
author: lmr
created_at: 2026-06-27 13:45:31
change: 2026-06-27-perf-profile
stage: brainstorm
doc_type: requirements
---

# Requirements — Phase 12 性能量化

## 功能需求

### FR-01: 外部 profiler 顺序计时
覆盖决策：D-001@v1, D-004@v1

Given 已有 Daily step 脚本
When 运行 `python3 perf_profile.py --date YYYY-MM-DD --dry-run`
Then profiler 按 run_all 顺序执行 step1_3/step4/step6/step7/step8，并记录每步耗时和退出码。

### FR-02: 生成结构化和可读报告
覆盖决策：D-001@v1, D-004@v1

Given profiler 执行结束或某 step 失败
When 查看输出目录
Then 存在 JSON 报告和 Markdown 报告，包含总耗时、每步耗时、退出码、stdout/stderr tail、最慢 step 排名。

### FR-03: run_all 输出每步耗时
覆盖决策：D-001@v1

Given 用户继续使用 `./run_all.sh [--date YYYY-MM-DD] [--dry-run]`
When 每个 step 执行完成
Then 控制台输出该 step 耗时；全部完成后输出总耗时；失败时输出已完成步骤耗时后按原语义退出。

### FR-04: 低侵入定位慢点
覆盖决策：D-002@v1, D-003@v1

Given Phase 12 只负责量化
When 实现完成
Then 不深改业务 step，不并发化，不优化，仅提供 step 级基线和低侵入线索。

### FR-05: 兼容现有流水线
覆盖决策：D-003@v1

Given 现有用户依赖 run_all 参数和输出产物
When 本变更完成
Then `run_all.sh` 的参数、step 顺序、失败短路和 0/1/2/3/HTML/PNG 产物保持不变。

## 非功能需求

- 兼容性：新增 profiler 不影响旧入口。
- 可回退：删除 `perf_profile.py` 并回退 `run_all.sh` 即可恢复。
- 可测试：可用 dry-run 生成报告并校验 JSON 字段。
- 成本可控：文档提示完整运行会触发网络和 LLM 调用。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-02, FR-03 | 外部 profiler + run_all 计时 |
| D-002@v1 | FR-04 | 默认 step 级，低侵入补充线索 |
| D-003@v1 | FR-04, FR-05 | 只量化不优化，兼容旧流水线 |
| D-004@v1 | FR-01, FR-02 | 采用方案 A |
