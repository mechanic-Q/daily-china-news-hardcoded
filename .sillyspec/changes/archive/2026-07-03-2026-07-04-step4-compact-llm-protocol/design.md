---
author: lmr
created_at: 2026-07-04 00:23:08
---

# Step4 Compact LLM Protocol Design

## 背景

Step4 目前通过 `llm_client.call_llm()` 调用 9router `model: low` 完成两类任务：涉华 batch 判断和栏目评分。近期运行 `step4.py --date 2026-07-03` 时出现 `ValueError: empty LLM response`，并且归档中当日记录全部退化为 `score_source=keyword-fallback`、`signals=null`。实测发现 `low` 模型会把复杂结构化任务的 token 消耗在 `reasoning_content`，导致 `message.content` 为空或截断。

当前 JSON 评分输出每篇文章重复 9 个 emoji 栏目 key，batch 越大输出越长，进一步放大截断风险。用户确认采用紧凑协议作为主路径：涉华用位串，栏目评分用矩阵；同时保持现有评分算法和上下游数据结构不变。

## 设计目标

1. 修复 `china-relevance` 和 `column-score` 在 `low` 模型下的空响应/截断问题。
2. 将 step4 主 LLM 输出协议从冗长 JSON 改为紧凑、严格可解析协议。
3. 保持现有业务算法不变：`aggregate_scores()`、`assign_category()`、`priority_score()` 不改。
4. 保持归档/月报结构不变：仍产出 `signals.relevance`、`signals.importance`、`signals.timeliness`、`category`、`priority`、`selected_in_top10`。
5. 失败时保留可诊断信息，不再让空 content 被下游解析器误判。

## 非目标

1. 不重写 Step4 栏目选择算法。
2. 不调整 `COLUMN_ORDER` 或栏目含义。
3. 不修改 `news_archive.py`、`monthly_report.py` 的数据结构。
4. 不重新设计 step1/step6/step7/step8 流水线。
5. 不把 JSON 作为主路径继续堆高 token；JSON 仅可作为 fallback/debug。

## 拆分判断

无需拆分。本次是单一调用链的协议稳定性修复，涉及 `step4.py`、`llm_client.py`、`llm.yaml` 和测试文件，但目标一致：让 Step4 LLM I/O 稳定输出并还原旧 `signals` 结构。不存在多角色、多页面或多个可独立交付功能。

## 总体方案

采用方案 A：紧凑协议主路径。

Wave 1：协议 parser 与调用保障

定义并测试两个 parser。涉华 parser 接收位串，去除空白后必须只包含 `0/1`，长度必须等于 batch size。评分 parser 接收矩阵行，每行格式为 `index|r1,r2,r3,r4,r5,r6,r7,r8,r9|importance|timeliness`，按 `COLUMN_ORDER` 还原成现有 `signals` dict。`llm_client.call_llm()` 对空 content fail-fast，并记录 `finish_reason`、`content_len`、`reasoning_len`。

Wave 2：Step4 主路径切换

`llm_is_china_related_batch()` prompt 改为要求输出位串。`score_signals_batch()` prompt 改为要求输出矩阵。两个 batch 函数先走紧凑协议，解析失败时保留现有 fallback 路径：涉华回退单条判断，栏目评分回退 `score_signals()` 或关键词 fallback。`score_signals()` 可同步使用单条矩阵协议，保证单条 fallback 也不依赖冗长 JSON。

Wave 3：配置与验收

对 `low` 模型调用传入 `reasoning_effort="none"`，并在程序内将输出上限设为 `max_tokens=262144`。1m context 是 `model: low` 的模型能力选择，不是 OpenAI Chat Completions 的独立参数；程序侧能明确控制的是输出上限。新增单元测试覆盖 parser、空 content 诊断、batch mock 端到端。使用 `python3 step4.py --date 2026-07-03 --dry-run` 验证不写文件时无 `empty LLM response`，且实际分类路径能产出非空 `signals`。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `step4.py` | 新增紧凑协议 parser；涉华 batch 使用位串；栏目评分使用矩阵；保留 fallback |
| 修改 | `llm_client.py` | 空 content fail-fast；记录 finish_reason/content_len/reasoning_len；支持透传 `reasoning_effort` |
| 修改 | `llm.yaml` | 为 `low`/紧凑协议调整 `max_tokens=262144` 与 timeout，避免继续使用过低输出上限 |
| 修改 | `tests/test_step4.py` | 增加位串 parser、矩阵 parser、batch mock 还原测试 |
| 修改 | `tests/test_llm_client.py` | 增加空 content 诊断/异常测试 |

## 接口定义

新增或调整的内部函数为 `step4.py` 私有协议层，不暴露新外部 API。

```python
def _parse_china_bitstring(raw: str, expected_count: int) -> list[bool]:
    """Parse compact china-relevance output into booleans."""

def _parse_score_matrix(raw: str, expected_count: int) -> list[dict]:
    """Parse compact column-score output into existing signals dicts."""

def _compact_llm_overrides(max_tokens: int | None = None) -> dict:
    """Return per-call overrides such as reasoning_effort='none'."""
```

评分矩阵协议：

```text
index|r1,r2,r3,r4,r5,r6,r7,r8,r9|importance|timeliness
```

其中 `r1..r9` 严格按 `COLUMN_ORDER` 解释。parser 输出保持旧结构：

```python
{
    "relevance": {COLUMN_ORDER[0]: r1, ..., COLUMN_ORDER[8]: r9},
    "importance": importance,
    "timeliness": timeliness,
}
```

涉华位串协议：

```text
101001
```

第 N 位对应输入 batch 第 N 条，`1=True`，`0=False`。

## 数据模型

无持久化数据模型变更。归档仍由 `news_archive.build_record()` 写入原字段：`column`、`category`、`aggregate_score`、`priority`、`selected_in_top10`、`score_source`、`signals`。月报仍按现有字段读取。

## 兼容策略

1. 新协议只影响 Step4 与 LLM 的输入输出文本，不改变 Step4 对内数据结构。
2. parser 失败时保留现有 fallback：涉华回退单条判断，栏目评分回退单条评分或关键词 fallback。
3. JSON 可作为 debug/fallback 留存，但不是主路径；如果 fallback 使用 JSON，也必须还原为同样 `signals` dict。
4. 旧归档记录无需迁移；重新跑 Step4 后新记录会带非空 `signals`。
5. `news_archive.py` 和 `monthly_report.py` 不需要感知紧凑协议。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 模型输出矩阵格式不严格，导致解析失败 | P1 | parser 严格校验并触发 fallback；prompt 明确禁止表头和解释 |
| R-02 | 矩阵协议可读性低，人工排查不如 JSON | P2 | debug 日志保留原 raw 片段；文档固定协议格式 |
| R-03 | 低模型仍可能忽略 `reasoning_effort=none` | P1 | call_llm 空 content fail-fast 并记录 reasoning_len；fallback 继续工作 |
| R-04 | 主协议改变后精选结果与旧 JSON 评分略有差异 | P1 | 不改算法；验证 mock 与真实 dry-run；必要时用高 token JSON 对照抽查 |
| R-05 | 输出上限配置过小导致矩阵被截断 | P1 | 紧凑协议仍配置足够 max_tokens；parser 检查行数和完整性 |

## 决策追踪

| 决策 | 覆盖位置 |
|---|---|
| D-001@v1 紧凑协议为主路径 | 总体方案、接口定义、兼容策略 |
| D-002@v1 不改算法/上下游结构 | 非目标、数据模型、兼容策略 |
| D-003@v1 parser 还原旧 signals | 设计目标、接口定义、文件变更清单 |
| D-004@v1 low 模型调用预算 | 总体方案、文件变更清单、风险登记 |

## 自审

| 检查项 | 结果 |
|---|---|
| 覆盖用户确认需求 | 通过：紧凑协议主路径、low 禁 reasoning、安全边界均覆盖 |
| 决策覆盖 | 通过：D-001/D-002/D-003/D-004 均在 design 中引用 |
| 约束一致性 | 通过：遵守 local.yaml 测试命令和 Daily 文件流水线 |
| 真实性 | 通过：文件和函数来自当前代码；新增函数已标注新增 |
| YAGNI | 通过：不新增外部服务、不改归档/月报、不新增长期配置系统 |
| 验收标准 | 通过：单测、mock E2E、2026-07-03 dry-run 均可执行 |
| 非目标清晰 | 通过 |
| 兼容策略 | 通过：fallback 与旧结构保持 |
| 生命周期契约表 | 不适用：不涉及 session/lease/daemon/lifecycle |
