---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-05
title: step4 提取 build_classification_result(today)
priority: P0
depends_on: [task-01, task-02, task-03, task-04]
blocks: [task-06, task-07]
requirement_ids: [FR-06]
decision_ids: [D-010@v1]
allowed_paths:
  - step4.py
---

# task-05: step4 提取 build_classification_result(today)

## 修改文件
- `step4.py`（新增函数，重构 run()）

## 覆盖来源
- Requirements: FR-06 (archive_news.py 独立补跑不写 md)
- Decisions: D-010@v1 (build_classification_result 共享函数)

## 实现要求

从 `step4.py` 的 `run()` 提取分类逻辑为独立纯数据函数：

```python
def build_classification_result(today):
    """
    运行完整分类流程，返回 (classified, selected)。
    不写任何文件，不调用 news_archive。
    archive_news.py --date 和 run() 共享此函数。
    """
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "0新闻_粗筛.md"

    articles = parse_0(input_path, today)
    if not articles:
        return {}, []

    # 质量过滤
    articles = [a for a in articles if is_quality_news(a["title"])]

    # 涉华过滤
    china_pass = []
    china_llm = []
    for a in articles:
        if is_china_related(a["title"]):
            china_pass.append(a)
        elif is_china_source(a["url"]):
            china_llm.append(a)
    llm_confirmed = []
    for a in china_llm:
        if llm_is_china_related(a["title"]):
            llm_confirmed.append(a)
    articles = china_pass + llm_confirmed

    # 分类 + 评分
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
            kw_scores = score_all_categories(a['title'])
            if not kw_scores:
                continue
            try:
                sorted_cats = sorted(kw_scores.items(), key=lambda x: -x[1])
                best_cat, best_score = sorted_cats[0]
                second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
                if best_score >= 4 and (best_score - second_score) >= 2:
                    cat = best_cat
                else:
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

    if articles:
        llm_fail_pct = llm_fail_count / len(articles) * 100
        if llm_fail_pct >= 30:
            print(f"\n⚠ column-score 降级率 {llm_fail_pct:.0f}%", file=sys.stderr)

    # 排序
    for col in classified:
        classified[col].sort(key=lambda x: -x.get('priority', 0))

    # top-10 选取
    selected = []
    used_urls = set()
    for col in COLUMN_ORDER:
        pool = [a for a in classified[col] if a['url'] not in used_urls]
        if pool:
            pick = pool[0]
            pick['column'] = col
            selected.append(pick)
            used_urls.add(pick['url'])

    remaining = []
    for col in COLUMN_ORDER:
        for a in classified[col]:
            if a['url'] not in used_urls:
                remaining.append(a)
    remaining.sort(key=lambda x: -x.get('priority', 0))
    while len(selected) < 10 and remaining:
        pick = remaining.pop(0)
        if pick['url'] not in used_urls:
            pick['column'] = pick.get('category', COLUMN_ORDER[1])
            selected.append(pick)
            used_urls.add(pick['url'])

    return classified, selected
```

## 接口定义

```python
def build_classification_result(today: datetime.date) -> tuple[dict, list]
```
返回 `(classified: {column: [article dict]}, selected: [article dict])`

## 边界处理

1. `0新闻_粗筛.md` 不存在 → 返回 `({}, [])`，不抛异常
2. `articles` 为空 → 返回空 dict 和空 list
3. 所有 `score_signals` 返回 None → 走 legacy knee 仍产出 classified
4. `assign_category` 返回 None → 跳过该 article
5. 全局 top-10 不足 10 篇 → selected 仅返回能选出的数量
6. 保持原有 `used_urls` 去重逻辑
7. 不调用 `news_archive`，不回写任何文件
8. 不写 type hints（实现中）

## 非目标
- 不修改 `run()` 写 `1新闻_链接.md` 行为（task-06）
- 不调用归档模块
- 不在本函数内打印分类进度（由 call 方负责）

## 参考
- step4.py run() L424-572 当前实现
- D-010@v1 决策
- design.md §5.3 build_classification_result

## TDD 步骤
1. mock parse_0 + score_signals → 调 build_classification_result
2. 断言 classified 有 9 栏、selected 为 list
3. 写 test_build_classification_result_no_input 返回空
4. 确认测试通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | 输入文件不存在 → 返回 `({}, [])` | 不抛异常 |
| AC-02 | mock 3 条有效文章 → `classified` 含 9 栏 key | `len(classified) == 9` |
| AC-03 | mock 3 条有效文章 → `selected` 非空 list | `len(selected) > 0` |
| AC-04 | `archive_news.py` 调 `build_classification_result` 不写 md | 目录下无新 md 文件 |
| AC-05 | `run()` 调 `build_classification_result` 后仍写 `1新闻_链接.md` | 文件存在 |
