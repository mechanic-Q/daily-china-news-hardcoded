---
author: lmr
created_at: 2026-06-27 03:13:46
id: task-02
title: 新增 USER_MANUAL.md 用户手册
priority: P0
estimated_hours: 2
depends_on: []
blocks: [task-04]
requirement_ids: [FR-02, FR-04]
decision_ids: [D-002@v1, D-003@v1, D-004@v1]
allowed_paths:
  - USER_MANUAL.md
---

# task-02: 新增 USER_MANUAL.md 用户手册

## 修改文件

- `USER_MANUAL.md`

## 覆盖来源

- Requirements: FR-02, FR-04
- Decisions: D-002@v1, D-003@v1, D-004@v1

## 实现要求

1. 在项目根目录新增 `USER_MANUAL.md`。
2. 使用中文，面向项目使用者自查。
3. 覆盖以下章节：
   - 项目功能概览
   - 数据流和输出文件
   - 一键运行命令
   - 分步运行命令
   - `--date` 和 `--dry-run`
   - `time` 和 `/usr/bin/time -v` 计时
   - sillyspec 常用阶段命令
   - 常见故障排查
   - 当前已知风险
   - 后续 Phase 12/13/14 路线
4. 手册必须说明输出目录是 `/mnt/e/每日新中国/YYYY-MM-DD/`。
5. 手册必须说明当前无标准 build/test/lint，local.yaml `test_strategy: skip`。
6. 手册必须说明 step5 编号空缺是历史原因，不要补。
7. 后续路线只记录方向，不把 Phase 12/13/14 当作本次已实现功能。

## 接口定义

文档任务，无代码接口。

建议章节结构：

```text
# USER_MANUAL.md
1. 项目是什么
2. 快速开始
3. 输出文件
4. 分步命令
5. 计时与性能量化
6. SillySpec 工作流
7. 故障排查
8. 已知风险
9. 后续路线
```

## 边界处理

- 不写未实现功能为已完成能力。
- 不暴露 `.env` 中真实 API key。
- 命令使用当前真实文件名：`step1_3.py`, `step4.py`, `step6.py`, `step7.py`, `step8.py`。
- 日期示例使用占位 `YYYY-MM-DD` 或历史日期，不假设今天已有完整数据。
- 说明 dry-run 对 step8 仍会写 HTML、跳过截图。
- 说明全流水线可能调用外部网络、Chromium、LLM，耗时与费用/额度有关。
- 不新增 docs 目录或拆多文件。

## 非目标

- 不写开发者 API 参考。
- 不写详细代码设计文档。
- 不写性能优化方案细节。
- 不替代 README。

## 参考

- `.sillyspec/local.yaml`
- `.sillyspec/docs/Daily/scan/PROJECT.md`
- `.sillyspec/docs/Daily/scan/ARCHITECTURE.md`
- `.sillyspec/docs/Daily/modules/orchestrator.md`
- `.sillyspec/docs/Daily/modules/renderer.md`

## TDD 步骤

1. 先列出必须覆盖的章节清单。
2. 写 `USER_MANUAL.md`。
3. 对照 requirements.md FR-02/FR-04 检查章节。
4. 搜索敏感词，确认没有真实 secret。
5. 运行 task-04 验证。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `test -f USER_MANUAL.md` | 文件存在 |
| AC-02 | 人工检查目录 | 包含项目功能、输出文件、全量运行、分步运行、date/dry-run、time、sillyspec、故障排查、已知风险、后续路线 |
| AC-03 | 搜索 `ZHIPU_API_KEY\|MINIMAX_API_KEY\|NINEROUTER_API_KEY` | 只出现变量名，不出现真实 key 值 |
| AC-04 | 搜索 `Phase 12\|Phase 13\|Phase 14` | 后续路线存在且标注未实现 |
