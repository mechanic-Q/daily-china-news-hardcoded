# Phase 7: 左右栏平衡改进 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 07-column-balance
**Areas discussed:** 权重公式设计, 分配算法选择, 栏目内多文章处理

---

## 权重公式设计

| Option | Description | Selected |
|--------|-------------|----------|
| 标定公式 | weight = 4.5(卡片基础) + sum(1.2 + text_len/90 per item) | ✓ |
| 直接移植原始 skill | 直接用 2.8 + body/140 + bullets 公式映射到 heading/summary | |
| 像素实测反推 | 先跑渲染量每个卡片像素高度再反推参数 | |

**User's choice:** 标定公式
**Notes:** 当前 step8 的数据结构（heading + items[title+summary]）与原始 skill（body + bullets）不同，直接移植不合适。标定公式思路与原始 skill 一致但系数匹配当前 CSS。

---

## 分配算法选择

| Option | Description | Selected |
|--------|-------------|----------|
| 贪心 | O(n)，简单可读，8 个栏目效果已经不错 | |
| 穷举最优 | 2^8=256 种全部枚举，保证最小差值 | ✓ |

**User's choice:** 穷举最优
**Notes:** 8 个栏目规模下穷举几乎免费，保证最优解。

---

## 栏目内多文章处理

| Option | Description | Selected |
|--------|-------------|----------|
| 不拆分 | 一个栏目整体分配，视觉一致 | ✓ |
| 允许拆分 | 同一栏目的文章可分配到两栏，平衡更精确但视觉 confusing | |

**User's choice:** 不拆分
**Notes:** 穷举在不可拆分组的情况下已经足够。

---

## the agent's Discretion

- 权重公式的具体系数可在 plan 阶段微调
- 穷举算法的实现风格（位掩码 vs 递归）
- 空列分配的特殊处理

## Deferred Ideas

None
