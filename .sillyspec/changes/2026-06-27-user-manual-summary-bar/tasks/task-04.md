---
author: lmr
created_at: 2026-06-27 03:13:46
id: task-04
title: 验证手册覆盖范围
priority: P0
estimated_hours: 1
depends_on: [task-02]
blocks: []
requirement_ids: [FR-02, FR-04]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths:
  - USER_MANUAL.md
---

# task-04: 验证手册覆盖范围

## 修改文件

- 不修改源码；必要时只修正 `USER_MANUAL.md` 漏项。

## 覆盖来源

- Requirements: FR-02, FR-04
- Decisions: D-002@v1, D-003@v1

## 实现要求

1. 检查 `USER_MANUAL.md` 是否存在。
2. 对照 FR-02 必须覆盖项逐项核对。
3. 对照 FR-04 检查后续 Phase 12/13/14 是否只作为路线记录，未宣称已完成。
4. 检查命令是否与真实脚本名一致。
5. 检查文档不包含真实 API key 或 secret。

## 接口定义

文档验证任务，无代码接口。

覆盖项清单：

```text
project overview
output files/data flow
run_all full command
individual step commands
--date / --dry-run
time / /usr/bin/time -v
sillyspec commands
troubleshooting
known risks
Phase 12/13/14 roadmap
```

## 边界处理

- 若某章节标题不同但内容等价，可视为通过。
- 若某命令依赖已有日期数据，手册需说明前置条件。
- 真实 secret 不得出现；变量名允许出现。
- 后续路线不得写成已实现功能。
- 手册不得要求不存在的 `step5.py`。
- 手册不得声称有标准自动化测试。
- 手册不得改写实际输出目录。

## 非目标

- 不验证 README 内容。
- 不生成英文版手册。
- 不新增 docs 目录。
- 不做截图或浏览器验证。

## 参考

- `requirements.md` FR-02/FR-04。
- `.sillyspec/local.yaml` 命令和测试策略。
- `orchestrator.md` run_all 参数契约。

## TDD 步骤

1. 读取 `USER_MANUAL.md`。
2. 建立覆盖项 checklist。
3. 搜索命令和关键章节。
4. 搜索 secret 风险。
5. 修正缺漏并复查。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `test -s USER_MANUAL.md` | 文件存在且非空 |
| AC-02 | 覆盖项 checklist | 10 个必需覆盖项全部存在 |
| AC-03 | 搜索 `step5.py` | 不出现 |
| AC-04 | 搜索真实 key 形态或 `.env` 值 | 不出现真实 secret |
| AC-05 | 搜索 `Phase 12`, `Phase 13`, `Phase 14` | 三者均存在且标注为后续路线 |
