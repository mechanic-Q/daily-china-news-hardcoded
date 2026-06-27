---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-08
title: 空栏目消失 — run() 输出逻辑
priority: P1
depends_on: [task-07]
blocks: [task-09, task-10]
requirement_ids: [FR-06]
decision_ids: [D-016@v1]
allowed_paths:
  - step4.py
---

# task-08: 空栏目消失 — run() 输出逻辑

**Created**: 2026-06-27 21:09:09
**Author**: lmr

## 修改文件
`step4.py` `run()` 末尾写 md 的循环

## 覆盖来源
- FR-06 空栏目消失
- D-016@v1 路径 A

## 实现要求

现 L395-405:
```python
for col in col_order:
    col_selected = [a for a in selected if a.get('column') == col]
    lines.append(f"\n## {col}\n")
    if col_selected:
        for a in col_selected:
            src = detect_source(a['url'])
            lines.append(f"### [{src}] {a['title']}")
            lines.append(f"URL：{a['url']}")
            lines.append('')
    else:
        lines.append('（当日无真实报道，栏目留空）\n')
```

改为：
```python
for col in COLUMN_ORDER:
    col_selected = [a for a in selected if a.get('column') == col]
    if not col_selected:
        continue   # 空栏目完全跳过，不写 heading 也不写占位
    lines.append(f"\n## {col}\n")
    for a in col_selected:
        src = detect_source(a['url'])
        lines.append(f"### [{src}] {a['title']}")
        lines.append(f"URL：{a['url']}")
        lines.append('')
```

## 接口定义
`run()` 内代码块改写，无新增函数。

## 边界处理
1. 所有栏目都有内容 → 写出 9 个 heading，行级格式与现行一致
2. 某栏目空 → `continue` 跳过，相邻栏目自然衔接，无空 heading
3. 全部栏目都空（selected 为空）→ 只写文件头 `# {date} 精选新闻...`，无任何 heading
4. `col_selected` 排序按 `selected` 顺序（不变）
5. `##` 与 `###` 之间空行格式保持
6. 旧 8 栏 md 仍能被 step7 / step8 解析（不缺 🤖 是上游问题，下游不会因 9 栏 heading 报错）
7. 不修改 `### [{src}] {title}` 行级格式
8. 不修改 `URL：{url}` 行级格式

## 非目标
- 不改 step7 / step8 解析逻辑（按设计 step7/8 天然兼容）
- 不修改 `selected` 选取算法
- 不修改 `used_urls` 逻辑

## 参考
- design §4.2 路径 A 说明

## TDD 步骤
1. `test_run_writes_only_non_empty_columns`（mock selected 仅 3 栏有内容 → 读取 `1新闻_链接.md` 仅 3 个 `## ` heading）
2. `test_run_skips_all_empty`（selected 为空 → 文件无 `## `）
3. `test_run_no_placeholder_text`（`rg "（当日无真实报道"` 在新输出中不存在）

## 验收标准
| ID | 描述 | 预期 |
|----|------|------|
| AC-01 | mock 9 栏全 0 selected → md 无 `^## ` | True |
| AC-02 | mock 3 栏有数据 → md 含 3 个 heading | True |
| AC-03 | 旧占位字符串 "（当日无真实报道" 在 md 中 0 次 | True |
| AC-04 | 行级 `### [src] title` 与 `URL：url` 格式不变 | True |
| AC-05 | dry-run 预览输出同样跳过空栏目 | True |
