---
wave: 1
depends_on: []
files_modified:
  - step8.py
requirements: [BAL-01, BAL-02]
autonomous: true
---

# Plan 1: 左右栏平衡 — 视觉权重穷举分配

## Goal

替换 `balance_columns()` 的纯字符贪心分配为视觉权重穷举最优分配。

## must_haves

- `balance_columns()` 使用 `_estimate_weight()` 计算每个栏目的视觉权重
- 穷举 2^8=256 种分配方案，选择左右权重差值最小的
- 同一栏目（heading）不拆分，保持整体分配
- 输出格式不变（返回 `left, right` 两个列表）
- 下游（`build_html`, `run`）不需要修改

---

## Task 1: 新增 `_estimate_weight(group)`

<read_first>
- step8.py（当前 balance_columns 函数和 CSS 样式参数）
</read_first>

<action>

在 `balance_columns()` 函数之前新增 `_estimate_weight(group)` 函数：

```python
def _estimate_weight(group):
    items = group.get("items", [])
    return 4.5 + sum(1.2 + (len(item.get("title", "")) + len(item.get("summary", ""))) / 90 for item in items)
```

公式含义：
- `4.5` — section-card 固定开销（border-top 2px + padding-top 10px + margin-bottom 18px + heading h2 约 46px）
- `1.2` — 每个 `<li>` 的 margin-bottom 10px + `::before` bullet 圆点空间
- `text_len/90` — 文本行数估算（24px font, line-height 1.73, 约 21 字/行 → 90 字 ≈ 4 行）
</action>

<acceptance_criteria>
- `step8.py` 包含 `def _estimate_weight(group):` 函数定义
- 输入 `{"heading": "军事", "items": [{"title": "A", "summary": "B"}]}` 返回约 5.74
- 不依赖外部模块
</acceptance_criteria>

---

## Task 2: 重写 `balance_columns()`

<read_first>
- step8.py（当前 balance_columns 和 Task 1 新增的 _estimate_weight）
</read_first>

<action>

重写 `balance_columns(sections)`：

```python
def balance_columns(sections):
    groups = {}
    for sec in sections:
        groups.setdefault(sec["heading"], []).append(sec)

    ordered = []
    for heading, items in groups.items():
        weight = _estimate_weight({"heading": heading, "items": items})
        ordered.append({"heading": heading, "items": items, "weight": weight})

    n = len(ordered)
    if n == 0:
        return [], []
    if n == 1:
        return [ordered[0]], []

    best_mask = 0
    best_diff = float("inf")

    for mask in range(1 << n):
        left_weight = 0
        right_weight = 0
        for i in range(n):
            if mask & (1 << i):
                right_weight += ordered[i]["weight"]
            else:
                left_weight += ordered[i]["weight"]
        diff = abs(left_weight - right_weight)
        if diff < best_diff:
            best_diff = diff
            best_mask = mask

    left = []
    right = []
    for i in range(n):
        if best_mask & (1 << i):
            right.append(ordered[i])
        else:
            left.append(ordered[i])

    return left, right
```

删除旧版 `balance_columns`（基于 chars 的贪心逻辑）。
</action>

<acceptance_criteria>
- `balance_columns()` 函数签名和返回格式不变（两个列表）
- 对 8 个栏目穷举 256 种分配，选择差值最小的
- `run()` 调用 `balance_columns(sections)` 无需修改
- 同一 heading 下的所有 items 保持不拆分
- `print(f"...左右栏分配: ...")` 仍然正常显示
</acceptance_criteria>

---

## Task 3: 用真实数据 E2E 验证

<read_first>
- step8.py（修改后的完整文件）
- /mnt/e/每日新中国/2026-05-17/3新闻_概述.md（输入）
</read_first>

<action>

```bash
cd /mnt/e/Daily && python3 step8.py --date 2026-05-17
```

检查控制台输出和生成的文件：
1. 左右栏分配合理，不出现极端偏斜
2. HTML 正常生成
3. PNG 正常生成

对比旧输出：视觉平衡应优于旧版。
</action>

<acceptance_criteria>
- `python3 step8.py --date 2026-05-17` 执行成功（exit code 0）
- HTML 文件正常生成
- PNG 文件正常生成
- 左右栏栏目数分布合理（无单栏为 0 的极端情况）
</acceptance_criteria>

---

## Verification Criteria

- [x] BAL-01（移植权重估算）→ Task 1
- [x] BAL-02（视觉权重替代纯字符）→ Task 2
- [x] 单文件修改（step8.py）
- [x] 输出格式不变
- [x] 有测试数据（2026-05-17）可验证
