# Phase 8: 摘要与过滤健壮性 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 08-summary-robustness
**Areas discussed:** 摘要长度控制, API截断诊断, 涉华过滤, 负面新闻过滤, 扶贫定义缩宥, 无效摘要回退

---

## 摘要长度控制

| Option | Description | Selected |
|--------|-------------|----------|
| 硬截断60字 | 摘要超过60字时截断到最后一句话 | |
| 调 prompt + max_tokens | 把 prompt 从"2-3句"改为"1-2句"，max_tokens 从300降到100 | |
| 两者都做 | 调 prompt 控制源头 + 硬截断兜底 | |

**User's choice:** 不截断，通过 prompt 引导 LLM 精简、准确、完整地概括
**Notes:** 用户明确反对硬截断和 max_tokens 限制，希望 LLM 自然地输出精简摘要

---

## API截断诊断

| Option | Description | Selected |
|--------|-------------|----------|
| 正文过长导致截断 | 1511字超过API处理能力 | |
| API偶发异常 | MiniMax M2.7 上下文204,800 tokens，1511字不可能溢出 | ✓ |

**User's choice:** 需要调查API真实能力
**Notes:** 用户质疑"1511字溢出"的结论，经查证 MiniMax M2.7 上下文窗口 204,800 tokens，1511字(~2000 tokens)远不会溢出。"由于霍"是偶发API异常

---

## 涉华过滤

| Option | Description | Selected |
|--------|-------------|----------|
| 关键词过滤 | 加涉华关键词列表，纯外国新闻直接过滤 | |
| 关键词+LLM双重 | 关键词初筛 + LLM二次确认边角案例 | ✓ |
| 不过滤，改摘要角度 | 不加密关过滤，但在摘要prompt里要求关注涉华角度 | |

**User's choice:** 关键词+LLM双重
**Notes:** 10条新闻中6条纯外国（日本研究、美国研究、欧洲油价、俄乌战争、伊朗美国、航行警告），比例很高。涉华关键词需排除源名噪点（"新华社"含"华"但不是涉华证据）

---

## 负面新闻过滤

| Option | Description | Selected |
|--------|-------------|----------|
| 加负面关键词过滤 | 在EXCLUDE中加入审查调查/违纪违法等关键词 | ✓ |
| 只过滤审查调查类 | 只过滤"违纪/审查"类，不过滤其他负面 | |

**User's choice:** 加负面关键词过滤
**Notes:** "王晓东接受审查调查"被误分到农业（因标题含"农业和农村委员会"）

---

## 扶贫定义缩宥

| Option | Description | Selected |
|--------|-------------|----------|
| 缩宥扶贫关键词 | 去掉"乡村振兴"泛匹配，只保留扶贫/脱贫关键词 | ✓ |
| 乡村振兴单分 | 把"乡村振兴"移到其他栏目 | |
| 改栏目名 | 扶贫改为"乡村振兴与扶贫" | |

**User's choice:** 缩宥扶贫关键词
**Notes:** "乡村振兴"不等于"扶贫"，当前关键词列表导致"玫瑰经济助力乡村振兴"被分到扶贫

---

## 无效摘要回退

已确认 MiniMax M2.7 上下文204,800 tokens，"由于霍"是偶发API异常。通过质量验证检测 + 规则回退处理。

## the agent's Discretion

- 涉华关键词的完整列表和调优
- LLM 涉华判断的 prompt 设计
- 扶贫关键词缩宥后的具体列表
- 摘要 prompt 的具体措辞
- 无效摘要的检测规则

## Deferred Ideas

None — discussion stayed within phase scope
