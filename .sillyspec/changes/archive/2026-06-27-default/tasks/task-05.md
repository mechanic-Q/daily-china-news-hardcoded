---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-05
title: 实现 aggregate_scores
priority: P0
depends_on: [task-04]
blocks: [task-07, task-09]
requirement_ids: [FR-03]
decision_ids: [D-003@v1, D-007@v1]
allowed_paths:
  - step4.py
---

## 修改文件

`step4.py` — 新增函数 `aggregate_scores`

## 覆盖来源

- FR-03 聚合公式
- D-003@v1 公式定义
- D-007@v1 系数不外置

## 实现要求

**公式：** `aggregate[cat] = relevance[cat] * (AGG_RELEV_BASE + AGG_IMP_W * importance / 10 + AGG_TIME_W * timeliness / 10)`

**常量（task-04 已声明，本任务不重复）：** `AGG_RELEV_BASE = 0.5`, `AGG_IMP_W = 0.3`, `AGG_TIME_W = 0.2`

```python
def aggregate_scores(signals):
    relev = signals['relevance']
    imp = signals.get('importance', 0)
    time_v = signals.get('timeliness', 0)
    factor = AGG_RELEV_BASE + AGG_IMP_W * imp / 10 + AGG_TIME_W * time_v / 10
    return {cat: relev[cat] * factor for cat in relev}
```

## 接口定义

| 项目 | 值 |
|------|-----|
| signature | `def aggregate_scores(signals) -> dict[str, float]` |
| 返回 | `{cat: float}` key 与 `signals['relevance']` 同（9 栏）；value 浮点数 |

## 边界处理

1. **全 0：** relev=0, imp=0, time=0 → factor=0.5, aggregate[cat]=0
2. **全 10：** relev=10, imp=10, time=10 → factor=1.0, aggregate[cat]=10
3. **relev[cat]=0：** aggregate[cat]=0（单栏不归属）
4. **importance/timeliness 缺失：** 使用 0 兜底（`signals.get(.., 0)`）
5. **纯函数：** 不就地修改 signals
6. **浮点精度：** 浮点乘法，不舍入；调用方自行格式化
7. **无 type hints（CONVENTIONS）**

## 非目标

- 不实现 `assign_category`（task-06）
- 不外置系数到 yaml（D-007@v1）
- 不处理 `signals=None`（上游 `score_signals` 已确保非 None）

## 参考

- design §4.5

## TDD 步骤

1. 写 test → `test_aggregate_all_zero` / `test_aggregate_all_ten` / `test_aggregate_relev_zero` / `test_aggregate_mixed` → 失败
2. 实现
3. 通过

## 验收标准

| ID | 描述 | 预期 |
|----|------|------|
| AC-01 | 全 0 → 所有 cat aggregate=0 | True |
| AC-02 | 全 10 → 所有 cat aggregate=10.0 ±1e-9 | True |
| AC-03 | relev=0, imp/time=10 → 0 | True |
| AC-04 | signals 不被修改 | dict 引用前后相等 |
| AC-05 | 缺 importance key → 用 0 | aggregate 不报错 |
