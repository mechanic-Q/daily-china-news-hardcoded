---
author: lmr
created_at: 2026-06-27 03:13:46
id: task-03
title: 验证 step8 语法与 dry-run 输出
priority: P0
estimated_hours: 1
depends_on: [task-01]
blocks: []
requirement_ids: [FR-01, FR-03]
decision_ids: [D-001@v1]
allowed_paths:
  - step8.py
  - /mnt/e/每日新中国/**
---

# task-03: 验证 step8 语法与 dry-run 输出

## 修改文件

- 不修改源码；可生成/覆盖指定日期的 HTML 输出文件。

## 覆盖来源

- Requirements: FR-01, FR-03
- Decisions: D-001@v1

## 实现要求

1. 运行 `python3 -m py_compile step8.py`。
2. 选择一个已有 `3新闻_概述.md` 的日期目录。
3. 运行 `python3 step8.py --date YYYY-MM-DD --dry-run`。
4. 检查生成 HTML 中不含 `class="summary"`。
5. 检查 step8 CLI 参数和输出路径未变。

## 接口定义

命令接口不变：

```bash
python3 step8.py --date YYYY-MM-DD --dry-run
```

输入：`/mnt/e/每日新中国/YYYY-MM-DD/3新闻_概述.md`
输出：`/mnt/e/每日新中国/YYYY-MM-DD/YYYY-MM-DD_每日新中国_<期号>.html`

## 边界处理

- 若没有任何已有日期目录，记录无法 dry-run 的原因，不编造数据。
- dry-run 下 step8 应跳过截图，不要求 PNG 更新。
- 若 Chromium 不存在不影响 dry-run 验证，因为截图跳过。
- 不运行全管道，避免触发外部网络和 LLM。
- 不修改 `run_all.sh` 或上游 markdown。
- 如果 dry-run 失败，保留错误输出用于修复。
- 如果 HTML 文件名含中文期号，用 glob/目录列表定位最新 HTML。

## 非目标

- 不验证 screenshot PNG 像素效果。
- 不验证 step1_3/step4/step6/step7。
- 不做性能计时。

## 参考

- `step8.py run()`：dry-run 生成 HTML、跳过截图。
- `renderer.md`：输出 HTML + PNG 契约。

## TDD 步骤

1. 运行语法检查。
2. 找到已有日期样例。
3. dry-run 生成 HTML。
4. 搜索 HTML 中 summary DOM。
5. 记录验证结果。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python3 -m py_compile step8.py` | 退出码 0 |
| AC-02 | `python3 step8.py --date YYYY-MM-DD --dry-run` | 退出码 0，输出 HTML 路径 |
| AC-03 | 搜索生成 HTML 的 `class="summary"` | 0 处匹配 |
| AC-04 | 检查运行输出 | 显示 dry-run 跳过截图或未生成 PNG |
