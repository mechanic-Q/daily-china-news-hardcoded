# Phase 9: 智能分类 — Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

用 C+D 混合方案重写 step4.py 的分类逻辑：关键词加权评分 + LLM 批量裁决。替换当前线性优先级硬匹配，确保歧义词（如"火箭"）不被错误归类，"世界性科研突破"和"军事"等易混淆栏目有区分度。

只改 step4.py，其他文件不动。保持平面脚本结构。

</domain>

<decisions>
## Implementation Decisions

### 关键词加权评分
- **D-01:** 用 `CATEGORY_KEYWORDS` 词典替换 8 个独立关键词列表。每条新闻对所有 8 栏目计算加权得分
- **D-02:** 权重基于直觉设定，先上线再调优（dry-run 时人工确认分类结果）
- **D-03:** `火箭` 从"世界性科研突破"中移除（与"火箭炮"混淆导致军事新闻误归科研），`火箭炮` 只在"军事"（权重 4）
- **D-04:** `发现` 从"世界性科研突破"中移除（太泛），改为 `考古发现`（权重 4）
- **D-05:** 科研突破关键词权重普遍较高（3-5），军事关键词差异化（火箭炮/导弹/航母=4，训练/官兵=2）

### 高置信度直接归类
- **D-06:** 最高分 ≥ 3 且领先第二名 ≥ 2 视为高置信度，直接归入，不调 LLM
- **D-07:** 不达阈值（低置信度/平局/全 0）→ 送 LLM 批量裁决

### LLM 批量裁决
- **D-08:** 低置信度标题按 5 条一批发送给 MiniMax M2.7，逐条指定最贴切栏目
- **D-09:** LLM 返回格式："序号|栏目名"，解析失败时降级回退
- **D-10:** LLM 失败时：有部分关键词得分的取最高分栏目，全 0 的丢弃

### 优先级差异化
- **D-11:** `priority_score()` 改为接收 title + category 两个参数
- **D-12:** "世界性科研突破"标准更高——必须有"首次/突破/发现/全球"等信号才加分，否则基础分减 2

### the agent's Discretion
- `CATEGORY_KEYWORDS` 的具体权重值（不超过 5，不低于 1）
- LLM 分类 prompt 的具体措辞
- 输出中是否显示"关键词高置信度 / LLM 裁决 x条"的统计信息

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要修改的代码
- `step4.py` — 栏目分类筛选脚本，需重写 classify()、priority_score() 和 run() 中调用逻辑

### 上游决策
- `.planning/phases/08-summary-robustness/8-CONTEXT.md` — Phase 8 涉华过滤/负面过滤/扶贫缩宥等决策（这些在 Phase 9 中保持不变）
- `.planning/phases/08-summary-robustness/8-UAT.md` — Phase 8 UAT 测试项，验证智能分类不破坏已有功能

### 参考数据
- `/mnt/e/每日新中国/2026-05-17/0新闻_粗筛.md` — 测试数据（197条），用于 dry-run 验证分类效果
- `/mnt/e/Daily/step4.py` — 当前版本（被重写的目标文件）

### API 文档
- MiniMax M2.7: 上下文窗口 204,800 tokens, base_url `https://api.minimax.chat/v1`, OpenAI SDK 兼容

</canonical_refs>

<code_context>
## Existing Code Insights

### 被修改的代码
- `step4.py:143-170` — classify() 函数，8段硬编码 if/elif，将被 `score_all_categories()` 替代
- `step4.py:173-181` — priority_score() 函数，将被改为接收 category 参数
- `step4.py:243-247` — run() 中分类循环，需改为先评分→分离高低置信度→LLM裁决→合并

### 无需改动的部分
- `is_quality_news()` — 保持不变
- `is_china_related()` / `is_china_source()` / `llm_is_china_related()` — 保持不变
- `detect_source()` — 保持不变
- 精选逻辑（每栏目1条+补选到10条）— 保持不变（D-13）
- 输出格式 — 保持不变

### Established Patterns
- CLI 参数：`--date YYYY-MM-DD` + `--dry-run`
- 数据路径：`/mnt/e/每日新中国/{date}/`
- API 调用：OpenAI SDK，base_url `https://api.minimax.chat/v1`
- 涉华过滤：关键词→来源白名单→LLM三层过滤（保持在智能分类之前）

</code_context>

<specifics>
## Specific Ideas

- 低置信度/平局案例举例："新能源无人机在农业领域的创新应用" → 科技=4、农业=3，领先=1，送 LLM
- 高置信度案例举例："箭啸喀喇昆仑——新疆军区某团火箭炮分队训练影像" → 军事=9、其他=0，直接归类

</specifics>

<deferred>
## Deferred Ideas

- 关键词权重用历史数据系统性验证优化 — 后续迭代
- 精选逻辑增加"每栏目限制条数" — 当前已够用，后续需要再加
- 8栏目的增减或合并 — 超出本 phase 范围

</deferred>

---

*Phase: 09-smart-classify*
*Context gathered: 2026-05-18*
