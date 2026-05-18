# Plan 1: 智能分类 (C+D混合) — Summary

**Completed:** 2026-05-18
**Files modified:** step4.py, step8.py

## What was built

### Key changes

| Function | Change |
|----------|--------|
| `classify()` | 删除 — 被 `score_all_categories()` + `llm_classify_batch()` 替代 |
| `CATEGORY_KEYWORDS` | 新增 — 8栏目×加权关键词词典（权重1-5） + post-执行扩充（加回Phase 8丢失词 + 新常见词） |
| `score_all_categories(title)` | 新增 — 对所有栏目计算加权得分 |
| `llm_classify_batch(articles)` | 新增 — 批量 LLM 分类裁决（5条一批） |
| `priority_score(title, category)` | 重写 — 差异化评分，科研突破标准更高 |
| `run()` 分类循环 | 重写 — 三阶段：高置信度直接归类 → LLM裁决 → 部分得分回退 |
| `parse_md()` | step8.py — current_title复位移至if外部，防止跨栏目泄漏 |
| `build_html()` | step8.py — 单栏时居中布局，不显示空白右栏+分割线 |

### E2E results (2026-05-17 data)

- ✅ step4: 197条→103条移除→94条→10条精选（6栏目）
- ✅ step6: 10/10 正文提取成功
- ✅ step7: 7/8 API成功 + 1 规则回退，摘要45-92字
- ✅ step8: HTML+PNG 正常生成（6栏目，左右平衡）

### E2E results (2026-05-18 data — 修复后验证)

- ✅ step4: 137条→57条→10条精选（5栏目：科研/农业/医疗/科技/军事）
- ✅ step8: 双栏布局正常（单栏回退+安全重置已修复）

### Key behavioral changes

| Before | After |
|--------|-------|
| 线性优先级if/elif→第一个命中即止 | 所有栏目加权评分→最高分胜出 |
| "箭啸喀喇昆仑" 误归科研突破 | "箭啸喀喇昆仑" 正确归入军事 |
| "火箭" 歧义导致军事新闻误分类 | "火箭" 从科研移除，"火箭炮" 只在军事 |
| `priority_score(title)` 单参数 | `priority_score(title, category)` 差异化 |
| LLM 分类 CoT 泄漏导致 0 条成功 | GLM-4 Flash 逐条分类 ~100% 成功 |
| 关键词覆盖不足，大量文章全 0 分 | 宽泛词(权重1) + 阈值≥4，过滤假阳性 |
| 分类得分=0 的文章优先度=0，排序随机 | 分类得分直接加入优先度，高分高优先 |
| 单栏时右栏空白+分割线 | 单栏时居中布局 |
