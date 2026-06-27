---
author: lmr
created_at: 2026-06-27 15:40:30
schema_version: 1
doc_type: decisions
change_id: 2026-06-27-column-scoring-v2
phase: 13
---

# Decisions · 2026-06-27-column-scoring-v2

每条决策含稳定 ID。后续若修订请使用 `D-xxx@v2` 并写 `supersedes: D-xxx@v1`。

## D-001@v1: Phase 13 范围 = 重做 step4.py 栏目评分
- type: boundary
- status: accepted
- priority: P0
- source: docs
- question: Phase 13 应该改什么？
- answer: 重做 step4.py 栏目评分链；不含渲染（Phase 07）、不含性能量化（Phase 12）、不含性能优化（Phase 14）
- normalized_requirement: 改 `step4.py` 评分相关函数与 `llm.yaml`；step1_3/6/7/8 与上下游 md 契约不动
- impacts: [G-01, G-02, FR via §1, §3, §5]
- evidence: `.sillyspec/changes/archive/2026-06-26-2026-06-27-user-manual-summary-bar/requirements.md:45-47`、`.../design.md:26`

## D-002@v1: 评分机制 = B+ 信号提取式
- type: architecture
- status: accepted
- priority: P0
- source: user
- question: 用 A 纯 LLM / B 关键词+LLM 修正 / C 多维规则 / B+ 信号提取式 哪个？
- answer: B+（LLM 单次 JSON 输出 `relevance{8 栏目} + importance + timeliness`，离线公式聚合，关键词兜底）
- normalized_requirement: 每篇 1 次 `call_llm("column-score")`；结构化 JSON 输出；LLM 失败必降级到关键词层
- impacts: [G-01, G-02, G-03, §4, §6, §8]
- evidence: brainstorm step 8 用户回答 "B+可以"；基于 2025 PASTEL/MAPEGY 业界做法

## D-003@v1: 聚合公式
- type: architecture
- status: accepted
- priority: P1
- source: user
- question: 多维信号如何聚合成单个分？
- answer: `aggregate(cat) = relevance[cat] × (0.5 + 0.3·importance/10 + 0.2·timeliness/10)`
- normalized_requirement: relevance 主导（≥50% 权重不可压），importance 最多 +30%，timeliness 最多 +20%；全 10 → 10，relevance=0 → 0
- impacts: [§4.3, AC-04]
- evidence: brainstorm step 9 用户回答 "同意"

## D-004@v1: LLM 失败必降级
- type: compatibility
- status: accepted
- priority: P0
- source: user
- question: LLM 调用失败时怎么办？
- answer: 必须自动降级到 legacy_path（关键词高置信度 + 现有 `llm_classify_single` 仲裁 + `priority_score`），不抛错不中断流水线
- normalized_requirement: 9 种异常场景全部走降级；单批降级率 >30% 仅 stderr WARN
- impacts: [G-03, §8, R-02, AC-02]
- evidence: brainstorm step 9 设计中明确，用户确认

## D-005@v1: 变更名
- type: term
- status: accepted
- priority: P2
- source: user
- question: 变更目录命名？
- answer: `2026-06-27-column-scoring-v2`
- normalized_requirement: changeDir = `.sillyspec/changes/default`（运行时别名 default 指向上述命名）；档案归档时改名遵循 sillyspec change-rename
- impacts: [frontmatter, AC]
- evidence: brainstorm step 9 用户回答 "同意"

## D-006@v1: 保留 llm_classify_single 不删
- type: compatibility
- status: accepted
- priority: P1
- source: code
- question: 旧的低置信度仲裁 `llm_classify_single` 删不删？
- answer: 不删，作为 legacy_path（降级路径）的一部分；call_site `column-classify` 在 llm.yaml 中保留
- normalized_requirement: legacy_path 完整保留：score_all_categories + 高置信度阈值（≥4 且差 ≥2）+ llm_classify_single + priority_score
- impacts: [§5, §8, R-02]
- evidence: §8 兼容矩阵；防回滚断链

## D-007@v1: 聚合系数不外置
- type: premise
- status: accepted
- priority: P2
- source: code
- question: 聚合公式的 0.5/0.3/0.2 要不要放 yaml 让用户调？
- answer: 不外置（YAGNI）。固定在代码常量 `AGG_RELEV_BASE=0.5`、`AGG_IMP_W=0.3`、`AGG_TIME_W=0.2`
- normalized_requirement: 不引入新 config 表面；后续需要调时再升 D-007@v2
- impacts: [R-06, §9]
- evidence: 决策时点用户未提出可配置需求；调研中无证据显示系数需常变

## D-008@v1: column-score 用 temperature=0.0
- type: consistency
- status: accepted
- priority: P1
- source: design-grill
- question: column-score 的 temperature 与 llm.yaml 现有 3 个 site 的 0.7 不一致，是不是写错了？
- answer: 故意偏离。评分需要确定性（同标题输入应得相近评分），其他 site 是文本生成场景容忍随机性
- normalized_requirement: llm.yaml `call_sites.column-score.temperature = 0.0`，注释说明原因
- impacts: [§6.2, llm.yaml]
- evidence: 现有 llm.yaml 4-12 行温度均 0.7

## D-009@v1: 9router 挂时二级降级
- type: compatibility
- status: accepted
- priority: P1
- source: design-grill
- question: 9router (localhost:20128) 挂掉时 legacy_path 也无 LLM 仲裁，纯关键词覆盖率够吗？
- answer: 二级降级 — legacy_path 内 `llm_classify_single` 失败时跳过它，直接用 `score_all_categories` 最高分归属。流水线必能产出，质量降级
- normalized_requirement: legacy_path 实现需 catch llm_classify_single 异常；最终兜底 = max(score_all_categories)；若仍无分（关键词全不命中）→ 跳过该篇文章
- impacts: [§8, R-08]
- evidence: 当前 step4.py:339 调 llm_classify_single 无 try/except，本期需补

## D-010@v1: 实现代码不写 type hints
- type: consistency
- status: accepted
- priority: P2
- source: design-grill
- question: design.md 在接口定义里用 `dict | None` type hint，是否违反 CONVENTIONS §2.3 "极少使用 type hints"？
- answer: design.md 中 type hint 仅作接口约定文档，实现代码不写。与项目其余 Python 代码保持风格一致
- normalized_requirement: step4.py 实现：函数签名不带注解、不 import typing 模块；docstring 描述输入输出类型
- impacts: [§6.1, AC-08（新增）]
- evidence: `.sillyspec/docs/Daily/scan/CONVENTIONS.md §2.3`

## D-011@v1: 栏目语义契约写入 §4.0
- type: architecture
- status: accepted
- priority: P0
- source: user
- question: LLM 评分仅靠"对 8 栏目打 0-10"是否够？每个栏目的内在价值观/判定标准未定义，会失控
- answer: 必须先把 8（→9）栏目语义契约（intent + Must/Must-not + Tier + 正反例 + 边界）落到 design §4.0，prompt 模板基于此构造
- normalized_requirement: design.md §4.0 含 9 栏完整语义契约；step4.py prompt 字符串引用其简化版作为 LLM 指引
- impacts: [§4.0, §6.3 prompt, AC-09~AC-12]
- evidence: brainstorm 用户原话："我们必须理解这个标题、这个板块内在的价值观和价值感是什么，然后才能将其作为标准去给新闻做筛选和评分"

## D-012@v1: 新增第 9 栏 🤖 AI智能前沿
- type: architecture
- status: accepted
- priority: P0
- source: user
- question: AI / 机器人 / 量子计算 / 智能制造该归哪个栏目？
- answer: 新增独立栏目 🤖 AI智能前沿，固定排序第 2 位（仅次于 🔬），承接所有智能前沿主题
- normalized_requirement: COLUMN_ORDER = [🔬, 🤖, 🌾, 🤝, ⚡, 🏥, 🚀, 🧱, 🎖️]；step4/step7/step8 三处同步
- impacts: [§4.0 🤖, §5, AC-07, AC-12, D-017@v1]
- evidence: brainstorm 用户原话"我还要增加一个新板块……AI、机器人、量子计算机应用这三个主题一起拉出来"+"实际内涵还是智能前沿"

## D-013@v1: 🤖 T2 国产 AI 算力芯片厂商列举
- type: term
- status: accepted
- priority: P1
- source: user + research
- question: 国产 AI 芯片 / GPU 应该覆盖哪些厂商作为关键词？
- answer: 显式列举：华为昇腾、寒武纪、海光 DCU、摩尔线程、沐曦、壁仞、燧原、天数智芯、平头哥、昆仑芯、登临、算能
- normalized_requirement: §4.0 🤖 T2 描述 + step4.py CATEGORY_KEYWORDS '🤖 AI智能前沿' 字典含上述厂商名词条
- impacts: [§4.0 🤖, §5 step4.py, AC-12]
- evidence: brainstorm 用户原话"国产芯、国产显卡的芯片，比如华为昇腾、摩尔线程这些……支撑算力中心、支撑国产大模型……支撑未来具身智能群集化"+ tavily 调研 2025-2026 IDC / 招股书数据

## D-014@v1: 🚀 重新切分 + 国产通用 CPU 厂商列举
- type: term
- status: accepted
- priority: P1
- source: user + research
- question: 🚀 科技栏的 AI/智能制造已切到 🤖，那 🚀 还剩什么？国产 CPU 厂商有哪些？
- answer: 🚀 T1 国产通用 CPU 列举：龙芯、飞腾、鲲鹏、海光、兆芯、申威；国产 OS：鸿蒙、欧拉、统信 UOS、麒麟；T2-T6 收缩为 5G/6G/北斗/数字基建/科技园区/应用落地
- normalized_requirement: §4.0 🚀 描述 + step4.py CATEGORY_KEYWORDS '🚀 科技' 词典剥离 AI/智能制造词条；明确边界：AI 加速卡 → 🤖 T2，通用 CPU → 🚀 T1
- impacts: [§4.0 🚀, §4.0 🤖, §5 step4.py]
- evidence: brainstorm 用户原话"科技里的智能制造这部分，也可以算到 AI 的智能前沿那一块儿"+ tavily 调研六大国产 CPU

## D-015@v1: 方案 X 世界级抢占规则
- type: architecture
- status: accepted
- priority: P0
- source: user
- question: 🔬 世界级新闻可能被 argmax 分到其他栏，如何强制归 🔬？且如何避免同新闻多栏重复？
- answer: 代码后处理：🔬 relevance ≥ 7 时强制返回 🔬，覆盖 argmax；assign_category 返回单值，单文章只进单栏；现有 used_urls 集合天然实现 URL 级 dedup
- normalized_requirement: step4.py assign_category 实现见 §4.1；prompt 中加 "🔬 达世界级 Must 标准时打 7-10" 提示；阈值常量 WORLD_CLASS_THRESHOLD = 7
- impacts: [§4.1, §6.1 assign_category, §6.3 prompt, AC-09, AC-10]
- evidence: brainstorm 用户原话"世界级优先。这个可以再用方案X来实现……出现在世界级突破里，其他板块里就不要再重复出现那个新闻"

## D-016@v1: 空栏目消失采用路径 A
- type: architecture
- status: accepted
- priority: P1
- source: user
- question: 当日某栏无内容时如何处理？路径 A（step4 不写 heading）还是路径 B（step8 过滤）？
- answer: 路径 A — step4.py 写 1新闻_链接.md 时只为有 items 的栏目写 `## {栏目}` heading；step7/step8 天然兼容
- normalized_requirement: step4.py run() 末尾循环跳过 col_selected 为空的栏目；不再写"（当日无真实报道，栏目留空）"占位
- impacts: [§4.2, §5 step4.py, AC-11]
- evidence: brainstorm 用户回答 "Q2路径A可以"

## D-017@v1: step7/step8 同步 COLUMN_ORDER
- type: consistency
- status: accepted
- priority: P0
- source: design-grill (X-007)
- question: D-012 新增第 9 栏，但 §3 非目标说"不改 step7/step8"。如何处理？
- answer: 三处常量必须同步（step4 / step7 / step8 的 COLUMN_ORDER）；step7/step8 仅同步常量、不改逻辑，视为非目标的最小同步项
- normalized_requirement: 三处 COLUMN_ORDER 加 🤖 AI智能前沿 于第 2 位；其余字段、函数、模板不动
- impacts: [§3 修订, §5, AC-07]
- evidence: step8.py:20 `COLUMN_ORDER` 硬编码 8 栏；不同步将导致渲染顺序与 step4 输出对不上

## D-018@v1: 🔬 E 期刊白名单 + 文章类型双层判定
- type: term
- status: accepted
- priority: P1
- source: user
- question: 顶刊论文怎么判？只要发 Nature 就算？还是要看文章类型？
- answer: 三维判定 — E.1 期刊白名单（国际顶刊 + 子刊 + 中国顶刊 NSR/Cell Research/Science China 等）× E.2 文章类型必须是 Research/Letter/Article/Report 等原创（拒 Review/Perspective/Comment/News & Views）× E.3 标题强信号词组合
- normalized_requirement: design §4.0 🔬 E 完整定义；prompt 模板提示 LLM 注意"研究类 vs 综述类"区分
- impacts: [§4.0 🔬 E]
- evidence: brainstorm 用户原话"你在 Nature 评论区发的文章和在 Nature 论文区发的文章，那肯定不是一个含金量"+"中科院的、中国的顶刊也算"

## D-019@v1: 🔬 D 国产化推进型拆 D.1 / D.2
- type: boundary
- status: accepted
- priority: P1
- source: user
- question: 商业产品核心依赖进口（如 C919 发动机）就完全打死吗？国产化逐步替代算不算突破？
- answer: D 拆为 D.1 终局型（核心已国产量产，即使代差落后）+ D.2 替代型（关键部件首次国产替代 / 国产化率提升 / 长期被卡部件研发关键节点突破 / 替代方案完成实验验证）
- normalized_requirement: design §4.0 🔬 D 完整定义；判别词清单覆盖国产化推进语义
- impacts: [§4.0 🔬 D]
- evidence: brainstorm 用户原话"国产大飞机 C919……发动机我们也有落地方案，还在实验过程中……一步步的替代，一步步的国产化，我觉得也是一种突破"
