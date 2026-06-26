---
author: lmr
created_at: 2026-06-27 03:13:46
id: task-01
title: 删除 step8 顶部全局摘要栏
priority: P0
estimated_hours: 1
depends_on: []
blocks: [task-03]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-004@v1]
allowed_paths:
  - step8.py
---

# task-01: 删除 step8 顶部全局摘要栏

## 修改文件

- `step8.py`

## 覆盖来源

- Requirements: FR-01
- Decisions: D-001@v1, D-004@v1

## 实现要求

1. 删除 `generate_summary(sections)` 函数。
2. 删除 `build_html()` 内 `summary_text = generate_summary(sections)`。
3. 删除 HTML 模板中的 `<div class="summary">{esc(summary_text)}</div>`。
4. 删除 CSS `.summary { ... }` 样式块。
5. 保留 `build_html(target_date, sections, left_sections, right_sections)` 函数签名。
6. 保留标题、slogan、日期、期号、双栏正文、footer。
7. 不新增配置开关、环境变量、CLI 参数或兼容旧 summary 的分支。

## 接口定义

`build_html(target_date, sections, left_sections, right_sections)` 签名不变。

控制流：

```text
build_html:
  compute issue/date_text
  render left/right column groups
  build page header
  directly render story-wrap after header
  render footer
```

删除后不再有 `generate_summary()` 符号；`build_html()` 内不再有 `summary_text` 变量。`parse_md()` 内用于单条新闻解析的局部 `summary_text` 不属于顶部全局摘要栏。

## 边界处理

- `sections` 为空时仍沿用现有 `story_main_html` 逻辑，不新增空态。
- `left_sections`/`right_sections` 单列逻辑保持现状。
- HTML escaping 仍通过 `esc()` 处理标题和正文。
- `--dry-run` 行为不变，由 `run()` 控制。
- 不修改输入 `sections` 列表或其元素。
- 不修改 screenshot/crop 逻辑。
- 删除 summary 不影响 `parse_md()` 解析单条新闻摘要。

## 非目标

- 不改双栏平衡算法。
- 不改 CSS 主题、字号、footer。
- 不改摘要生成 step7。
- 不做栏目评分或性能优化。

## 参考

- `design.md` Renderer 调整。
- `renderer.md`：step8 是管道终点。

## TDD 步骤

1. 搜索 `generate_summary|class="summary"|.summary`，确认现状存在。
2. 删除 summary 栏相关代码。
3. 运行 `python3 -m py_compile step8.py`。
4. 运行 task-03 的 dry-run 验证。
5. 搜索确认无 summary 栏残留。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `/usr/bin/rg -n "generate_summary|class=\"summary\"|\.summary" step8.py` | 0 处匹配 |
| AC-02 | `python3 -m py_compile step8.py` | 退出码 0 |
| AC-03 | 人工检查 `build_html()` | header 后直接渲染 `story-wrap` |
| AC-04 | `git diff -- step8.py` | 仅删除 summary 栏相关代码，无无关重构 |
