---
author: lmr
created_at: 2026-06-27 03:10:26
change: 2026-06-27-user-manual-summary-bar
stage: brainstorm
doc_type: requirements
---

# Requirements — 用户手册与顶部总摘要栏移除

## 功能需求

### FR-01: 删除顶部全局摘要栏

覆盖决策：D-001@v1, D-004@v1

Given 已有 `3新闻_概述.md` 可供 step8 渲染
When 运行 `python3 step8.py --date YYYY-MM-DD --dry-run`
Then 输出 HTML 中不包含 `<div class="summary">`，页面标题区域后直接进入正文双栏。

Given 源码中存在 `generate_summary()`
When 执行本变更
Then 删除 `generate_summary()` 及其唯一调用，不保留 summary 开关。

### FR-02: 新增用户手册

覆盖决策：D-002@v1, D-004@v1

Given 用户需要自查项目能力和操作命令
When 打开根目录 `USER_MANUAL.md`
Then 能看到项目功能、输出文件、运行方式、分步命令、sillyspec 命令、计时方法、故障排查和后续路线。

### FR-03: 保持现有流水线接口不变

覆盖决策：D-003@v1

Given 用户已有调用脚本
When 本变更完成后继续运行 `./run_all.sh [--date YYYY-MM-DD] [--dry-run]` 或 `python3 step8.py [--date YYYY-MM-DD] [--dry-run]`
Then 命令参数、输入输出路径、文件命名保持不变。

### FR-04: 后续议题只记录路线，不在本次实现

覆盖决策：D-003@v1

Given 用户提出性能慢和栏目评分需要重做
When 本变更完成
Then `USER_MANUAL.md` 记录 Phase 12 性能量化、Phase 13 栏目评分重做、Phase 14 性能优化路线；源码不实现这些议题。

## 非功能需求

- 兼容性：上游 `3新闻_概述.md` 格式不变，HTML/PNG 输出路径不变。
- 可回退：如需恢复摘要栏，可通过 git diff 恢复删除内容。
- 可测试：通过 Python 语法检查、step8 dry-run、HTML 内容检查验证。
- 可维护：手册为单文件，后续 phase archive 时同步更新。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01 | 删除顶部全局摘要栏 |
| D-002@v1 | FR-02 | 手册覆盖全范围 |
| D-003@v1 | FR-03, FR-04 | 后续议题拆分，不纳入本次实现 |
| D-004@v1 | FR-01, FR-02 | 采用最小变更方案 A |
