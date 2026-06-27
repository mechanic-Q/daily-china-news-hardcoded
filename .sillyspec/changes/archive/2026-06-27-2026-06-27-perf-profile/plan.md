---
author: lmr
created_at: 2026-06-27 13:50:00
change: 2026-06-27-perf-profile
stage: plan
doc_type: plan
plan_level: light
---

# 轻量计划：Phase 12 性能量化

## 来源

用户确认方案 A：新增 `perf_profile.py` 外部 profiler，逐 step 记录耗时、退出码、stdout/stderr tail，输出 JSON + Markdown 报告；同时修改 `run_all.sh` 输出每步耗时和总耗时。Phase 12 只量化，不优化。

## 范围

- `perf_profile.py`：新增外部性能量化入口。
- `run_all.sh`：增加每步耗时、总耗时、失败时已完成耗时输出。
- `.sillyspec/changes/2026-06-27-perf-profile/*`：本次变更规范与验证记录。

不修改：`step1_3.py`、`step4.py`、`step6.py`、`step7.py`、`step8.py`、栏目评分算法、并发模型、报纸产物语义。

## Wave 分组

### Wave 1（无依赖，可并行）

- [ ] task-01: 新增 perf_profile.py 外部 profiler（覆盖：FR-01, FR-02, FR-04, D-001@v1, D-002@v1, D-004@v1）
- [ ] task-02: 修改 run_all.sh 输出每步耗时和总耗时（覆盖：FR-03, FR-05, D-001@v1, D-003@v1）

### Wave 2（依赖 Wave 1）

- [ ] task-03: 验证 profiler dry-run 报告（依赖：task-01；覆盖：FR-01, FR-02, FR-04, D-001@v1, D-002@v1）
- [ ] task-04: 验证 run_all.sh 兼容性和计时输出（依赖：task-02；覆盖：FR-03, FR-05, D-001@v1, D-003@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 新增 perf_profile.py 外部 profiler | W1 | P0 | — | FR-01, FR-02, FR-04, D-001@v1, D-002@v1, D-004@v1 | 新增 profiler 和 JSON/MD 报告 |
| task-02 | 修改 run_all.sh 输出每步耗时和总耗时 | W1 | P0 | — | FR-03, FR-05, D-001@v1, D-003@v1 | 保持 CLI/顺序/失败短路 |
| task-03 | 验证 profiler dry-run 报告 | W2 | P0 | task-01 | FR-01, FR-02, FR-04, D-001@v1, D-002@v1 | py_compile、dry-run、JSON/MD字段 |
| task-04 | 验证 run_all.sh 兼容性和计时输出 | W2 | P0 | task-02 | FR-03, FR-05, D-001@v1, D-003@v1 | bash -n、dry-run、计时输出 |

## 关键路径

- task-01 → task-03
- task-02 → task-04

两条路径可并行，最终验收需 task-03 和 task-04 均通过。

## 验收

- `python3 -m py_compile perf_profile.py` 通过。
- `python3 perf_profile.py --date <已有日期> --dry-run` 退出码 0 或在 step 失败时仍生成报告。
- JSON 报告存在，包含 `date`、`dry_run`、`total_duration_s`、`steps[]`、`slowest`。
- Markdown 报告存在，包含每步耗时表和最慢 step 排名。
- `./run_all.sh --date <已有日期> --dry-run` 输出每步耗时和总耗时。
- `run_all.sh` 参数、step 顺序、失败短路语义不变。
- 不修改 5 个业务 step 文件。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02, task-03, task-04 | profiler 报告 + run_all 计时输出 |
| D-002@v1 | task-01, task-03 | step 级报告，不深度插桩业务 step |
| D-003@v1 | task-02, task-04 | 不优化、不并发、兼容旧 run_all |
| D-004@v1 | task-01, task-03 | 采用外部 profiler 为主 |
