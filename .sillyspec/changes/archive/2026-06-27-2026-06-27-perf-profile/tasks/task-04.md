---
author: lmr
created_at: 2026-06-27 13:49:58
id: task-04
title: 验证 run_all.sh 兼容性和计时输出
priority: P0
estimated_hours: 1
depends_on: [task-02]
blocks: []
requirement_ids: [FR-03, FR-05]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - run_all.sh
---

# task-04: 验证 run_all.sh 兼容性和计时输出

## 修改文件

- 不修改源码；仅运行语法检查和 dry-run 验证。

## 覆盖来源

- Requirements: FR-03, FR-05
- Decisions: D-001@v1, D-003@v1

## 实现要求

1. 运行 `bash -n run_all.sh`。
2. 选择已有日期。
3. 运行 `./run_all.sh --date YYYY-MM-DD --dry-run`。
4. 检查每个 step 耗时输出。
5. 检查总耗时输出。
6. 检查参数解析和 step 顺序未变。

## 接口定义

验证命令：

```bash
./run_all.sh --date YYYY-MM-DD --dry-run
```

预期输出包含：

```text
⏱ step1_3.py: ...s
⏱ step4.py: ...s
⏱ step6.py: ...s
⏱ step7.py: ...s
⏱ step8.py: ...s
⏱ 总耗时: ...s
```

## 边界处理

- 若 dry-run 因上游文件缺失失败，仍需确认失败前 step 耗时输出。
- 不运行非 dry-run，避免网络和 LLM 成本。
- 不修改任何输出 markdown/html/png 断言。
- 不改变 `DRY_RUN` 为空时不加引号的约定。
- 不改变 `STEPS` 数组顺序。
- 失败路径仍应 exit 1。

## 非目标

- 不验证 profiler 报告。
- 不做耗时数值阈值判断。
- 不做性能优化。

## 参考

- `orchestrator.md`
- `run_all.sh`

## TDD 步骤

1. 运行 shell 语法检查。
2. dry-run 一次。
3. 搜索耗时输出行。
4. 检查 step 顺序。
5. 汇总结果。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `bash -n run_all.sh` | 退出码 0 |
| AC-02 | `./run_all.sh --date YYYY-MM-DD --dry-run` | 输出 step 耗时和总耗时 |
| AC-03 | 检查 `STEPS` | 顺序仍为 step1_3, step4, step6, step7, step8 |
| AC-04 | 检查 CLI | `--date` 和 `--dry-run` 仍可用 |
| AC-05 | 失败路径人工/命令检查 | 保留 `exit 1` 失败短路 |
