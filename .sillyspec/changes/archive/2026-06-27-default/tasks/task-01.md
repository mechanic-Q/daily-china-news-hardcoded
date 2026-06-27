---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-01
title: COLUMN_ORDER 三处同步加 🤖
priority: P0
depends_on: []
blocks: [task-03, task-07, task-09, task-10]
requirement_ids: [FR-05]
decision_ids: [D-012@v1, D-017@v1]
allowed_paths:
  - step4.py
  - step7.py
  - step8.py
---

# task-01: COLUMN_ORDER 三处同步加 🤖

## 修改文件
- step4.py (replace local col_order inside run() AND introduce top-level COLUMN_ORDER constant)
- step7.py (top-level COLUMN_ORDER)
- step8.py (top-level COLUMN_ORDER)

## 覆盖来源
- Requirements: FR-05 (9 栏 COLUMN_ORDER 三处同步)
- Decisions: D-012@v1 新增 🤖 第 9 栏 / D-017@v1 step7/step8 同步常量

## 实现要求
The exact 9-element list (in this order; emoji must be byte-exact, including 🎖️ which contains VS16):
```
COLUMN_ORDER = [
    '🔬 世界性科研突破',
    '🤖 AI智能前沿',
    '🌾 农业',
    '🤝 扶贫',
    '⚡ 能源',
    '🏥 医疗',
    '🚀 科技',
    '🧱 材料',
    '🎖️ 军事',
]
```

1. step4.py: 当前 run() 内 L312-315 局部 col_order 是 8 栏。将 col_order 提升为模块顶层常量 COLUMN_ORDER（9 栏）；run() 内全部 col_order 引用改为 COLUMN_ORDER。
2. step7.py: L24 已有 COLUMN_ORDER（8 栏），扩为 9 栏，🤖 AI智能前沿 插入第 2 位。
3. step8.py: L20 已有 COLUMN_ORDER（8 栏），同步扩为 9 栏。
4. 三处使用完全相同的字面常量（含 emoji codepoint，含中间空格）。建议把常量集中到 step4.py 然后 step7/step8 复制粘贴（不通过 import 共享，遵循文件接力风格）。

## 接口定义
- 顶层常量声明，无函数变更。
- 类型：list[str]，长度 9。

## 边界处理
1. 空值不适用（常量始终存在）。
2. 兼容旧行为：旧 8 栏 `1新闻_链接.md` 仍能被新 step7/step8 解析（缺 🤖 即该栏目无内容，渲染时自然消失，不报错）。
3. 异常：写入或读取常量不应有异常路径。
4. 不修改传入参数：常量不可变（虽 Python list 可变，约定不写入）。
5. 歧义/冲突：原 step4.py:312 局部 col_order 与 step7/step8 顶层 COLUMN_ORDER 重复，本次统一为顶层 COLUMN_ORDER。
6. emoji codepoint：🎖️ 含 VS16 变体选择符（U+1F396 + U+FE0F），必须字节级一致。

## 非目标
- 不实现评分逻辑（task-04/05/06）。
- 不改 CATEGORY_KEYWORDS（task-03）。
- 不改 step7.py / step8.py 的其他逻辑（balance_columns / parse_md 等不动）。
- 不把 COLUMN_ORDER 移到独立模块（不破坏文件接力风格）。

## 参考
- 现有 step7.py:24-35 与 step8.py:20-30 的列表字面量风格。
- 现有 step4.py:312-315 局部 col_order 写法。

## TDD 步骤
1. 写测试：在 tests/test_column_scoring.py 中加 test_column_order_consistency（导入三处常量做 == 比较）。
2. 确认失败（当前 step4 无顶层 COLUMN_ORDER → ImportError；step7/8 仍 8 栏 → assertion fail）。
3. 改 step4 顶层加常量；改 step7/8 加 🤖。
4. 重跑测试通过。
5. 回归：python3 step4.py --date 2026-06-25 --dry-run 仍可解析。

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `rg "^COLUMN_ORDER = " step4.py step7.py step8.py` | 三个文件各有一处声明 |
| AC-02 | 三处 list 字面量字符串比对 | 完全一致，9 元素 |
| AC-03 | 🤖 AI智能前沿 位于第 2 位 | index = 1 |
| AC-04 | 旧 8 栏 1新闻_链接.md 由新 step7 parse_1news 解析 | 不报错，🤖 栏目 items 为空 |
| AC-05 | step4.py run() 内不再有局部 col_order | `rg "col_order" step4.py` 无匹配（或仅 COLUMN_ORDER） |
