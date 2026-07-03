---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
status: brainstorm-ready
---

# Design · Phase 15E · LLM batching

## 背景

Daily 是 Python 3.12 文件接力新闻流水线，`run_all.sh` 串行执行 `step1_3.py -> step4.py -> step6.py -> step7.py -> step8.py`。Phase 15E 聚焦两个 LLM 密集点：`step4.py` 的涉华判定与栏目评分，以及 `step7.py` 的摘要生成。

当前真实代码中，`step4.py` 在 `build_classification_result()` 内对 `china_llm` 候选逐条调用 `llm_is_china_related()`，随后对每条通过涉华过滤的文章逐条调用 `score_signals()`。`score_signals()` 失败后才退到关键词和 `llm_classify_single()`，因此单日候选较多时 LLM 调用次数随文章数线性增长，最坏可达数十到数百次。

`step7.py` 当前已包含 `ThreadPoolExecutor(max_workers=3)`、`STEP7_MAX_WORKERS = 3`、`summarize_article_worker()`，满足摘要并发的主体方案。本 phase 对 `step7.py` 只做契约化检查和必要补强，不重复引入第二套 async 方案。

## 设计目标

- G-01：把 `step4.py` 单日 LLM 调用次数降到 `<=30`，以 2026-06-30 样本为基准。
- G-02：保持 `1新闻_链接.md` 输出格式不变，下游 `step6.py`、归档补全、`archive_enrich.py` 不需要适配。
- G-03：保持分类语义接近 15A baseline，输出差异 `<=5%` 或人工确认差异合理。
- G-04：批量 LLM JSON 解析失败、缺项、校验失败时回退到现有单条逻辑，不让批处理失败中断流水线。
- G-05：确认 `step7.py` 摘要并发保持输出顺序与 `1新闻_链接.md` 一致，且失败仍走 `fallback_summarize()`。
- G-06：不新增用户运行步骤，继续支持 `python3 step4.py --date YYYY-MM-DD [--dry-run]` 和 `python3 step7.py --date YYYY-MM-DD [--dry-run]`。

## 非目标

- NG-01：不改 `COLUMN_ORDER`、栏目名称、栏目数量和输出 Markdown 结构。
- NG-02：不改 `step1_3.py` 采集逻辑。
- NG-03：不改 `step6.py` 正文提取逻辑。
- NG-04：不改 `step8.py` 渲染逻辑。
- NG-05：不迁移到异步 HTTP/async LLM SDK，不引入 Playwright/Selenium 等新依赖。
- NG-06：不改变 `llm.yaml` 配置结构，除非执行中发现批量 call site 必须独立配置；默认复用现有 `china-relevance`、`column-score`、`column-classify`。

## 拆分判断

Phase 15E 是 Phase 15 系列中的 LLM 调用优化层，依赖 15A 已完成的 `llm_client.py` 统一抽象。它不与 15B/15C/15F/15G 合并，原因如下：

- 与 15B 正文抽取无直接接口耦合；15E 只消费 `0新闻_粗筛.md`、输出 `1新闻_链接.md`，不触碰 `2新闻_已审核.md` 正文结构。
- 与 15C 异步采集不同；15E 的并发/批处理对象是 LLM 请求，不是新闻源网络抓取。
- 与 15F 图片质量不同；15E 不修改归档图片和首图逻辑。
- 与 15G 工程化不同；15E 可以用少量 helper 和手工验证完成，不需要大规模包结构调整。

## 总体方案

### Wave 1：建立调用计数与基线

新增手工验证脚本 `tests/manual/test_15e_llm_call_count.py`，用 monkeypatch 或包装方式统计 `step4.py` 内 `llm_is_china_related()`、`score_signals()`、`llm_classify_single()` 的调用次数，并对 2026-06-30 或可用样本日期输出 JSON/文本报告。

该脚本不要求真实请求 LLM；优先使用替身返回稳定结果，目标是比较改造前后调用路径数量和输出条数。若样本输入不存在，脚本应清晰报错并提示需要先准备 `/mnt/e/每日新中国/YYYY-MM-DD/0新闻_粗筛.md`。

### Wave 2：step4 高置信度关键词直通

在 `build_classification_result()` 的分类循环中，先计算 `kw_scores = score_all_categories(title)`。满足以下条件时直接分栏并跳过 `score_signals()`：

- `best_score >= 6`
- `best_score - second_score >= 3`

直通结果写入现有 article 字段：

- `a['signals'] = None`
- `a['score_source'] = 'keyword-high-confidence'`
- `a['category'] = best_cat`
- `a['priority'] = priority_score(title, best_cat) + kw_scores.get(best_cat, 0)`

低置信度文章继续走 LLM 批量评分或单条 fallback。

### Wave 3：step4 批量涉华判断

新增 `llm_is_china_related_batch(articles)`，输入 `china_llm` 候选列表，按 `BATCH_SIZE = 20` 分批调用 LLM。prompt 使用稳定 index，而不是 title 作为 JSON key，避免标题重复或标点导致解析困难。

输出 schema：

```json
[
  {"index": 0, "is_china_related": true},
  {"index": 1, "is_china_related": false}
]
```

解析策略：

- 去除 `<think>...</think>` 和 ```json fences。
- `json.loads()` 后必须是 list。
- 每项必须包含整数 `index` 和布尔 `is_china_related`。
- index 必须落在当前 batch 范围内。
- batch 缺项、重复、类型错误、JSON 解析失败时，该 batch 整体 fallback 到现有 `llm_is_china_related(title)` 单条函数。

`build_classification_result()` 中替换逐条循环：

```python
llm_confirmed = llm_is_china_related_batch(china_llm)
```

### Wave 4：step4 批量栏目评分

新增 `score_signals_batch(articles)`，输入已通过涉华过滤但未命中高置信度直通的文章，按 `BATCH_SIZE = 20` 分批调用现有 `column-score` call site。prompt 要求模型返回 list，每项包含 `index` 和现有 `_validate_signals()` 可验证的 signals 字段。

输出 schema：

```json
[
  {
    "index": 0,
    "relevance": {"🔬 世界性科研突破": 0, "🤖 AI智能前沿": 0},
    "importance": 0,
    "timeliness": 0
  }
]
```

实现时必须确保 `relevance` 覆盖全部 `COLUMN_ORDER` 栏目；文档示例允许省略展示，代码 prompt 必须列出完整栏目。解析后复用 `_validate_signals(signals)`。

fallback 策略：

- batch JSON 失败或任一条缺少有效 signals：该 batch 缺失/无效条目逐条调用 `score_signals(title, source)`。
- 单条 `score_signals()` 仍失败：继续走现有关键词 fallback 与 `llm_classify_single([a])` 仲裁。
- 为控制调用次数，`llm_classify_single()` 暂不做批量改造；只作为低频兜底保留。

### Wave 5：step7 并发契约确认

`step7.py` 已实现 `ThreadPoolExecutor(max_workers=STEP7_MAX_WORKERS)` 和按 index 写回结果。计划阶段只安排验证和小修：

- 保持 `STEP7_MAX_WORKERS = 3`。
- 保持 `summarize_article_worker(index, article)` 返回 `(index, summary, fallback)`。
- 保持 `results[idx]` 后按 `enumerate(matched)` 回填，确保输出顺序不随 future 完成顺序变化。
- 若验证发现异常传播导致整个 step 失败，可在 worker/future 收集处补单条异常 fallback，但不改变摘要 API。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `step4.py` | 增加批量涉华判断、批量栏目评分、高置信度关键词直通、解析 helper 和 fallback 统计 |
| 修改 | `step7.py` | 仅在验证发现缺口时补强并发异常处理；保留现有 ThreadPoolExecutor 方案 |
| 修改 | `design.md` | 同步文件变更清单与实际产出 |
| 修改 | `.sillyspec/changes/2026-07-05-phase-15e-llm-batching/plan.md` | 更新 task checkbox 进度标记 |
| 修改 | `llm_client.py` | 默认不修改；如执行中需要批量调用通用包装，仅新增兼容 `call_llm()` 的薄 helper |
| 新增 | `.sillyspec/changes/2026-07-05-phase-15e-llm-batching/verify-result.md` | Phase 15E 验收检查报告 |
| 新增 | `tests/manual/test_15e_llm_call_count.py` | 手工统计 step4 LLM 调用次数和输出差异，用于验证 `<=30` 目标 |

## 接口定义

### `step4.py` 新增常量

```python
LLM_BATCH_SIZE = 20
HIGH_CONFIDENCE_MIN_SCORE = 6
HIGH_CONFIDENCE_MARGIN = 3
```

### `step4.py` 新增 helper

```python
def _strip_llm_json(raw):
    """去除 think 块和 markdown fence，返回可 json.loads 的字符串。"""

def _chunks(items, size):
    """按固定大小切分 list。"""

def high_confidence_keyword_category(title):
    """返回 (category, kw_scores)；不满足高置信度时 category 为 None。"""

def llm_is_china_related_batch(articles):
    """批量涉华判断；返回通过涉华判断的 article 列表，失败时按 batch 回退单条 llm_is_china_related。"""

def score_signals_batch(articles):
    """批量栏目评分；返回 {title: signals_or_none}，失败/缺失条目回退单条 score_signals。"""
```

### `step7.py` 既有接口保持

```python
STEP7_MAX_WORKERS = 3

def summarize_article_worker(index, article):
    """返回 (index, summary, fallback)。"""
```

## 数据模型

无数据库、表结构或持久化 schema 变更。`0新闻_粗筛.md`、`1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md` 文件格式保持不变。

运行时新增的 `score_source` 值只存在于内存 article dict 和调试输出中，不写入最终 Markdown 契约。

## 兼容策略

- 未配置新功能开关：不需要配置开关；批处理失败自动回退到已有单条函数。
- API key 缺失：沿用 `llm_client.call_llm()` 抛错路径；batch helper 捕获异常后逐条 fallback，单条函数按现状返回 `False` 或 `None`。
- JSON 不稳定：batch 级解析失败不影响整个流程，只影响该 batch 降级为旧逻辑。
- 输出兼容：`1新闻_链接.md` 和 `3新闻_概述.md` 不增加字段、不改标题层级。
- 下游兼容：`step6.py`、`step8.py`、`news_archive.py`、`archive_enrich.py` 不需要改动。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 批处理 LLM 返回非 JSON 或部分缺项 | P1 | `_strip_llm_json()` + schema 校验；失败 batch 回退单条函数 |
| R-02 | 批量评分与单条评分结果存在小幅差异 | P1 | 手工脚本对比 2026-06-30 输出；差异 `<=5%` 或人工确认 |
| R-03 | 高置信度阈值误伤边界标题 | P2 | 阈值设为 6/3，仅跳过明显领先标题；低置信度仍走 LLM |
| R-04 | 批量 prompt 太长导致模型截断 | P2 | `LLM_BATCH_SIZE = 20`，执行中如失败率高可降到 10 |
| R-05 | `step7.py` 并发异常传播中断整步 | P2 | 验证 `future.result()` 行为；必要时补 worker 异常 fallback |
| R-06 | `--help` 或误建 change 污染 SillySpec 状态 | P2 | 不手动 mv/rm change；后续用 SillySpec CLI/doctor 处理 |

## 决策追踪

当前无独立 `decisions.md`。本设计内的关键决策如下：

| 决策 | 覆盖需求 | 理由 |
|---|---|---|
| 使用高置信度阈值 6/3 跳过栏目评分 LLM | FR-01 | 只跳过强关键词且领先明显的标题，降低误分风险 |
| 批处理 JSON 使用 `index` 而不是标题作 key | FR-02, FR-03, FR-04 | 标题可能重复、含标点或被模型改写；index 更稳定 |
| batch 失败按 batch/条目回退旧单条函数 | FR-04 | 最大化兼容，避免批处理失败变成流水线失败 |
| 保留 `step7.py` ThreadPoolExecutor 方案 | FR-05 | 真实代码已实现且符合需求，不引入第二套并发模型 |

## 自审

- 需求覆盖：通过。FR-01 对应 Wave 2，FR-02 对应 Wave 3，FR-03/FR-04 对应 Wave 4，FR-05 对应 Wave 5。
- 约束一致性：通过。保留文件接力、根目录 step 脚本、手写 CLI 参数、中文进度输出，不新增运行步骤。
- 真实性：通过。`build_classification_result()`、`llm_is_china_related()`、`score_signals()`、`llm_classify_single()`、`STEP7_MAX_WORKERS`、`summarize_article_worker()` 均来自当前代码。
- YAGNI：通过。不引入 async SDK、不重构包结构、不改栏目定义。
- 验收标准：通过。调用次数、输出差异、fallback 和顺序保持均可通过手工脚本与指定日期运行验证。
- 非目标清晰：通过。明确不触碰采集、正文抽取、渲染、Markdown 输出结构。
- 兼容策略：通过。批处理失败回退旧逻辑，下游文件契约不变。
- 生命周期契约表：不适用。本变更不涉及 session、lease、agent_run、daemon、heartbeat 等生命周期状态机。
