---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-04
title: 新增 news_archive.py best-effort wrapper
priority: P0
depends_on: [task-01, task-02, task-03]
blocks: [task-06]
requirement_ids: [FR-05]
decision_ids: [D-003@v1, D-006@v1, D-007@v1]
allowed_paths:
  - news_archive.py
---

# task-04: 新增 news_archive.py best-effort wrapper

## 修改文件
- `news_archive.py`（追加函数）

## 覆盖来源
- Requirements: FR-05 (归档失败不阻断 doce 日报)
- Decisions: D-003@v1 (默认接入 run_all 但失败不阻断)、D-006@v1 (helper module 方案B)、D-007@v1 (不改 run_all.sh)

## 实现要求

`archive_articles_best_effort(today_str, classified, selected, dry_run=False)`:
1. 遍历 `classified` 所有栏目 + 文章，收集到 `all_articles` 列表
2. 调 `archive_articles(all_articles + selected, today_str, selected, dry_run)`
3. 外层 `try/except Exception` 捕获所有异常
4. 异常时 `print(f"⚠ 新闻归档失败: {e}")`，不 raise
5. 成功时 `print(f"✅ 新闻归档: {new}新 {updated}更新")`
6. `dry_run` 透过到 `archive_articles`

## 接口定义

```python
def archive_articles_best_effort(today_str, classified, selected, dry_run=False):
    """
    classified: {col: [article dict]} — step4 classified 字典
    selected: [article dict] — step4 精选 top-10
    dry_run: 只预览
    失败只打印 warning，不抛异常
    """
    try:
        all_articles = []
        for col, items in classified.items():
            all_articles.extend(items)
        new, upd = archive_articles(all_articles, today_str, selected, dry_run)
        print(f"✅ 新闻归档: {new}新 {upd}更新")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"⚠ 新闻归档失败: {e}")
```

## 边界处理

1. `classified` 为空 dict → 收集 0 篇文章，`archive_articles` 处理空列表
2. JSONL 写入失败（磁盘满、权限） → catch，打印 warning，不阻断
3. 任一 article 数据不完整 → `build_record` 可能返回缺字段 dict，被 JSONL 写入容忍
4. `selected` 为空列表 → `selected_in_top10` 全部 False
5. `dry_run=True` → 穿透到 `archive_articles`，不落盘
6. traceback 打印到 stderr 但程序继续
7. 不写 type hints

## 非目标
- 不修改 `run_all.sh`
- 不实现断点续传
- 不统计失败率

## 参考
- design.md §5.1 helper module
- D-003@v1 设计决策
- step4.py 对 `llm_classify_single` 的 try/except 模式

## TDD 步骤
1. 写 test_best_effort_passes_through、test_best_effort_handles_exception
2. 确认失败
3. 实现
4. 通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | archive_articles 抛 Exception → 不传播 | `archive_articles_best_effort(...)` 不抛 |
| AC-02 | 正常路径打印 "✅ 新闻归档" | stdout 含 `✅ 新闻归档` |
| AC-03 | 异常路径打印 "⚠ 新闻归档失败" | stdout 含 `⚠ 新闻归档失败` |
| AC-04 | dry_run=True 的 classified 9 栏文章传递给 archive_articles | mock 捕获参数一致 |
| AC-05 | selected 文章也包含在归档中 | record 中出现 selected 文章的 url |
