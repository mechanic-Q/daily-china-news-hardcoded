---
author: lmr
created_at: 2026-06-27 03:14:00
change: 2026-06-27-user-manual-summary-bar
stage: plan
doc_type: plan
plan_level: light
---

# 轻量计划：用户手册与顶部总摘要栏移除

## 来源

用户确认方案 A：删除 `step8.py` 大标题下方自动生成的所有新闻总摘要栏；新增根目录 `USER_MANUAL.md`，覆盖项目功能、运行命令、sillyspec 流程、`time` 计时、故障排查和后续 Phase 12/13/14 路线。

## 范围

- `step8.py` / renderer 模块：删除 summary 栏生成、样式和模板输出。
- `USER_MANUAL.md`：新增单文件用户手册。
- `.sillyspec/changes/2026-06-27-user-manual-summary-bar/*`：本次变更规范与验证记录。

不修改：`run_all.sh`、`step1_3.py`、`step4.py`、`step6.py`、`step7.py`、LLM 配置、性能逻辑、栏目评分算法。

## Wave 分组

### Wave 1（无依赖，可并行）

- [ ] task-01: 删除 step8 顶部全局摘要栏（覆盖：FR-01, D-001@v1, D-004@v1）
- [ ] task-02: 新增 USER_MANUAL.md 用户手册（覆盖：FR-02, FR-04, D-002@v1, D-003@v1, D-004@v1）

### Wave 2（依赖 Wave 1）

- [ ] task-03: 验证 step8 语法与 dry-run 输出（依赖：task-01；覆盖：FR-01, FR-03, D-001@v1）
- [ ] task-04: 验证手册覆盖范围（依赖：task-02；覆盖：FR-02, FR-04, D-002@v1, D-003@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 删除 step8 顶部全局摘要栏 | W1 | P0 | — | FR-01, D-001@v1, D-004@v1 | 删除函数、CSS 和模板输出 |
| task-02 | 新增 USER_MANUAL.md 用户手册 | W1 | P0 | — | FR-02, FR-04, D-002@v1, D-003@v1, D-004@v1 | 单文件中文手册 |
| task-03 | 验证 step8 语法与 dry-run 输出 | W2 | P0 | task-01 | FR-01, FR-03, D-001@v1 | 语法、dry-run、HTML DOM 检查 |
| task-04 | 验证手册覆盖范围 | W2 | P0 | task-02 | FR-02, FR-04, D-002@v1, D-003@v1 | 覆盖项与 secret 检查 |

## 关键路径

- task-01 → task-03
- task-02 → task-04

两条路径可并行，最终验收需 task-03 和 task-04 均通过。

## 验收

- `python3 -m py_compile step8.py` 通过。
- `python3 step8.py --date <已有日期> --dry-run` 可生成 HTML。
- 生成的 HTML 不包含 `<div class="summary">` 或 `class="summary"`。
- `step8.py` 中不存在 `generate_summary` 函数或调用。
- `USER_MANUAL.md` 包含：项目功能、输出文件/数据流、全量运行、分步运行、`--date`/`--dry-run`、`time`/`/usr/bin/time -v`、sillyspec 命令、常见故障、已知风险、Phase 12/13/14 路线。
- `run_all.sh` 和各 step CLI 不变。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-03 | HTML 无 `class="summary"`；step8 无 `generate_summary` |
| D-002@v1 | task-02, task-04 | `USER_MANUAL.md` 章节覆盖全范围 |
| D-003@v1 | task-02, task-04 | 手册记录后续 Phase，源码不实现后续议题 |
| D-004@v1 | task-01, task-02 | 无 summary 开关；无多文档拆分 |
