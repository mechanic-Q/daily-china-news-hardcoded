---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-06
title: step4.run() 接入 build_classification_result 与归档调用
priority: P0
depends_on: [task-04, task-05]
blocks: [task-08, task-09]
requirement_ids: [FR-05, FR-06]
decision_ids: [D-003@v1, D-006@v1, D-007@v1]
allowed_paths:
  - step4.py
---

# task-06: step4.run() 接入 build_classification_result 与归档调用

## 修改文件
- `step4.py`（修改 `run()` 函数）

## 覆盖来源
- Requirements: FR-05 (归档失败不阻断)、FR-06 (共享 build_classification_result)
- Decisions: D-003@v1 (默认接入 run_all)、D-006@v1 (helper module)、D-007@v1 (不改 run_all.sh)

## 实现要求

将 `run()` 重构为：
1. 调 `classified, selected = build_classification_result(today)`
2. 打印进度信息（现有 print）
3. 写 `1新闻_链接.md`（保留现有逻辑）
4. 在写文件后 best-effort 调 `news_archive.archive_articles_best_effort`：

```python
def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")

    print(f"═══ Step 4: 分类筛选 ═══")
    print(f"日期: {today_str}")

    classified, selected = build_classification_result(today)

    if not classified:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    # 打印栏目统计 (保留)
    for col in COLUMN_ORDER:
        if classified[col]:
            top = classified[col][0]
            print(f"  {col}: {len(classified[col])}条 [最高={top.get('priority',0)}] {top['title'][:40]}")
        else:
            print(f"  {col}: 0条")

    print(f"\n精选: {len(selected)}条")
    for a in selected:
        ps = a.get('priority', 0)
        print(f"  [{ps}分] {a.get('column', '?')} | {a['title'][:50]}")

    # 写 1新闻_链接.md
    lines = [f"# {today_str} 精选新闻（按栏目分类）\n"]
    for col in COLUMN_ORDER:
        col_selected = [a for a in selected if a.get('column') == col]
        if not col_selected:
            continue
        lines.append(f"\n## {col}\n")
        for a in col_selected:
            src = detect_source(a['url'])
            lines.append(f"### [{src}] {a['title']}")
            lines.append(f"URL：{a['url']}")
            lines.append('')

    output_path = BASE_DIR / today_str / "1新闻_链接.md"
    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print("\n".join(lines)[:2000])
    else:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")

    # Best-effort 归档 (→ Phase 14A)
    from news_archive import archive_articles_best_effort
    archive_articles_best_effort(today_str, classified, selected, dry_run)
```

## 接口定义

`run(today, dry_run)` 签名不变。

## 边界处理

1. `build_classification_result` 返回空 → 提前 return，不归档
2. `archive_articles_best_effort` 抛任何异常 → 内层已 catch，不影响 return
3. dry_run 透传给 build_classification_result（不生成 JSONL）和 best_effort
4. `1新闻_链接.md` 写逻辑完全不变（只重构为外调 build_classification_result）
5. 保留所有现有 print 输出
6. `from news_archive import archive_articles_best_effort` 放在 run() 内部导入，不影响模块顶层
7. 不写 type hints

## 非目标
- 不修改 `parse_0`、`is_china_related` 等函数
- 不修改 `detect_source`
- 不修改 `1新闻_链接.md` 行级格式

## 参考
- step4.py run() L424-563
- design.md §5.1 build_classification_result 共享方案
- D-007@v1 不改 run_all.sh

## TDD 步骤
1. mock build_classification_result + archive_articles_best_effort
2. 断言 run() 仍写 md 且调 best_effort
3. 断言 archive 异常不传播
4. 确认测试通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | dry_run=False → `1新闻_链接.md` 正常写入 | 文件存在 |
| AC-02 | run() 调了 `archive_articles_best_effort` | mock 被调 1 次 |
| AC-03 | archive_articles_best_effort 抛 Exception → run() 不中断 | `1新闻_链接.md` 仍写入 |
| AC-04 | `1新闻_链接.md` 格式不变 | `### [源] 标题` + `URL：url` |
| AC-05 | `run_all.sh` 无 diff | `git diff run_all.sh` 为空 |
