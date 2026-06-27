---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-03
title: CATEGORY_KEYWORDS 扩 🤖 词典 + 调 🚀
priority: P0
depends_on: [task-01]
blocks: [task-07, task-09]
requirement_ids: [FR-09]
decision_ids: [D-013@v1, D-014@v1]
allowed_paths:
  - step4.py
---

# task-03: CATEGORY_KEYWORDS 扩 🤖 词典 + 调 🚀

## 修改文件
- step4.py (仅 CATEGORY_KEYWORDS 字典体)

## 覆盖来源
- Requirements: FR-09 (CATEGORY_KEYWORDS 词典扩 🤖 + 调 🚀)
- Decisions: D-013@v1 (🤖 厂商列表)、D-014@v1 (🚀 重切 + CPU 厂商)

## 实现要求

1. **9 栏目 key** — CATEGORY_KEYWORDS 含 9 个 key，与 task-01 COLUMN_ORDER 字节级一致（🎖️ 含 VS16）。
   ```
   '🔬 世界性科研突破', '🤖 AI智能前沿', '🌾 农业', '🤝 扶贫',
   '⚡ 能源', '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事'
   ```

2. **新增 '🤖 AI智能前沿'** — ≥30 加权词条，权重参考 design §4.0 🤖 T1-T7（映射到 1-5 区间）：
   - T1 (weight 4-5): 大模型, DeepSeek, Qwen, 文心, Kimi, 智谱, 千亿参数, 万亿参数, 开源大模型, Agent, AGI, 多模态
   - T2 (weight 4-5): 昇腾, 寒武纪, 海光DCU, 摩尔线程, 沐曦, 壁仞, 燧原, 天数智芯, 平头哥, 昆仑芯, 登临, 算能, 智算中心, 国产GPU, 国产NPU, 算力集群
   - T3 (weight 3-4): 人形机器人, 宇树, 智元, 傅利叶, 银河通用, 优必选, 具身智能, 工业机器人, 服务机器人
   - T4 (weight 3-4): 量子计算, 量子通信, 九章, 悟空, 京沪干线, 量子比特, 量子纠错
   - T5 (weight 2-3): 智能制造, 灯塔工厂, 工业AI, AI质检, 工业大模型, 智能产线
   - T6 (weight 1-2): AI应用, 智能体, 垂域大模型, AI+, AI大模型, AI芯片
   - T7 (weight 1): AI治理, AI伦理, AI安全

3. **改写 '🚀 科技'**：
   - 删除 AI/机器人/智能制造类词条: '人工智能', 'AI', '机器人', '无人机', '算力', '智能'
   - 新增 T1 国产通用 CPU/OS (weight 3-4): 龙芯, 飞腾, 鲲鹏, 兆芯, 申威, 鸿蒙, 欧拉, 统信, 麒麟
   - '海光' 不放 🚀（仅放 🤖 T2 作 DCU 上下文强信号）
   - 保留现有: 科创, 数字, 数据, 科技, 创新, 生产线, 专利, 中关村, 芯片, 5G, 6G, 北斗, 数字经济, 数字基础设施, 工业互联网, 经济, 产业, 发展, 建设, 项目

4. **其他 7 栏目**（🔬/🌾/🤝/⚡/🏥/🧱/🎖️）现有词典不动。

5. **emoji key 字节一致性** — 9 个 key 必须与 COLUMN_ORDER 逐字节相同。

## 接口定义

`CATEGORY_KEYWORDS` 仍是 `dict[str, dict[str, int]]`。新增 '🤖 AI智能前沿' 子字典。改写 '🚀 科技' 子字典内容。其他 7 栏不变。权重正整数 1-5，沿用现有纯 dict 字面量风格。

## 边界处理

1. **重复 key 跨栏**：'量子' 在 🔬 weight 4 且 '量子计算' 在 🤖 weight 3 — 两者并存，同一标题含 '量子计算' 同时加 🔬 和 🤖 分，等待 task-04 算法统一裁决。'海光' 因词面歧义仅放 🤖 T2（'海光DCU'），🚀 不放。
2. **emoji 字节级一致性**：所有 9 栏目 key 与 step4.py 顶层 COLUMN_ORDER 逐字节一致（🎖️ 含 VS16 `U+FE0F`）。
3. **只增不删他栏**：不改 🔬/🌾/🤝/⚡/🏥/🧱/🎖️ 数据。
4. **'AI' 短串防御**：不用裸 `'AI': w`（太长尾易误伤），用组合词 `'AI应用'`, `'AI芯片'`, `'AI大模型'`, `'AI+'`。
5. **权重 1-5 正整数**：沿用现有风格，不引入浮点或负权。
6. **不写 type hints**：保持纯 dict 字面量。

## 非目标

- 不改 `score_all_categories` 算法（task-04+）
- 不改 `llm_classify_single` 等周边函数
- 不写测试（task-09）
- 不动其他 7 栏目词典
- 不引入新配置/常量

## 参考

- `step4.py:141-195` 现有 8 栏字典风格
- `design.md §4.0` 🤖 T1-T7 信号词表 + 🚀 T1-T6 信号词表
- `requirements.md` FR-09
- `decisions.md` D-013@v1, D-014@v1

## TDD 步骤

1. 写测试 `tests/test_column_scoring.py`：`test_keywords_have_9_columns`、`test_ai_column_min_30_words`、`test_tech_column_no_ai_words`
2. 确认失败（当前 CATEGORY_KEYWORDS 只 8 栏，无 🤖；🚀 含 AI 词）
3. 改 CATEGORY_KEYWORDS 字典：加 🤖 子字典 + 改写 🚀 子字典
4. 重跑测试通过

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `len(CATEGORY_KEYWORDS) == 9` | True |
| AC-02 | `'🤖 AI智能前沿' in CATEGORY_KEYWORDS` | True |
| AC-03 | `len(CATEGORY_KEYWORDS['🤖 AI智能前沿']) >= 30` | True |
| AC-04 | `'人工智能'/'机器人'/'AI' 不在 '🚀 科技'` | True |
| AC-05 | `'龙芯'/'飞腾'/'鲲鹏'/'兆芯'/'申威'/'鸿蒙' 在 '🚀 科技'` | True |
| AC-06 | `'昇腾'/'摩尔线程'/'寒武纪'/'沐曦' 在 '🤖 AI智能前沿'` | True |
