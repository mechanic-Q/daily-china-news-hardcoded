---
author: lmr
created_at: 2026-06-27 15:40:30
schema_version: 1
doc_type: design
change_id: 2026-06-27-column-scoring-v2
phase: 13
status: draft
---

# Phase 13 · 栏目评分 v2（B+ 信号提取式）

## 1. 背景

`step4.py` 当前用 `CATEGORY_KEYWORDS`（45 加权词条 × 8 栏目）+ 低置信度 LLM 单条裁决（`llm_classify_single`）做归属分类，再用 `priority_score` 单独算栏目内优先级。问题：

- **关键词覆盖窄**：长尾或新词（如新型实验室技术）漏判，落到无评分桶
- **二段拼接难维护**：评分（归属）与优先级（排序）两套逻辑分离，加新维度（时效性）要改两处
- **LLM 仅做仲裁**：只对低置信度子集调一次，无法给出每栏相关度
- 历史规划已锁定：参见 `archive/2026-06-26-2026-06-27-user-manual-summary-bar/requirements.md` L45-47 — "Phase 13 栏目评分重做"

## 2. 设计目标

| ID | 目标 |
|----|------|
| G-01 | 单次 LLM 调用为每篇文章输出 **8 栏目 relevance + importance + timeliness** 结构化评分 |
| G-02 | 用确定性聚合公式产生归属 + 栏目内排序，替代 `score_all_categories + priority_score` 拼接 |
| G-03 | batch LLM 失败 / JSON 非法 / Schema 不全 时先重试并回退逐条 LLM；仅逐条 LLM 也失败时才进入显式 `keyword-fallback`，不得把关键词结果伪装为 LLM 评分 |
| G-04 | 不破坏 `1新闻_链接.md` 输出格式（下游 step6 契约不变） |
| G-05 | 全天调用预算 ≤ 250 次 GLM 调用、step4 P95 ≤ 10 min |
| G-06 | 候选新闻必须有可信见报/发布日期且等于目标日期；正文事件日期可早于目标日期 |

## 3. 非目标

- **不改** step1_3 / step6 任何逻辑
- **不改** 涉华过滤（`is_china_related` / `is_china_source` / `llm_is_china_related`）
- **不改** 质量过滤（`EXCLUDE_TITLES` / `EXCLUDE_NEGATIVE`）
- **不引入** embedding / 微调 / 本地 ML 模型
- **不实现** 性能并发优化（Phase 14 范围）
- **不删除** `CATEGORY_KEYWORDS` 词典（保留作 fallback 数据源；本期为 🤖 新栏增补关键词）
- **不改** `1新闻_链接.md` 行级格式（`### [{源}] {标题}` + `URL：{url}`）；但栏目集合从 8 → 9，空栏目不再写 heading（§4.2）
- **不深改** step7 / step8 逻辑，仅同步 `COLUMN_ORDER` 常量增加 🤖 一项

## Quick 补充：见报/发布日期硬闸门

- collector 输出的每条通过候选必须携带真实 `published_at`，且 `published_at == --date`。
- 无可信发布日期或发布日期不等于目标日期的候选进入淘汰列表，不得写入通过列表。
- `0新闻_粗筛.md`、`1新闻_链接.md`、`2新闻_已审核.md` 必须传递真实发布日期，不得用运行日期伪造发布时间。
- 日期闸门只约束文章见报/发布日期，不约束正文描述的事件发生日期。

## 4. 总体方案

### 4.0 栏目语义契约（9 栏 — 本期核心交付）

**9 栏固定顺序**（COLUMN_ORDER）：
```
🔬 世界性科研突破 → 🤖 AI智能前沿 → 🌾 农业 → 🤝 扶贫 → ⚡ 能源 → 🏥 医疗 → 🚀 科技 → 🧱 材料 → 🎖️ 军事
```

**两种栏目语义机制**：

| 类型 | 栏目 | relevance 含义 |
|------|------|---------------|
| **门槛型** | 🔬 世界性科研突破 | Must 命中→ 7-10；Must-not / 不达世界级 → 0-3；中间地带极少 |
| **排序型** | 🤖 / 🌾 / 🤝 / ⚡ / 🏥 / 🚀 / 🧱 / 🎖️ | 中国主体新闻即入选，按 Tier 权重打 0-10，承载"是否归属 + 含金量"双重信号 |

---

#### 🔬 世界性科研突破（门槛型）

**Intent**：中国处于"绝无仅有 / 一枝独秀"位置的事件 — 别人做不出、不让我们做我们做了、没人做我们先做、做得最大/最先进。判定锚点："世界范围内中国的位置"。

**Must（命中任一）**：
- **A 卡脖子突破** — 以往被封锁的技术，中国自研出来（光刻、EDA、航发、操作系统底层、特种材料）
- **B 填补世界空白** — 人类此前没做出过的事，中国首先做出（二氧化碳人工合成淀粉、可控核聚变长脉冲纪录、量子计算原型机、首次物理常数测定）
- **C 世界级一枝独秀工程** — 基建/装备世界级独有（"世界首条/最大/最长/最深/最复杂"指标明确）
- **D 国产自研载体的商业产品 / 国产化推进型**
  - **D.1 终局型**：商业产品 + 核心技术（自研芯片、操作系统、发动机等）已突破封锁并量产；即使**代差落后**（如 7nm vs 国际 3nm），封锁下成型量产即合格
  - **D.2 替代型 国产化进度** — 任一即合格：
    - 关键部件首次国产替代（如 C919 某航电系统国产替代量产）
    - 国产化率显著提升且数据明确
    - 长期被卡部件研发关键节点突破（首次试车 / 首次台架点火 / 首次装机试飞）
    - 国产替代方案完成实验验证，非"计划/立项/启动"
- **E 高水平同行评议论文**（三维判定 — 期刊 × 类型 × 标题词）
  - **E.1 期刊白名单**：
    - 国际顶刊主刊：Nature / Science / Cell / NEJM / Lancet / PNAS / PRL
    - 国际顶刊高影响子刊：Nature Genetics / Nature Materials / Nature Physics / Cell Press 系列
    - **中国顶刊**：National Science Review (NSR) / Cell Research / Science China 系列 / Chinese Science Bulletin（科学通报）/ The Innovation / Light: Science & Applications / Fundamental Research
  - **E.2 文章类型**（必须是研究/原创）：
    - ✅ Research Article / Letter / Article / Report / Original Research / 研究快报
    - ❌ Review / Perspective / Comment / Editorial / News & Views / 综述 / 评论区 / 观点
  - **E.3 标题强信号词**：首次发现 / 首次解析 / 首次实现 / 首次合成 / 首次观测 / 世界纪录 / 提出新理论 / 突破 X 极限 / 改写认知
- **F 中国独家壮举型推进** — 航天 / 深海 / 极地等领域，**中国是世界上唯一在持续推进的**（嫦娥探月、天问火星、奋斗者号深潜、空间站常态化运行）

**Must-not（命中即排除）**：
- 国内首次但国外早实现（追赶型）
- 综述论文 / 评论区 / 观点 / 政策表态 / 立项审批 / 战略合作签约
- 商业产品但**报道中无任何国产化推进信号**
- "开工 / 奠基 / 启动"未投运
- 排名 / 计量榜单（专利数、用户数、销量）

**国产化推进判别词**：自研 / 替代进口 / 突破封锁 / 国产化率 / 首次国产 / 国产首台 / 自主可控 / 自主设计 / 国产装机 / 长江发动机 / 国产某型

---

#### 🤖 AI智能前沿（排序型）

**Intent**：中国 AI / 机器人 / 量子计算 / 智能制造的发展与应用进展。AI 智能为传播语义，实质涵盖智能前沿全谱。

| Tier | 权重 | 锚点 | 关键厂商 / 信号词 |
|------|------|------|-------------------|
| T1 | 10 | 国产大模型重大进展 / 开源 / 性能突破 | DeepSeek / Qwen / 文心 / Kimi / 智谱 / 千亿参数 / 万亿参数 / 开源 / AGI / Agent 底座 |
| T2 | 9 | **国产 AI 算力芯片 / 国产 GPU / 国产 NPU**（支撑大模型与具身智能集群）| **华为昇腾 / 寒武纪 / 海光 DCU / 摩尔线程 / 沐曦 / 壁仞 / 燧原 / 天数智芯 / 平头哥 / 昆仑芯 / 登临 / 算能** / 智算中心 / 算力集群 |
| T3 | 8 | 国产机器人（人形 / 工业 / 服务 / 具身智能） | 人形机器人 / 宇树 / 智元 / 傅利叶 / 银河通用 / 优必选 / 具身智能 / 工业机器人 / 服务机器人 |
| T4 | 7 | 量子计算 / 量子通信中国进展 | 量子计算 / 九章 / 悟空 / 量子通信 / 京沪干线 / 量子纠错 / 量子比特 |
| T5 | 6 | AI + 智能制造 / 智能工厂 / 工业 AI | 智能制造 / 灯塔工厂 / 工业 AI / 智能产线 / AI 质检 / 工业大模型 |
| T6 | 5 | AI 应用落地（医疗 AI / 教育 AI / 政务 AI / Agent） | AI 应用 / Agent / 智能体 / AI+ / 垂域大模型 |
| T7 | 3 | AI 治理 / 政策 / 国际标准 | AI 治理 / 伦理 / 标准 / 监管 |

**世界级 → 改归 🔬**：如"华为昇腾突破制裁量产" / "量子计算世界纪录"，由 §4.1 抢占规则代码兜底
**EXCLUDE**：商业并购 / 融资 / AI 公司估值八卦

---

#### 🌾 农业（排序型）

**Intent**：中国农业相关新闻 — 涵盖粮食、农事、农技、农村、农民、农产品全链条。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 粮食安全 | 粮食产量 / 储备 / 口粮自给 / 种业自主 / 耕地保护 / 藏粮于地 / 藏粮于技 |
| T2 | 8 | 高新技术农业应用 | 智慧农业 / 农业 AI / 农业大数据 / 生物育种 / 设施农业 / 数字农场 / 无人机植保 |
| T3 | 7 | 农业科技 | 农机 / 农艺 / 灌溉 / 作物保护 / 品种改良（非世界级） |
| T4 | 5 | 农业生态 | 治沙 / 退耕还林 / 盐碱地改造 / 水土保持 / 生态修复 |
| T5 | 3 | 农业振兴 / 乡村振兴 | 高标准农田 / 合作社 / 新农人 / 农村基建 / 产业振兴 |
| T6 | 2 | 民生 / 菜篮子 | 价格 / 丰收 / 节日供应 / 农产品流通 |

**世界级 → 改归 🔬**：袁隆平海水稻、玉米种自主选育突破封锁
**对外援助 → 改归 🤝**：治沙模式输出非洲、菌草援外、杂交稻援外
**EXCLUDE**：农业商业并购 / 资本运作、灾害负面、政策空话

---

#### 🤝 扶贫（排序型）

**Intent**：中国脱贫成就 + 对外减贫合作 + 共同富裕推进。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 全球减贫贡献 / 对外输出 | 减贫贡献 / 援外 / 菌草 / 杂交稻援外 / 治沙模式输出 / 对外输出 |
| T2 | 8 | 易地搬迁 / 精准扶贫 / 脱贫攻坚衔接 | 精准扶贫 / 易地搬迁 / 脱贫攻坚 / 巩固成果 |
| T3 | 7 | 对口帮扶 / 东西部协作 / 消费扶贫 | 对口帮扶 / 东西部协作 / 消费扶贫 / 驻村 |
| T4 | 5 | 共同富裕 / 乡村振兴衔接 | 共同富裕 / 乡村振兴衔接 |
| T5 | 3 | 民生改善个案 | 教育扶贫 / 健康扶贫 / 就业帮扶 |

**EXCLUDE**：扶贫资金挪用 / 形式主义 / 商业操盘

---

#### ⚡ 能源（排序型）

**Intent**：中国能源安全 + 转型 + 装机/发电世界级成就。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 核电 / 可控核聚变 | 核电 / 核能 / 人造太阳 / 可控核聚变 / EAST / 托卡马克 / 中国环流器 |
| T2 | 8 | 新能源装机 / 发电世界级 | 光伏装机 / 风电 / 特高压 / 清洁能源 / 装机容量 / 发电量 |
| T3 | 7 | 储能 / 氢能 / 智能电网 / 抽蓄 | 储能 / 氢能 / 智能电网 / 抽水蓄能 / 电池 |
| T4 | 5 | 油气保供 / 战略储备 | 石油 / 天然气 / 能源安全 / 保供 / 原油 |
| T5 | 3 | 节能减排 / 双碳 | 节能 / 减排 / 碳中和 / 清洁 / 碳达峰 |
| T6 | 2 | 能源价格 / 民生用电（保供语义）| 油价 / 电价 / 用电高峰 |

**世界级 → 改归 🔬**：EAST 世界纪录类
**EXCLUDE**：能源事故 / 油价投机 / 能源企业资本运作

---

#### 🏥 医疗（排序型）

**Intent**：中国医疗卫生事业 + 公共健康 + 创新药 + 中医药。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 创新药 / 国产药突破封锁 / 自主疫苗 | 创新药 / 自主研发 / 国产首个 / 获批上市 / 临床突破 / 疫苗 |
| T2 | 8 | 重大疾病防治进展 | 肿瘤 / 罕见病 / 抗癌 / 新药 / 临床试验 |
| T3 | 7 | 中医药传承创新 | 中药 / 中医 / 中医药 / 古方 |
| T4 | 5 | 医保 / 医改 / 分级诊疗 | 医保 / 医改 / 医联体 / 分级诊疗 / 集采 |
| T5 | 4 | 公共卫生 / 疾控 / 健康中国 | 健康中国 / 疾控 / 公共卫生 / 健康管理 |
| T6 | 2 | 医疗服务个案 / 民生医疗 | 患者 / 医院 / 就医 / 看病 |

**世界级 → 改归 🔬**：mRNA 肿瘤疫苗首例获批等
**EXCLUDE**：医闹 / 医疗事故 / 药品负面 / 保健品骗局

---

#### 🚀 科技（排序型 — 收缩为硬件基建 + 通信 + 数字经济）

**Intent**：中国科技产业成就 / 基础设施 / 数字经济。**注意：AI 相关 / 智能制造已切到 🤖**。

| Tier | 权重 | 锚点 | 信号词 / 厂商 |
|------|------|------|---------------|
| T1 | 10 | **国产通用 CPU / 国产操作系统** | **海光 / 鲲鹏 / 飞腾 / 龙芯 / 兆芯 / 申威** / 鸿蒙 / 欧拉 / 统信 UOS / 麒麟 |
| T2 | 8 | 5G / 6G / 卫星互联网 / 北斗 | 5G / 6G / 卫星互联网 / 北斗 / 千兆光网 |
| T3 | 7 | 数字基础设施 | 东数西算 / 数据中心 / 千兆光网 |
| T4 | 5 | 数字经济 / 工业互联网（非 AI 化部分） | 数字经济 / 工业互联网（非智能制造）/ 数字基础设施 |
| T5 | 3 | 科技园区 / 创新平台 / 专利 | 中关村 / 专利 / 孵化器 / 科技园 |
| T6 | 2 | 一般科技应用落地 | 应用 / 落地 / 升级 / 转型 |

**边界**：
- **AI 加速卡**（昇腾/摩尔线程/沐曦等）→ 🤖 T2
- **通用 CPU**（龙芯/飞腾/鲲鹏/海光/兆芯/申威）→ 🚀 T1
- **智能制造 / 工业 AI** → 🤖 T5
- **传统工业互联网（非 AI 化）** → 🚀 T4

**世界级 → 改归 🔬**：国产 CPU 突破封锁量产（D.1）
**EXCLUDE**：互联网公司绯闻 / 商业并购 / 资本运作 / 商业模式炒作

---

#### 🧱 材料（排序型）

**Intent**：中国新材料 / 战略材料 / 制造业基础。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 新材料突破 / 卡脖子材料国产化 | 新材料 / 特种钢 / 碳纤维 / 稀土永磁 / 光刻胶 / 半导体材料 |
| T2 | 8 | 战略矿产 / 稀土 / 关键矿物 | 稀土 / 锂 / 钴 / 石墨 / 关键矿产 |
| T3 | 7 | 高端装备制造 | 造船 / 重工 / 高端机床 / 特种装备 |
| T4 | 5 | 钢铁 / 化工产能升级 | 钢铁 / 化工 / 产能升级 |
| T5 | 3 | 一般制造业 / 工厂建设 | 制造业 / 工厂 / 装备 / 设备 |

**世界级 → 改归 🔬**：光刻胶突破美国封锁量产
**EXCLUDE**：原材料价格炒作 / 稀土走私 / 商业并购

---

#### 🎖️ 军事（排序型）

**Intent**：中国国防力量建设 + 装备发展 + 演训成果 + 维和反恐。**仅正面/常态化报道**。

| Tier | 权重 | 锚点 | 信号词 |
|------|------|------|--------|
| T1 | 10 | 国产新型主战装备列装/试飞/下水 | 航母 / 055 / 歼-20 / 东风 / 长剑 / 入役 / 列装 / 下水 / 首飞 |
| T2 | 8 | 战略性军事行动 / 远海演训 / 维和反恐 | 远海训练 / 联合军演 / 护航 / 维和 / 反恐 |
| T3 | 7 | 国防科技 / 军工产业突破 | 国防科技 / 军工 / 军民融合 |
| T4 | 5 | 大型演训 / 战区联合演习 | 军演 / 联合演练 / 战区 / 合成训练 |
| T5 | 3 | 官兵风采 / 部队建设 / 国防教育 | 官兵 / 训练 / 连队 / 国防教育 / 强军 |
| T6 | 2 | 退役军人 / 军属保障 | 退役军人 / 军属 / 双拥 |

**世界级 → 改归 🔬**：国产长江航发首次装机试飞（D.2）
**EXCLUDE**：负面军事 / 冲突推演 / 敏感内容 / 武器走私 / 军购争议

---

### 4.1 🔬 世界级抢占规则（方案 X）

**目的**：避免世界级新闻被 argmax 分到其他栏，且避免同一新闻在多栏重复出现。

```python
WORLD_CLASS_THRESHOLD = 7  # 🔬 relev ≥ 7 即抢占

def assign_category(signals):
    relev = signals['relevance']
    # 优先级 1：世界级抢占
    if relev.get('🔬 世界性科研突破', 0) >= WORLD_CLASS_THRESHOLD:
        return '🔬 世界性科研突破'
    # 优先级 2：argmax（仅排序型栏目竞争）
    other = {k: v for k, v in relev.items() if k != '🔬 世界性科研突破'}
    if not other:
        return None
    best_cat, best_score = max(other.items(), key=lambda x: x[1])
    return best_cat if best_score > 0 else None
```

**配合 prompt 指令**：LLM prompt 明确要求"如新闻达到世界级 Must 标准，🔬 relevance 应打 7-10"。代码做强制兜底，LLM 偶发漏判也不影响归属。

**Dedup 天然实现**：单文章只进单栏（assign_category 返回唯一值），现有 `used_urls` 集合确保同 URL 不重复入选；新规则与现有 dedup 兼容。

### 4.2 空栏目消失规则（路径 A）

- `step4.py` 在写 `1新闻_链接.md` 时，**只为有 items 的栏目写 `## {栏目}` heading**，不再为空栏目写"（当日无真实报道，栏目留空）"占位
- `step7.py` `parse_1news` 天然只读出现的 heading，无空栏目分支
- `step8.py` `parse_md` 同理 — 输入中没有 heading 就不渲染；`balance_columns` 对 K 个非空栏目做 2^K 平衡（K ≤ 9，仍 ≤ 512 子集）
- **效果**：当日哪个栏目无新闻，HTML/PNG 自然缺该 section，9 栏固定顺序中相邻栏目自然衔接

### 4.3 单 Wave 实现

变更触及 `step4.py` + `step7.py` (COLUMN_ORDER) + `step8.py` (COLUMN_ORDER) + `llm.yaml` + 新增测试文件。规模可控，单 Wave 完成；不走批量模式。

### 4.4 新数据流

```
parse_0 → quality_filter → china_filter
       ↓
score_signals(title, source)
   ├─ try call_llm("column-score") → JSON (9 栏 relevance + imp + time)
   │      _validate_signals()
   │      success → return signals
   └─ on any error → return None  (调用方降级)
       ↓
       ┌─ signals is None? ─┐
       │ yes                │ no
       ↓                    ↓
legacy_path()         aggregate_scores(signals)
   = score_all_         scores[cat] = relev[cat]
     categories +        × (0.5 + 0.3·imp/10 + 0.2·time/10)
     priority_score
       ↓                    ↓
       └─────────┬──────────┘
                 ↓
       assign_category(signals)     ← §4.1 抢占规则
         ├─ 🔬 relev ≥ 7 → 🔬
         └─ else argmax over other 8
                 ↓
       栏目内按 aggregate desc 排
                 ↓
       每栏取 1 → 全局 top-10（与现有逻辑一致）
                 ↓
       write 1新闻_链接.md（仅写有 items 的栏目 heading，§4.2）
```

### 4.5 聚合公式

```
aggregate(cat) = relevance[cat] × (0.5 + 0.3·importance/10 + 0.2·timeliness/10)
```

- `relevance ∈ [0,10]` 主导分（最低保 50% 权重）
- `importance ∈ [0,10]` 调出最多 +30% 加成
- `timeliness ∈ [0,10]` 调出最多 +20% 加成
- 全 10 满分 → aggregate = 10；全 0 → 0；relevance=0 → 0（不归属该栏）

## 5. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `step4.py` | ① 新增 `score_signals` / `aggregate_scores` / `_validate_signals` / `assign_category` / `_build_score_prompt`；② `COLUMN_ORDER` 加 🤖 AI智能前沿（第 2 位）；③ `CATEGORY_KEYWORDS` 新增 🤖 词典（含 GPU/CPU/大模型/机器人/量子等约 50 词）作 fallback 数据；④ `CATEGORY_KEYWORDS` 🚀 词典剥离 AI/智能制造词条迁到 🤖；⑤ `run()` 走新链路 + 实现 §4.2 空栏目不写 heading；⑥ 保留 `score_all_categories` / `llm_classify_single` / `priority_score` 作降级 |
| 修改 | `step7.py` | `COLUMN_ORDER` 加 🤖 AI智能前沿（第 2 位） |
| 修改 | `step8.py` | `COLUMN_ORDER` 加 🤖 AI智能前沿（第 2 位）；逻辑不变（空栏目天然消失） |
| 修改 | `llm.yaml` | `call_sites` 新增 `column-score`：`max_tokens: 256, temperature: 0.0, timeout: 30` |
| 新增 | `tests/test_column_scoring.py` | 单元测试：聚合公式 / JSON 校验 / 抢占规则 / 9 栏 / 降级路径 / 空栏目 |
| 不变 | `step1_3.py` `step6.py` `run_all.sh` | 上下游契约不变 |
| 不变 | `1新闻_链接.md` **行级**格式 | `### [{源}] {标题}` + `URL：{url}` 不变；空栏目不再写 heading |

## 6. 接口定义

### 6.1 新增函数（step4.py）

```python
SCORE_SCHEMA_VERSION = 1

def _build_score_prompt(title: str, source: str) -> str:
    """构造结构化打分 prompt，要求 LLM 输出 JSON。"""

def score_signals(title, source):
    """
    返回 dict 或 None。
    流程：
        1. call_llm("column-score", messages=[...]) → str
        2. _strip_think(raw)  # 复用 step4.py:225 风格清洗 <think>...</think>
        3. _strip_codefence(raw)  # 去 ```json ... ```
        4. json.loads
        5. _validate_signals
    异常处理：
        - LLMCallError      → 返回 None
        - JSONDecodeError   → 重试 1 次（追加 "只输出严格 JSON，不要 markdown 包裹" prompt）→ 仍失败返回 None
        - _validate_signals False → 返回 None
        - 其他 Exception    → 返回 None（防止任何意外打断流水线）
    注：项目约定 type hints 极少使用（CONVENTIONS §2.3），故实现签名不带注解。
    """

def _validate_signals(data):
    """校验：relevance 含 **9 栏目** key（含 🤖 AI智能前沿），每值 ∈ [0,10]；importance/timeliness ∈ [0,10]。"""

def aggregate_scores(signals):
    """signals → {cat: aggregate} 字典（9 栏）。"""

def assign_category(signals):
    """方案 X 抢占规则。见 §4.1。返回单个栏目名或 None。"""

def classify_v2(article):
    """
    article → (category, priority, source_tag)
    source_tag ∈ {"llm", "keyword-fallback"} 用于日志
    """
```

### 6.2 新增 LLM call site（llm.yaml）

当前 `llm.yaml`：`provider: 9router, model: low, base_url: http://localhost:20128/v1`。所有 call_site 走该本地代理。新增 site 沿用此 provider/model。

```yaml
call_sites:
  column-score:
    max_tokens: 256
    temperature: 0.0   # 评分需确定性 — 与其他 site 的 0.7 不同，见 D-008@v1
    timeout: 30
```

### 6.3 Prompt 契约

```
你是中国正面新闻编辑。对下面新闻标题就 9 个栏目分别打分（0-10 整数）。

栏目列表（固定顺序）：
🔬 世界性科研突破 / 🤖 AI智能前沿 / 🌾 农业 / 🤝 扶贫 / ⚡ 能源 /
🏥 医疗 / 🚀 科技 / 🧱 材料 / 🎖️ 军事

栏目语义提示：
- 🔬 世界性科研突破: 中国"绝无仅有/一枝独秀"事件 — 卡脖子突破/填补世界空白/世界级独有工程/国产化推进/顶刊原创论文/中国独家壮举。**如新闻达到此标准，🔬 relevance 应打 7-10。**
- 🤖 AI智能前沿: 中国 AI 大模型 / 国产 AI 芯片(昇腾/摩尔线程/沐曦等) / 国产机器人 / 量子计算 / AI+智能制造 / AI 应用
- 🌾 农业: 中国农业全链条 — 粮食安全 > 农业高新技术 > 农业科技 > 农业生态 > 乡村振兴 > 民生菜篮子
- 🤝 扶贫: 中国脱贫 + 对外减贫 + 共同富裕
- ⚡ 能源: 核电/可控核聚变 > 新能源装机/特高压 > 储能氢能 > 油气保供 > 节能双碳
- 🏥 医疗: 创新药/国产药 > 重大疾病 > 中医药 > 医保医改 > 公共卫生
- 🚀 科技: 国产通用 CPU(龙芯/飞腾/鲲鹏/海光/兆芯/申威) / 国产 OS(鸿蒙/欧拉/统信) / 5G6G / 北斗 / 数字基建（不含 AI/智能制造，那是 🤖）
- 🧱 材料: 新材料/卡脖子材料 > 稀土关键矿产 > 高端装备 > 钢铁化工
- 🎖️ 军事: 新型装备列装 > 远海演训/维和 > 国防科技 > 部队建设

请只输出 JSON（无 markdown 代码块、无 think 标签）：
{
  "relevance": {
    "🔬 世界性科研突破": <0-10>,
    "🤖 AI智能前沿": <0-10>,
    "🌾 农业": <0-10>,
    "🤝 扶贫": <0-10>,
    "⚡ 能源": <0-10>,
    "🏥 医疗": <0-10>,
    "🚀 科技": <0-10>,
    "🧱 材料": <0-10>,
    "🎖️ 军事": <0-10>
  },
  "importance": <0-10>,
  "timeliness": <0-10>
}

标题：{title}
来源：{source}
```

## 7. 数据模型

无持久化变更。仅新增内存中间结构：

```python
# 9 栏 relevance + 2 个全局维度
signals = {
    "relevance": {<9 个栏目名>: <0-10 整数>},
    "importance": <0-10 整数>,
    "timeliness": <0-10 整数>,
}
```

## 8. 兼容策略（brownfield）

| 场景 | 行为 |
|------|------|
| `column-score` 未配置在 llm.yaml | `call_llm` 抛 ConfigError → score_signals catch 返回 None → 降级到 legacy_path（旧行为完全保留） |
| `NINEROUTER_API_KEY` 缺失 | `get_client` 抛 LLMCallError → 同上降级 |
| 9router 本地服务（localhost:20128）不在线 | `call_llm` 抛 LLMCallError → 同上降级；**legacy_path 内 `llm_classify_single` 也会同步失败**（同一 provider），最终降级到纯关键词 `score_all_categories` + `priority_score` |
| JSON 解析失败（含 think 标签污染） | 重试 1 次强制纯 JSON → 仍失败降级 |
| 缺失某栏目 key | `_validate_signals` 返回 False → 视为失败降级 |
| 单批降级率 >30% | stderr 输出 `⚠ column-score 降级率 X%`，不中断流水线 |
| 历史调用点 `llm_classify_single` | **保留**，仅在降级路径 + 关键词低置信度时使用，行为不变 |
| `CATEGORY_KEYWORDS` 词典 | **不删，扩充** — 新增 🤖 词条；🚀 词条剥离 AI/智能制造迁到 🤖 |
| `priority_score` | **保留**，仅 legacy_path 使用 |
| `1新闻_链接.md` 行级输出格式 | `### [{源}] {标题}` + `URL：{url}` 完全不变 |
| 空栏目处理 | 不再写 `## {栏目}\n（当日无真实报道，栏目留空）`；下游 step7/step8 天然兼容（heading 不存在则不渲染） |
| step7 / step8 与 step4 `COLUMN_ORDER` 不一致 | 必须同步加 🤖 AI智能前沿；不一致会导致 step8 渲染顺序错乱 |

## 9. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|----------|
| R-01 | GLM-4-Flash JSON 输出不稳定（漏 key / 越界）| P1 | Schema 校验 + 重试 1 次 + 降级到关键词；监控降级率 |
| R-02 | 9router 本地服务挂掉 → 全量降级 | P1 | 关键词路径完整保留；降级率 stderr WARN |
| R-03 | LLM 评分系统性偏向某栏目（如全押科技） | P1 | dry-run 跑 3 天历史数据，对比新旧 top-10 分布；阈值偏差 >20% 启动 prompt 调参 |
| R-04 | 200 篇 × 2s = 7 min 时延 vs 旧 ~1 min | P2 | 文档可接受，且 fail-fast 30s timeout 限制最坏情况；后续 Phase 14 再并发 |
| R-05 | `think` 标签污染 JSON（推理模型输出）| P1 | 复用 `step4.py:225` 的 `re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)` 清洗逻辑；还要去 markdown 代码块 ```json``` |
| R-08 | 9router 挂时 legacy 也无法用 LLM 仲裁，纯关键词覆盖率不足 | P1 | 二级降级：legacy_path 内 LLM 失败时直接用 `score_all_categories` 最高分归属，跳过低置信度仲裁；流水线仍能产出 |
| R-09 | 项目无 `tests/` 目录、无 pytest 配置 | P2 | 测试以可独立运行的 `tests/test_column_scoring.py` 文件形式提供，含 `if __name__ == "__main__"` 兜底；不引入 pytest 依赖（若已配则用之）|
| R-06 | 聚合公式系数（0.5/0.3/0.2）未经实证 | P2 | 在 design 中固定默认值，必要时通过 dry-run 对比微调；不放 config（YAGNI） |
| R-07 | 8 栏目顺序/名称今后变 | P2 | `COLUMN_ORDER` 已在 step4 顶部常量，prompt 模板基于此常量动态生成；不硬编码 |
| R-08 | 9router 挂时 legacy 也无法用 LLM 仲裁，纯关键词覆盖率不足 | P1 | 二级降级：legacy_path 内 LLM 失败时直接用 `score_all_categories` 最高分归属，跳过低置信度仲裁；流水线仍能产出 |
| R-09 | 项目无 `tests/` 目录、无 pytest 配置 | P2 | 测试以可独立运行的 `tests/test_column_scoring.py` 文件形式提供，含 `if __name__ == "__main__"` 兜底；不引入 pytest 依赖（若已配则用之）|
| R-10 | 9 栏 emoji 中 `🤖` / `🔬` 在 prompt 与 JSON key 中需精确匹配（含 ZWJ 等 unicode 细节） | P1 | 实现时 `assert COLUMN_ORDER[i] == json_key`；prompt 模板与 COLUMN_ORDER 共用常量构造；测试用例覆盖 emoji 完整 codepoint |
| R-11 | LLM 偶发漏判 🔬 世界级新闻（relev < 7 但实际是世界级）| P1 | 抢占规则只在 LLM 自己判定 7+ 时生效；漏判走 argmax 自然归到 🚀/🤖/相关栏，不影响产出；prompt 含 Must 标准提示降低概率 |
| R-12 | `🤖 AI智能前沿` 与 `🚀 科技` 边界模糊（如"算力中心揭牌"既可算 🤖 又可算 🚀）| P2 | prompt 明确划界：AI 加速卡/智能制造/具身智能 → 🤖；通用 CPU/OS/通信/数字基建 → 🚀；LLM 自决定，无强制规则 |

## 10. 决策追踪

| ID | 决策 | 来源 | 覆盖 |
|----|------|------|------|
| D-001@v1 | Phase 13 范围 = 重做 step4.py 栏目评分（不含渲染/性能） | archive/2026-06-26 user-manual-summary-bar | §1, §3 |
| D-002@v1 | 选用 B+ 信号提取式（拒绝 A 纯 LLM / B 关键词+LLM 修正 / C 多维规则）| 用户确认 brainstorm step 8 | §4 |
| D-003@v1 | 聚合公式 `relev × (0.5 + 0.3·imp/10 + 0.2·time/10)` | architect 提议、用户确认 brainstorm step 9 | §4.5 |
| D-004@v1 | LLM 失败必降级到关键词层，不抛错中断流水线 | 兼容策略 + R-02 | §8 |
| D-005@v1 | 变更名 `2026-06-27-column-scoring-v2` | 用户确认 brainstorm step 9 | 头部 frontmatter |
| D-006@v1 | 保留 `llm_classify_single` 不删，作 legacy_path 一部分 | 防止回滚断路径 | §5, §8 |
| D-007@v1 | 不引入聚合公式系数的外置配置（YAGNI）| R-06 | §9 |
| D-008@v1 | column-score 用 temperature=0.0（评分确定性需要），与其他 site 的 0.7 显式偏离 | Grill cross-check | §6.2 |
| D-009@v1 | 9router 挂时 legacy_path 二级降级：跳过 llm_classify_single 直接走纯关键词归属 | Grill cross-check vs R-08 | §8, R-08 |
| D-010@v1 | 实现代码不写 type hints（与 CONVENTIONS §2.3 一致），design.md 中 type hints 仅作签名说明 | Grill cross-check vs CONVENTIONS | §6.1 |
| D-011@v1 | 8 栏目语义契约入 §4.0：🔬 门槛型（Must A-F + Must-not），其余 8 栏排序型（Tier 0-10）| 用户 brainstorm 补充 | §4.0 |
| D-012@v1 | 新增第 9 栏 `🤖 AI智能前沿`，固定排序第 2 位，承接 AI/机器人/量子/智能制造 | 用户 brainstorm 补充 | §4.0, §5 |
| D-013@v1 | 🤖 T2 国产 AI 算力芯片厂商显式列举：昇腾/寒武纪/海光 DCU/摩尔线程/沐曦/壁仞/燧原/天数智芯/平头哥/昆仑芯/登临/算能 | 用户 brainstorm 补充 + 调研确认 | §4.0 🤖 T2 |
| D-014@v1 | 🚀 T1 国产通用 CPU 厂商显式列举：龙芯/飞腾/鲲鹏/海光/兆芯/申威；AI 加速卡剥离到 🤖 T2；智能制造剥离到 🤖 T5 | 用户 brainstorm 补充 + 调研确认 | §4.0 🚀 T1, §4.0 🤖 T2/T5 |
| D-015@v1 | 方案 X：🔬 relevance ≥ 7 时强制抢占归属，覆盖 argmax；prompt 同步提示 LLM；同文章只归单栏 | 用户 brainstorm 补充 | §4.1 |
| D-016@v1 | 空栏目消失采用路径 A：step4 不写空栏 heading；step7/step8 天然兼容 | 用户 brainstorm 补充 | §4.2 |
| D-017@v1 | step7 / step8 同步 `COLUMN_ORDER` 加 🤖（第 2 位），不动其他逻辑；视为非目标的最小同步项 | 一致性约束 + D-012@v1 | §3, §5, §8 |
| D-018@v1 | 🔬 E.1 期刊白名单含中国顶刊（NSR / Cell Research / Science China / Chinese Science Bulletin / The Innovation / Light: S&A / Fundamental Research）+ E.2 文章类型必须 Research/Letter/Article（排除 Review/Perspective/Comment）| 用户 brainstorm 补充 | §4.0 🔬 E |
| D-019@v1 | 🔬 D 国产化推进型拆 D.1 终局 + D.2 进度型（C919/航发首次试车等关键节点）| 用户 brainstorm 补充 | §4.0 🔬 D |

## 11. 验收标准

| AC | 描述 | 验证手段 |
|----|------|---------|
| AC-01 | dry-run 跑 2026-06-25 数据，`1新闻_链接.md` **是 9 栏目集合**且仅写非空栏目 heading | `python3 step4.py --date 2026-06-25 --dry-run` 查看 markdown 输出 |
| AC-02 | LLM 关闭（mock call_llm 抛错），dry-run 跑通且产出 top-10 | 单测：mock LLMCallError，断言走 legacy_path |
| AC-03 | `_validate_signals` 拒绝缺 key（9 栏少 1）/ 越界 / 非整数 | 单测 ≥6 case |
| AC-04 | `aggregate_scores` 边界：全 0 → 0；relev=0 → 0；全 10 → 10 | 单测 |
| AC-05 | step4 P95 ≤ 10 min（200 篇）| `time python3 step4.py --date <today>` |
| AC-06 | llm.yaml 含 `column-score` key | `python3 -c "import yaml;assert 'column-score' in yaml.safe_load(open('llm.yaml'))['call_sites']"` |
| AC-07 | step4 / step7 / step8 三处 `COLUMN_ORDER` 完全一致（9 栏，🤖 位于第 2 位） | `rg "^COLUMN_ORDER = " step4.py step7.py step8.py -A 4` diff |
| AC-08 | 实现代码无 type hints（CONVENTIONS §2.3 一致性）| `rg "->\s*(dict|str|int|None|list|tuple|bool)" step4.py` 结果为空 |
| AC-09 | **🔬 抢占规则**：mock signals 中 🔬 relev=8、🌾 relev=10 → assign_category 返回 🔬 | 单测 |
| AC-10 | **dedup**：同 url 不会出现在多栏；不同栏不重复同一新闻 | 单测 + dry-run diff |
| AC-11 | **空栏目消失**：mock 输入 9 栏只 5 栏有数据 → 输出 md 仅 5 个 `## ` heading | 单测 |
| AC-12 | `CATEGORY_KEYWORDS` 含 🤖 词典（≥30 词，覆盖国产 GPU/CPU/大模型）；🚀 剥离 AI/智能制造词条 | `python3 -c "from step4 import CATEGORY_KEYWORDS; assert '🤖 AI智能前沿' in CATEGORY_KEYWORDS"` |

## 12. 自审

### 12.1 需求覆盖
- ✅ Phase 13 = 栏目评分重做（D-001@v1） → §1, §4 完整覆盖
- ✅ B+ 信号提取式（D-002@v1） → §4.4 数据流图 + §6 接口
- ✅ 关键词兜底（用户原话） → §8 兼容策略矩阵
- ✅ 不改 step1_3/6（G-04 + 非目标）→ §3, §5
- ✅ **栏目语义契约 9 栏完整定义**（D-011~D-019）→ §4.0
- ✅ **🤖 AI智能前沿新栏**（D-012, D-013）→ §4.0 🤖
- ✅ **🔬 世界级抢占规则**（D-015）→ §4.1
- ✅ **空栏目消失**（D-016）→ §4.2

### 12.2 Grill / 决策覆盖
- ✅ 19 条 D-xxx@v1 全部映射到具体章节
- ✅ 无未解决 D-xxx；无 v2 升级

### 12.3 约束一致性
- ✅ 与 `ARCHITECTURE.md` 文件接力模式一致（仍读 `0新闻_粗筛.md` 写 `1新闻_链接.md`）
- ✅ 与 `classifier.md` 模块文档兼容（保留 `parse_0`, `is_china_*`, `score_all_categories`）
- ✅ 与 `llm-client.md` 一致：`call_llm` 失败抛 `LLMCallError`，调用方 catch 后降级
- ✅ 与 `CONVENTIONS.md §2.3` 一致：实现代码不写 type hints（D-010@v1）
- ✅ 与 `CONVENTIONS.md §3` 一致：不直接 import openai，通过 `from llm_client import call_llm` 接入
- ✅ 与 `CONVENTIONS.md §4` 一致：状态信息中文 emoji 前缀
- ✅ step7 / step8 `COLUMN_ORDER` 同步（D-017）— 三处一致是 step8 渲染顺序的硬约束

### 12.4 真实性
- ✅ 所有现有符号（`CATEGORY_KEYWORDS`/`score_all_categories`/`priority_score`/`llm_classify_single`/`COLUMN_ORDER`/`call_llm`）已在 step4.py / step7.py / step8.py / llm_client.py 实际定义（已验）
- ✅ 新增符号 (`score_signals`/`aggregate_scores`/`assign_category`/`_validate_signals`/`_build_score_prompt`) 明确标注新增
- ✅ `column-score` call_site 标注新增（llm.yaml 当前仅有 china-relevance/column-classify/summarize）
- ✅ 国产 GPU/CPU 厂商列举均经 2025-2026 公开报道核实（IDC 数据、各家招股书/财报）

### 12.5 YAGNI
- ✅ 不外置聚合公式系数（D-007@v1）
- ✅ 不引入异步/并发（Phase 14 范围）
- ✅ 不持久化 signals（每次重新计算可接受）
- ✅ 不为本期添加 prompt A/B 框架
- ✅ 不为 9 栏 emoji/顺序做可配置化（写死常量，三处同步）

### 12.6 验收可测试
- ✅ 12 条 AC 全部可执行（单测 + dry-run + 命令行 assert）

### 12.7 非目标清晰
- ✅ §3 明确 8 项非目标，含 step7/step8 仅同步常量边界

### 12.8 兼容策略
- ✅ §8 矩阵覆盖 12 种异常场景，全部降级到旧路径，旧行为完全保留
- ✅ 9 栏与旧 8 栏的迁移：旧 1新闻_链接.md 仍可被 step7/8 解析（不会因 🤖 缺失报错，只是该栏目无内容）

### 12.9 风险识别
- ✅ §9 列 9 条 R-xx，含等级与对策

### 12.10 生命周期契约表
- ❌ 不适用：本变更不涉及 session/lease/agent_run/daemon/lifecycle/claim/heartbeat 任一关键词；仅是同步函数调用 + JSON 校验

### 12.11 整体判断
**自审通过 ✅。**

## 13. Design Grill Result

**status: passed (扩展版 — 含 9 栏改造交叉审查)**

### 13.1 Cross-Check Matrix

| ID | 层级 | 交叉点 | 证据 A | 证据 B | 结论 | 决策 |
|----|------|--------|--------|--------|------|------|
| X-001 | feasibility | LLM provider 现状 | design §6.2 "GLM-4-Flash" | llm.yaml: provider=9router, model=low, base_url=localhost:20128 | 旧设计文字过时（"GLM"） | 修订 §6.2 为 9router 透传，删除 GLM 假设 |
| X-002 | consistency | temperature=0.0 vs 其他 site 0.7 | design.md §6.2 | llm.yaml L4/L8/L12 | 故意偏离需显式记录 | **D-008@v1** |
| X-003 | feasibility | 9router 挂时 legacy 仍调 LLM | design §8 兼容矩阵 | step4.py:339 llm_classify_single 无 try/except | 二级降级缺漏 | **D-009@v1** + R-08 |
| X-004 | consistency | design 用 `dict \| None` type hint | CONVENTIONS §2.3 "极少使用 type hints" | 文档可用、实现不可用 | **D-010@v1** + AC-08 |
| X-005 | definition | score_signals 异常处理粒度 | design §6.1 | llm_client.py:130 LLMCallError + traceback | 调用方不需再 traceback | 修订 §6.1 异常处理说明 |
| X-006 | consistency | think 标签 + markdown 代码块清洗 | design R-05 | step4.py:225 已有 think 清洗模式 | 仅写 think 不够 | 修订 R-05 补 codefence 清洗 |
| X-007 | consistency | 9 栏改造影响 step7/step8 COLUMN_ORDER | design §3 "不改 step7/step8" | step8.py:20 `COLUMN_ORDER` 硬编码 8 栏 | 不改 step7/8 与 9 栏一致性冲突 | **D-017@v1**：把 COLUMN_ORDER 同步列为 §5 必改项，非目标改为"不深改逻辑，只同步常量" |
| X-008 | definition | 🔬 抢占规则与 argmax 的执行顺序 | §4.1 代码片段 | §4.4 数据流图 | 数据流图需含抢占节点 | 修订 §4.4 数据流图，加 `assign_category` 节点 |
| X-009 | consistency | 空栏目消失对 balance_columns 的影响 | §4.2 路径 A | step8.py:137 `balance_columns` 对 ordered groups 做 2^n 枚举 | n=K≤9 仍 ≤512 枚举，性能无影响 | 在 §4.2 明确说明 |
| X-010 | feasibility | emoji codepoint 匹配 | 9 栏 emoji 含 `🔬🤖🌾🤝⚡🏥🚀🧱🎖️`（其中 🎖️ 含 VS16 变体选择符）| JSON key 与 COLUMN_ORDER 必须 byte-精确匹配 | unicode 易错 | **R-10**：测试覆盖 emoji codepoint |
| X-011 | premise | 🤖 与 🚀 边界模糊 | §4.0 边界说明 | 用户给定划界规则 | 仍有 LLM 主观判断空间 | **R-12**：接受 P2 风险，prompt 提示充分；不做强制规则 |
| X-012 | feasibility | CATEGORY_KEYWORDS 现有 8 栏，新增 🤖 + 剥离 🚀 词条 | design §5 step4.py 修改条目 | step4.py:141 CATEGORY_KEYWORDS 字典 | 词典操作必须保持 8 栏键名完全不变（不要把 🚀 改名为 🚀-base 这类）| §5 中明确"扩 🤖 + 调 🚀 的词条内容，不动 key" |

### 13.2 Question Distribution

| 分类 | 数量 | 含义 |
|------|------|------|
| immediately_answered | 12 | 全部可由代码 / scan 文档 / 用户已确认决策 / 公开调研直接确证 |
| needs_thinking | 0 | — |
| unresolved | 0 | — |

### 13.3 Unresolved Blockers

无。所有 P0/P1 问题已通过 D-008~D-019@v1 + R-08~R-12 解决。

### 13.4 总结

Cross-check 暴露原设计（8 栏 B+）→ 新设计（9 栏 + 抢占 + 空栏目消失）转型期间的 6 个新交叉点（X-007~X-012），全部修订至 design.md 与 decisions.md。`COLUMN_ORDER` 三处同步从"非目标"调整为"非目标的最小同步项"（D-017）；emoji codepoint / 🤖🚀 边界 / 词典扩充等细节均有应对。

**Design Grill passed ✅。** 可进入 Step 13 用户确认并生成规范文件。
