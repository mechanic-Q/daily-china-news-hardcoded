---
author: lmr
created_at: 2026-06-27 13:49:58
id: task-02
title: 修改 run_all.sh 输出每步耗时和总耗时
priority: P0
estimated_hours: 2
depends_on: []
blocks: [task-04]
requirement_ids: [FR-03, FR-05]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - run_all.sh
---

# task-02: 修改 run_all.sh 输出每步耗时和总耗时

## 修改文件

- `run_all.sh`

## 覆盖来源

- Requirements: FR-03, FR-05
- Decisions: D-001@v1, D-003@v1

## 实现要求

1. 保留原 CLI：`./run_all.sh [--date YYYY-MM-DD] [--dry-run]`。
2. 保留 `STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")` 顺序。
3. 在管道开始记录总开始时间。
4. 每个 step 前记录开始时间，执行后记录结束时间并输出耗时。
5. 全部成功后输出总耗时。
6. 如果 step 失败，输出该 step 耗时和当前总耗时，再按原语义 `exit 1`。
7. 因脚本有 `set -e`，执行 step 时必须临时 `set +e` 捕获 exit_code，再 `set -e` 恢复。
8. 不引入新依赖，使用 bash/date。

## 接口定义

CLI 不变：

```bash
./run_all.sh [--date YYYY-MM-DD] [--dry-run]
```

控制流：

```text
pipeline_start=$(now)
for step in STEPS:
  step_start=$(now)
  set +e
  python3 step --date DATE $DRY_RUN
  exit_code=$?
  set -e
  step_end=$(now)
  print step duration
  if exit_code != 0: print total duration; exit 1
print total duration
```

## 边界处理

- 未传 `--date` 时仍默认今天。
- 未传 `--dry-run` 时 `$DRY_RUN` 仍为空 token，不加引号传递。
- 未知参数仍退出 1。
- step 失败时仍停止后续 step。
- `set -e` 恢复后不影响后续命令。
- 耗时输出不改变 step stdout 内容，只额外追加日志行。
- 不修改 step 脚本或产物路径。

## 非目标

- 不写 JSON/Markdown 报告。
- 不改变日志格式以外的业务输出。
- 不做并发或重试。
- 不改变失败处理为继续执行。

## 参考

- `.sillyspec/docs/Daily/modules/orchestrator.md`
- `run_all.sh` 当前实现

## TDD 步骤

1. 记录当前 `run_all.sh` 行为和 CLI。
2. 加入计时辅助函数/变量。
3. 用 `set +e` 包裹 step 调用。
4. 运行 `bash -n run_all.sh`。
5. 用已有日期 dry-run 验证计时输出。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `bash -n run_all.sh` | 退出码 0 |
| AC-02 | `./run_all.sh --date YYYY-MM-DD --dry-run` | 输出每个 step 耗时 |
| AC-03 | 检查输出 | 输出总耗时 |
| AC-04 | 人工检查 diff | 参数解析和 STEPS 顺序不变 |
| AC-05 | 失败路径检查 | step 失败时仍 exit 1，且输出耗时 |
