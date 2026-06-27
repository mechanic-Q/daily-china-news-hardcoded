---
author: lmr
created_at: 2026-06-27 15:55:00
schema_version: 1
doc_type: proposal
change_id: 2026-06-27-column-scoring-v2
phase: 13
---

# Proposal · Phase 13 栏目评分 v2

## 动机

Daily 流水线 `step4.py` 当前的栏目评分体系（CATEGORY_KEYWORDS 关键词加权 + 低置信度 LLM 仲裁 + 独立 priority_score）已暴露三类问题：

1. **关键词覆盖窄**：长尾新词漏判，无评分桶兜底
2. **栏目语义未显式化**：每个栏目的内在价值判定标准散落在词典里，AI 评分缺锚点
3. **AI / 机器人 / 量子等智能前沿主题无独立位置**：被混入 🚀 科技或散落各处，无法承载日益增长的报道量

Phase 13 在 `USER_MANUAL.md` 中已锁定为"栏目算法完全重做"。本次按 B+ 信号提取式重做评分链 + 引入 9 栏语义契约 + 新增 🤖 AI智能前沿栏 + 实现 🔬 世界级抢占规则 + 空栏目消失。

## 关键问题

**痛点 1：栏目语义在代码外漂浮**
没有任何文档定义"什么算 🔬 世界性科研突破"。结果：LLM 自由判断、维护者各凭直觉、关键词词典越加越乱。

**痛点 2：AI/机器人/量子无家可归**
当前 🚀 科技栏既装 AI 大模型、又装 5G、又装数字经济，权重无法在同栏内拉开；🔬 又只收世界级突破，DeepSeek 这种产业级新闻被夹在中间。

**痛点 3：世界级新闻会被分散**
关键词或 argmax 可能把"我国 EAST 实现亿度千秒（世界纪录）"分到 ⚡ 能源而非 🔬，导致顶级新闻按 ⚡ 的语境呈现，且若被分到多栏会重复出现。

**痛点 4：空栏目占位污染版面**
当日某栏无内容时输出 `## {栏目}\n（当日无真实报道，栏目留空）`，HTML 渲染出空 section 占视觉权重。

## 变更范围

1. **`step4.py` 评分链重做**：score_signals (LLM 单次结构化打分) + aggregate_scores (确定性公式) + assign_category (方案 X 抢占) + 9 栏 CATEGORY_KEYWORDS fallback
2. **9 栏语义契约**：将 8 栏（含新增 🤖 AI智能前沿）的 intent/Must/Must-not/Tier/正反例完整定义入 design §4.0；prompt 引用其简化版
3. **新栏目 🤖 AI智能前沿**（固定第 2 位）：承接 AI 大模型 / 国产 AI 芯片（昇腾/摩尔线程/沐曦等） / 国产机器人 / 量子计算 / AI+智能制造 / AI 应用
4. **🚀 科技重新切分**：T1 国产通用 CPU（龙芯/飞腾/鲲鹏/海光/兆芯/申威） + 国产 OS；AI 加速卡 / 智能制造剥离到 🤖
5. **🔬 世界级抢占规则**：🔬 relevance ≥ 7 强制归 🔬，确保顶级新闻不被分散
6. **空栏目消失（路径 A）**：step4 不写空栏 heading，step7/step8 天然兼容
7. **`step7.py` / `step8.py` `COLUMN_ORDER` 同步**：三处常量加 🤖 AI智能前沿于第 2 位（仅常量改，不动逻辑）
8. **`llm.yaml` 新增 `column-score` call site**：temp=0.0、max_tokens=256、timeout=30
9. **失败必降级**：LLM 任何异常 → 关键词层；9router 挂时进一步走纯关键词归属
10. **测试**：`tests/test_column_scoring.py` 覆盖聚合公式 / Schema 校验 / 抢占规则 / 9 栏一致性 / 空栏目 / 降级

## 不在范围内（显式清单）

- 不改 `step1_3.py`（采集）
- 不改 `step6.py`（正文提取）
- 不深改 `step7.py` / `step8.py`（仅同步 COLUMN_ORDER 常量加 🤖）
- 不改 `1新闻_链接.md` 行级格式（`### [{源}] {标题}` + `URL：{url}` 不变）
- 不改涉华过滤 / 质量过滤逻辑
- 不引入 embedding / 微调 / 本地 ML 模型
- 不实现性能并发优化（Phase 14 范围）
- 不删除 `CATEGORY_KEYWORDS` 词典（保留作 fallback；本次为 🤖 扩充、🚀 剥离）
- 不外置聚合公式系数（写死代码常量；YAGNI）
- 不引入 pytest 强依赖（测试文件以独立可运行形式提供）

## 成功标准（可验证）

| 编号 | 条件 | 验证方式 |
|------|------|---------|
| S-01 | 9 栏 `COLUMN_ORDER` 在 step4/step7/step8 三处完全一致，🤖 AI智能前沿固定第 2 位 | `rg "^COLUMN_ORDER" step4.py step7.py step8.py -A 12` |
| S-02 | dry-run 2026-06-25 数据，1新闻_链接.md 仅含**非空栏目** heading | `python3 step4.py --date 2026-06-25 --dry-run` 后查看 md 输出 |
| S-03 | LLM 关闭（mock LLMCallError）时 step4 仍能产出 top-10，走 legacy_path | 单测 mock |
| S-04 | mock signals 中 🔬 relev=8、🌾 relev=10 → assign_category 返回 🔬 | 单测 |
| S-05 | mock 同一 url 在多栏 relevance > 0 → 仅出现在唯一栏目 | 单测 |
| S-06 | llm.yaml 含 `column-score` 且 temperature=0.0 | `yaml.safe_load` assert |
| S-07 | `CATEGORY_KEYWORDS` 含 9 栏，🤖 词典覆盖国产 GPU/CPU/大模型/机器人/量子 ≥30 词 | 单测 + 词典断言 |
| S-08 | step4 P95 ≤ 10 min（200 篇）实测 | `time python3 step4.py --date <today>` |
| S-09 | 实现代码无 type hints（CONVENTIONS §2.3 一致性）| `rg "->\s*(dict\|str\|int\|None\|list\|tuple\|bool)" step4.py` 结果为空 |
| S-10 | 旧 1新闻_链接.md（8 栏版本）仍能被新 step7/step8 解析（缺 🤖 不报错）| 兼容性手测 |
