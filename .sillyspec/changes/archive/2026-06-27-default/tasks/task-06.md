---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-06
title: 实现 assign_category（方案 X 抢占）
priority: P0
depends_on: [task-04]
blocks: [task-07, task-09]
requirement_ids: [FR-04]
decision_ids: [D-015@v1]
allowed_paths:
  - step4.py
---

# task-06: 实现 assign_category（方案 X 抢占）

## 修改文件
- step4.py 新增函数 `assign_category`；不删现有函数

## 覆盖来源
- FR-04 / D-015@v1 方案 X 抢占

## 实现要求
```python
WORLD_CLASS_THRESHOLD = 7  # 已在 task-04 声明
WORLD_CLASS_CATEGORY = '🔬 世界性科研突破'

def assign_category(signals):
    relev = signals.get('relevance', {})
    if relev.get(WORLD_CLASS_CATEGORY, 0) >= WORLD_CLASS_THRESHOLD:
        return WORLD_CLASS_CATEGORY
    other = {k: v for k, v in relev.items() if k != WORLD_CLASS_CATEGORY}
    if not other:
        return None
    best_cat, best_score = max(other.items(), key=lambda kv: kv[1])
    return best_cat if best_score > 0 else None
```

注：本函数只决定归属，不算 aggregate score；aggregate_scores 由调用方分别算。

## 接口定义
```python
def assign_category(signals: dict) -> str | None
```
signals 同 `score_signals` 返回值 (含 relevance_importance_timeliness 三个顶层键)。

## 边界处理 (≥5)
1. 🔬 relev=8, 🌾 relev=10 → 返回 🔬（抢占）
2. 🔬 relev=6, 🌾 relev=10 → 返回 🌾（未达阈值）
3. 🔬 relev=7, 其他 0 → 返回 🔬
4. 全 0 → 返回 None（无栏目命中）
5. argmax 平局（如两栏均 8）→ Python max 取第一个匹配项（dict 插入顺序，按 COLUMN_ORDER）；这是确定性的，不抛错
6. signals 缺 'relevance' 键 → 返回 None（不报错）
7. relevance 字典含 🔬 但值非数字 → 让 Python TypeError 抛出（不静默吞，调用方 try/except）
8. 调用方保证 signals 经过 `_validate_signals`，本函数信任输入

## 非目标
- 不实现 aggregate_scores（task-05）
- 不写日志
- 不处理多种 'world class' 抢占阈值配置（YAGNI）

## 参考
- design §4.1 代码片段
- task-04 COLUMN_ORDER / WORLD_CLASS_THRESHOLD 声明

## TDD 步骤
1. `tests/test_column_scoring.py` 加测试：
   - `test_assign_world_class_preempt`（🔬=8 🌾=10 → 🔬）
   - `test_assign_normal_max`（🔬=6 🌾=10 → 🌾）
   - `test_assign_all_zero_returns_none`
   - `test_assign_missing_relevance_returns_none`
   - `test_assign_tie_deterministic`（两栏同分，结果按 COLUMN_ORDER 稳定）
2. 跑测试失败
3. 实现 `assign_category`
4. 跑测试通过

## 验收标准
| AC-ID | 验证步骤 | 通过标准 |
|-------|----------|----------|
| AC-01 | signals 🔬=8 其他=0 → 结果 | == 🔬 |
| AC-02 | signals 🔬=8 🌾=10 → 结果（抢占） | == 🔬 |
| AC-03 | signals 🔬=6 🌾=10 → 结果 | == 🌾 |
| AC-04 | signals 全 0 → 结果 | is None |
| AC-05 | signals 缺 relevance → 结果 | is None |
| AC-06 | 平局按 COLUMN_ORDER dict 顺序取第一个 | 按 COLUMN_ORDER 稳定（🤖 优先于 🌾） |
