---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-07
title: 重写 run() 评分链路 + legacy 降级
priority: P0
depends_on: [task-04, task-05, task-06]
blocks: [task-08, task-09, task-10]
requirement_ids: [FR-01, FR-07, FR-08]
decision_ids: [D-004@v1, D-006@v1, D-009@v1]
allowed_paths:
  - step4.py
---

## Context

- `/mnt/e/Daily/.sillyspec/changes/default/design.md` (§4.4 数据流, §8 兼容矩阵, §9 风险)
- `/mnt/e/Daily/.sillyspec/changes/default/requirements.md` (FR-01, FR-07, FR-08)
- `/mnt/e/Daily/.sillyspec/changes/default/decisions.md` (D-004@v1, D-006@v1, D-009@v1)
- `/mnt/e/Daily/step4.py` L277-414 (现 run() 实现)

## 修改文件

`step4.py` run() 函数（核心改造），保留 `score_all_categories` / `llm_classify_single` / `priority_score` 作为 legacy_path

## 覆盖来源

FR-01 / FR-07 LLM 失败降级 / FR-08 降级率监控 / D-004@v1 必降级 / D-006@v1 保留 llm_classify_single / D-009@v1 二级降级

## 实现要求

1. 现 run() 中 "Phase 1: 关键词评分", "Phase 2: LLM 仲裁", "Phase 3: 合并" 三段（L318-352）替换为新链路：

   ```python
   classified = {col: [] for col in COLUMN_ORDER}
   llm_fail_count = 0
   for a in articles:
       source = detect_source(a['url'])
       signals = score_signals(a['title'], source)
       if signals is not None:
           a['signals'] = signals
           a['score_source'] = 'llm'
           scores = aggregate_scores(signals)
           cat = assign_category(signals)
           if cat is None:
               continue
           priority = scores.get(cat, 0)
       else:
           llm_fail_count += 1
           # legacy_path
           kw_scores = score_all_categories(a['title'])
           if not kw_scores:
               continue
           try:
               # 二级降级判断：高置信度直接归属，低置信度尝试 llm_classify_single
               sorted_cats = sorted(kw_scores.items(), key=lambda x: -x[1])
               best_cat, best_score = sorted_cats[0]
               second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
               if best_score >= 4 and (best_score - second_score) >= 2:
                   cat = best_cat
               else:
                   # 尝试 llm_classify_single；失败时退化为关键词 max（D-009@v1）
                   try:
                       results = llm_classify_single([a])
                       cat = results.get(a['title']) or best_cat
                   except Exception:
                       cat = best_cat
           except Exception:
               cat = max(kw_scores, key=kw_scores.get)
           a['signals'] = None
           a['score_source'] = 'keyword-fallback'
           priority = priority_score(a['title'], cat) + kw_scores.get(cat, 0)
       a['category'] = cat
       a['priority'] = priority
       classified[cat].append(a)
   ```

2. 降级率监控（FR-08）：批末统计 `llm_fail_count / total_articles`；若 ≥30% 输出

   ```python
   print(f"⚠ column-score 降级率 {pct}%", file=sys.stderr)
   ```

3. 栏目内排序 / 取 top-10 / used_urls 去重逻辑保持现行（L354-388）；`🚀 科技` 兜底字符串改为 `COLUMN_ORDER[1]`（即 `🤖 AI智能前沿`），并优先用 category

## 接口定义

`run(today, dry_run)` 签名不变；内部链路改造。

## 边界处理 (≥5)

1. articles 为空 → 直接返回（保留现有 `if not articles: return`）
2. 单条 score_signals 返回 None → legacy_path，不抛错不中断
3. legacy_path 内 llm_classify_single 抛错 → 退化关键词 max（D-009@v1）
4. 关键词亦无命中（score_all_categories 返回空 dict）→ 跳过该文章
5. assign_category 返回 None → 跳过该文章
6. 降级率监控不阻断流水线
7. dry_run 行为不变（仅预览，不写文件）
8. used_urls 去重逻辑不变
9. 不删除 score_all_categories / llm_classify_single / priority_score（D-006@v1）

## 非目标

- 不改空栏目输出逻辑（task-08）
- 不写测试（task-09）
- 不实现 build_classification_result 函数（Phase 14A 任务，不属于本变更）
- 不改写日报 md 格式（仅栏目集合从 8→9 自然变化）

## 参考

- `step4.py` 现 run() L277-414
- `llm_client.call_llm` 错误处理风格

## TDD 步骤

1. `test_run_uses_score_signals_for_all_articles`（mock score_signals 返回合法 signals → 断言 classified 有数据，无 legacy_path 调用）
2. `test_run_falls_back_when_score_signals_returns_none`（mock score_signals 始终 None → 断言 score_all_categories 被调用）
3. `test_run_handles_llm_classify_single_failure`（mock score_signals=None mock llm_classify_single 抛错 → 走关键词 max）
4. `test_run_logs_degradation_above_30pct`（mock 100 篇全部走 legacy → stderr 含 "⚠ column-score 降级率"）
5. `test_run_skips_articles_without_category`（mock signals 让 assign_category 全返回 None → classified 全空）

## 验收标准

| ID | 描述 | 预期 |
|---|---|---|
| AC-01 | 完整 LLM 路径，所有 article 入 classified | True |
| AC-02 | 完整 fallback 路径，关键词命中 article 入 classified | True |
| AC-03 | LLM + 关键词均失败 article 被 skip | True |
| AC-04 | 降级率 ≥30% 时 stderr 输出 warning | True |
| AC-05 | dry-run 不写文件 | True |
| AC-06 | run() 不再有 "Phase 1: 关键词评分" 注释（已重构） | `rg` 无匹配 |
