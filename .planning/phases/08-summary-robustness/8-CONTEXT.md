# Phase 8: 摘要与过滤健壮性 - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 step4.py（分类筛选）和 step7.py（摘要生成）的质量问题。具体包括：涉华过滤不足（6/10条纯外国新闻）、负面新闻过滤（反腐败新闻混入栏目）、扶贫栏目定义过宽（"乡村振兴"泛匹配）、摘要过长（58-131字，应1-2句约60字）、API偶发返回无效摘要（"由于霍"3字）。

不包含：CSS样式修改、左右栏平衡、新信源接入、正文提取相关改动。

</domain>

<decisions>
## Implementation Decisions

### 涉华过滤 (step4.py)
- **D-01:** 关键词+LLM双重过滤。先在 step4.py 的 classify() 前加一步涉华关键词初筛（中国/我国/国产/中华/中方/在华/访华/驻华/对华/涉华 + 省名 + 中央/纪委/监委/十四届/全国政协等），过滤时去掉源名噪点（新华社/参考消息/央视）。关键词无法判断的边角案例，用 LLM 二次确认是否与中国相关。纯外国新闻直接过滤，不进入栏目分类。

### 负面新闻过滤 (step4.py)
- **D-02:** 在 EXCLUDE_TITLES 或新增 EXCLUDE_KEYWORDS 中加入负面关键词黑名单：审查调查/违纪违法/纪律审查/监察调查/落马/双开/接受审查/涉嫌严重。包含这些关键词的新闻直接过滤，不进入栏目分类。

### 扶贫栏目缩宥 (step4.py)
- **D-03:** 扶贫栏目的关键词列表缩宥，去掉"乡村振兴"泛匹配。只保留明确的扶贫/脱贫关键词：扶贫/脱贫/对口帮扶/消费扶贫/驻村书记/精准扶贫/易地搬迁。"乡村振兴"类新闻应归入其他栏目或作为独立类别。

### 摘要长度控制 (step7.py)
- **D-04:** 通过 prompt 引导 LLM 自然精简输出，不设 max_tokens 硬上限。prompt 改为要求"用1-2句话精炼概括核心要点，简短、准确、完整"，强调精简而非字数。不做硬截断，保持 LLM 输出的自然语感。

### API无效摘要回退 (step7.py)
- **D-05:** 摘要结果质量验证：API返回后检测是否有效（长度>20字、不含正文原文片段、不含"由于"等截断特征词）。无效时走 fallback_summarize() 规则回退。MiniMax M2.7 上下文窗口 204,800 tokens，1511字正文不会溢出——"由于霍"是偶发API异常，不是上下文问题。

### the agent's Discretion
- 涉华关键词的完整列表和调优
- LLM 涉华判断的 prompt 设计和调用方式
- 扶贫关键词缩宥后的具体列表
- 摘要 prompt 的具体措辞
- 无效摘要的具体检测阈值和模式列表
- fallback_summarize() 是否需要同步调整

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要修改的代码
- `step4.py` — 栏目分类筛选脚本，classify()、is_quality_news()、EXCLUDE_TITLES
- `step7.py` — 摘要生成脚本，llm_summarize()、fallback_summarize()、prompt 模板

### 上游决策
- `.planning/milestones/v1.1-REQUIREMENTS.md` — v1.1 需求追踪表（SUM-01~03）
- `.planning/phases/07-column-balance/7-CONTEXT.md` — Phase 7 权重简化决策

### 参考数据
- `/mnt/e/每日新中国/2026-05-17/3新闻_概述.md` — 当前输出（含"由于霍"和长摘要样本）
- `/mnt/e/每日新中国/2026-05-17/2新闻_已审核.md` — step7 输入数据
- `/mnt/e/每日新中国/2026-05-17/0新闻_粗筛.md` — step4 输入数据

### API 文档
- MiniMax M2.7: 上下文窗口 204,800 tokens, base_url `https://api.minimaxi.com/v1`, OpenAI SDK 兼容

</canonical_refs>

<code_context>
## Existing Code Insights

### 被修改的代码
- `step4.py:19-26` — EXCLUDE_TITLES 质量过滤黑名单，需扩展负面关键词
- `step4.py:63-68` — is_quality_news() 函数，需增加涉华检测和负面过滤
- `step4.py:71-98` — classify() 函数，扶贫关键词列表需缩宥
- `step7.py:119-157` — llm_summarize() 函数，prompt 和结果验证需修改
- `step7.py:101-116` — fallback_summarize() 函数，可能需调整

### Established Patterns
- CLI参数：所有step脚本统一 `--date YYYY-MM-DD` + `--dry-run`
- 数据路径：`/mnt/e/每日新中国/{date}/`
- API调用：OpenAI SDK 兼容，base_url `https://api.minimax.chat/v1`
- 逐条调用：step7.py 对每条新闻独立调用 API

### Integration Points
- step4 输入：`0新闻_粗筛.md`（step1_3 产出）
- step4 输出：`1新闻_链接.md`（step6 的输入）
- step7 输入：`2新闻_已审核.md`（step6 产出）
- step7 输出：`3新闻_概述.md`（step8 的输入）

</code_context>

<specifics>
## Specific Ideas

- 涉华关键词过滤时需排除源名噪点（"新华社"含"华"字但不是涉华证据）
- "由于霍"是 API 偶发异常，不是上下文溢出。204,800 tokens 上下文足够处理 1511 字正文
- 当前 10 条新闻中 6 条纯外国，说明信源采集阶段没有涉华偏好——过滤只能在 step4 做
- "王晓东接受审查调查"被分到农业是因为标题含"农业和农村委员会副主任"，是 classify() 关键词匹配的误伤
- 用户明确要求摘要不截断、通过 prompt 引导 LLM 自然精简

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-summary-robustness*
*Context gathered: 2026-05-17*
