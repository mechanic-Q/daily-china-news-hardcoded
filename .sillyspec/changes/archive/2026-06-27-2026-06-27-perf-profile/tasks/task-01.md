---
author: lmr
created_at: 2026-06-27 13:49:58
id: task-01
title: 新增 perf_profile.py 外部 profiler
priority: P0
estimated_hours: 3
depends_on: []
blocks: [task-03]
requirement_ids: [FR-01, FR-02, FR-04]
decision_ids: [D-001@v1, D-002@v1, D-004@v1]
allowed_paths:
  - perf_profile.py
---

# task-01: 新增 perf_profile.py 外部 profiler

## 修改文件

- `perf_profile.py`

## 覆盖来源

- Requirements: FR-01, FR-02, FR-04
- Decisions: D-001@v1, D-002@v1, D-004@v1

## 实现要求

1. 新增 `perf_profile.py`。
2. 支持参数：`--date YYYY-MM-DD`、`--dry-run`、`--output-dir PATH`。
3. 默认 date 为今天，默认 output-dir 为 `/mnt/e/每日新中国/YYYY-MM-DD/perf/`。
4. 按固定顺序调用：`step1_3.py`、`step4.py`、`step6.py`、`step7.py`、`step8.py`。
5. 每步使用 `subprocess.run()` 顺序执行，捕获 stdout/stderr。
6. 使用 `time.perf_counter()` 记录每步耗时与总耗时。
7. 任一 step 失败时停止后续 step，但仍生成 JSON + Markdown 报告。
8. 报告保存 stdout_tail/stderr_tail，不保存完整日志。
9. 报告包含最慢 step 排名。
10. 不修改任何业务 step 文件。

## 接口定义

```bash
python3 perf_profile.py [--date YYYY-MM-DD] [--dry-run] [--output-dir PATH]
```

JSON 顶层字段：

- `date`
- `dry_run`
- `started_at`
- `ended_at`
- `total_duration_s`
- `steps`
- `slowest`

每个 step 字段：

- `name`
- `command`
- `started_at`
- `ended_at`
- `duration_s`
- `exit_code`
- `stdout_tail`
- `stderr_tail`

## 边界处理

- `--date` 格式错误时打印中文错误并退出 1。
- 输出目录不存在时自动创建。
- step 失败时报告仍落盘，并且 profiler 退出码等于失败 step 的 exit_code。
- stdout/stderr 为空时 tail 字段为空字符串。
- stdout/stderr 超长时只保留最后若干行或固定字符数。
- `--dry-run` 必须透传给所有 step。
- 不修改 step 脚本参数、输入、输出。
- 不并发执行 step。

## 非目标

- 不优化任何 step。
- 不做子阶段深度插桩。
- 不读取或上报真实 API key。
- 不写数据库。

## 参考

- `run_all.sh` 的 step 顺序和参数透传。
- `.sillyspec/local.yaml` 的 output_dir 和 run_step。

## TDD 步骤

1. 写最小 CLI 和日期解析。
2. 生成空报告结构。
3. 加入 step 调用和耗时记录。
4. 加入 JSON/Markdown 写入。
5. 运行 py_compile 和 dry-run 验证。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python3 -m py_compile perf_profile.py` | 退出码 0 |
| AC-02 | `python3 perf_profile.py --date YYYY-MM-DD --dry-run` | 生成 JSON + Markdown 报告 |
| AC-03 | 检查 JSON | 含 `date/dry_run/total_duration_s/steps/slowest` |
| AC-04 | 检查 steps | 每项含 name/command/duration_s/exit_code/stdout_tail/stderr_tail |
| AC-05 | 检查 Markdown | 含每步耗时表和最慢 step 排名 |
