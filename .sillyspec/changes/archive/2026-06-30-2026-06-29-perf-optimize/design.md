---
author: lmr
created_at: 2026-06-30 01:24:39
change: 2026-06-29-perf-optimize
stage: brainstorm
doc_type: design
---

# Phase15 性能优化设计

## 1. 背景

Daily 是 5 步 Python 新闻流水线：`step1_3.py → step4.py → step6.py → step7.py → step8.py`，各步骤通过 `/mnt/e/每日新中国/YYYY-MM-DD/` 下的 Markdown 文件接力。

Phase 12 `perf_profile.py` 已量化瓶颈：

- `step1_3.py` 约 88s：7 信源串行 + chromium 多次 cold-start。
- `step6.py` 约 73s：多篇正文串行提取。
- `step7.py` 约 102s：多篇 LLM 摘要串行，并含重试等待。
- `step4.py` 约 41s。
- `step8.py` 约 7s。

用户确认 Phase15 本期采用低风险高收益范围：只优化 `step6.py` 和 `step7.py` 的文章级串行处理，不动采集端和渲染端。

## 2. 设计目标

1. `step6.py` 正文提取由逐篇串行改为受限线程池并发。
2. `step7.py` 摘要生成由逐篇串行改为受限线程池并发。
3. 保持全部输入输出文件名、Markdown 格式、栏目顺序、CLI 参数和 `run_all.sh` 编排不变。
4. 保持失败语义：单篇正文失败写入错误占位；单篇摘要失败走 `fallback_summarize()`；不因单篇失败阻断整批。
5. 使用 `perf_profile.py` 做前后对比，验证 `step6 + step7` 总耗时下降。

## 3. 非目标

- 不优化 `step1_3.py` 信源抓取。
- 不做 chromium 进程复用。
- 不修改 `step4.py` 栏目算法或 LLM 分类逻辑。
- 不修改 `step8.py` HTML/PNG 渲染语义。
- 不修改 `run_all.sh` CLI、退出语义或 step 顺序。
- 不引入 `asyncio` 重构、Playwright、Selenium 或新第三方依赖。
- 不改变 `1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md` 的文件契约。

## 4. 拆分判断

本变更不需要拆分为多个 SillySpec change：

- `step6.py` 和 `step7.py` 都是文章级独立处理，优化模式一致。
- 影响面集中在 extractor 与 summarizer 两个模块。
- 两个模块通过磁盘文件接力解耦，可分任务、分 Wave 实现和验证。
- 不涉及数据库、状态机、跨服务接口或 UI 改造。

不走批量模式：本期不是多日期、多信源或多模板批处理，而是对两个固定脚本的并发模型调整。

## 5. 总体方案

### 5.1 Wave 1：step6 正文提取并发

`step6.py` 当前在 `run(today, dry_run)` 中解析 `1新闻_链接.md` 得到 `articles`，然后逐条调用 `fetch_and_extract(url, title)`。本期保留 `fetch_and_extract()`、`needs_chromium()`、`extract_body()` 等同步接口，只在 `run()` 内部把每篇文章提交给 `ThreadPoolExecutor`。

并发结果必须按原 `articles` 列表顺序回填，避免输出顺序随完成时间漂移。每个 worker 返回 `{index, body, err}` 或等价结构；主线程按 index 写回 `a['body']`，继续复用现有成功计数和 Markdown 生成逻辑。

建议新增常量：

```python
STEP6_MAX_WORKERS = 4
```

默认 4 线程原因：正文抓取主要是网络 I/O 和外部 chromium I/O；4 线程能降低串行等待，又避免对源站和本机 chromium 造成过高压力。

### 5.2 Wave 2：step7 摘要生成并发

`step7.py` 当前先通过 `parse_1news()` 和 `parse_2news()` 生成 `matched`，然后逐条调用 `llm_summarize(title, body)`，失败时调用 `fallback_summarize(title, body)`。本期保留匹配逻辑、摘要校验逻辑、fallback 逻辑和输出 Markdown 结构，只把每篇摘要任务提交给 `ThreadPoolExecutor`。

worker 执行单篇摘要流程：

1. 调用 `llm_summarize(title, body)`。
2. 若返回空值，调用 `fallback_summarize(title, body)`。
3. 返回 `{index, summary, fallback}` 或等价结构。
4. 主线程按 index 回填 `matched[index]['summary']` 和 `matched[index]['fallback']`。

建议新增常量：

```python
STEP7_MAX_WORKERS = 3
```

默认 3 线程原因：LLM 调用受 API 限流、网络波动和重试等待影响，过高并发会放大 429/超时风险。3 线程足够消除大部分串行等待，同时保守控制请求压力。

原先成功摘要之间的 `time.sleep(0.5)` 在并发模式下不再按全局顺序 sleep。重试内部的 `time.sleep(1/2)` 保留在 `llm_summarize()` 内部，作为单篇任务内部退避。

### 5.3 Wave 3：验证与性能对比

验证重点不是只看语法，而是证明文件契约和失败语义未漂移：

- `python3 -m py_compile step6.py step7.py`
- `python3 step6.py --date YYYY-MM-DD --dry-run`
- `python3 step7.py --date YYYY-MM-DD --dry-run`
- `python3 perf_profile.py --date YYYY-MM-DD --dry-run`

如果真实 LLM 或网络不可用，dry-run 仍应保留原有错误展示与 fallback 行为；性能对比可标注外部网络波动。

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `step6.py` | 在 `run()` 中加入受限线程池并发正文提取；新增并发常量和单篇 worker helper |
| 修改 | `step7.py` | 在 `run()` 中加入受限线程池并发摘要生成；新增并发常量和单篇 worker helper |
| 新增 | `.sillyspec/changes/2026-06-29-perf-optimize/prototype-perf-optimize.html` | 并发流程原型图 |
| 新增 | `.sillyspec/changes/2026-06-29-perf-optimize/design.md` | 本设计文档 |
| 新增 | `.sillyspec/changes/2026-06-29-perf-optimize/decisions.md` | 决策台账 |

## 7. 接口定义

### 7.1 `step6.py`

保留现有公开函数：

```python
def fetch_and_extract(url, title):
    ...

def run(today, dry_run):
    ...
```

新增实现辅助函数：

```python
STEP6_MAX_WORKERS = 4

def extract_article_worker(index, article):
    body, err = fetch_and_extract(article['url'], article['title'])
    return index, body, err
```

设计约束：

- `article` 继续使用现有 dict 字段：`src`、`title`、`url`、`body`。
- worker 不写文件，只返回结果。
- 文件写入仍只在 `run()` 主流程内发生。

### 7.2 `step7.py`

保留现有公开函数：

```python
def parse_1news(path, today_str):
    ...

def parse_2news(path, today_str):
    ...

def llm_summarize(title, body):
    ...

def fallback_summarize(title, body):
    ...

def run(today, dry_run):
    ...
```

新增实现辅助函数：

```python
STEP7_MAX_WORKERS = 3

def summarize_article_worker(index, article):
    summary = llm_summarize(article['title'], article['body'])
    fallback = False
    if not summary:
        summary = fallback_summarize(article['title'], article['body'])
        fallback = True
    return index, summary, fallback
```

设计约束：

- `matched` 字段继续使用：`title`、`category`、`src`、`body`、`summary`、`fallback`。
- worker 不改栏目顺序，不写文件。
- 主线程按 `COLUMN_ORDER` 生成 `3新闻_概述.md`，保持原格式。

## 8. 数据模型

无数据库、表结构或持久化 schema 变更。

Markdown 文件契约保持不变：

| 文件 | 生产者 | 消费者 | 契约 |
|---|---|---|---|
| `1新闻_链接.md` | `step4.py` | `step6.py`, `step7.py` | 标题、栏目、URL 格式不变 |
| `2新闻_已审核.md` | `step6.py` | `step7.py` | `## 【来源】标题` + `正文：...` 格式不变 |
| `3新闻_概述.md` | `step7.py` | `step8.py` | 栏目标题与摘要段落格式不变 |

## 9. 兼容策略

- CLI 兼容：`python3 step6.py --date YYYY-MM-DD [--dry-run]` 和 `python3 step7.py --date YYYY-MM-DD [--dry-run]` 不变。
- 编排兼容：`run_all.sh` 不变，仍串行执行 step。
- 文件兼容：输入输出文件名和 Markdown 格式不变。
- 失败兼容：正文失败仍写 `[正文提取失败: ...]`；摘要失败仍走规则 fallback。
- 回退路径：如并发引发问题，可把 `run()` 内并发段替回原串行循环，其他接口无需变化。

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | step7 LLM 并发触发 API 限流或超时 | P1 | 默认 `STEP7_MAX_WORKERS = 3`；保留单篇重试和 fallback；验收关注 fallback 比例 |
| R-02 | step6 多线程同时调用 chromium 导致本机资源抖动 | P1 | 默认 `STEP6_MAX_WORKERS = 4`；不做 chromium 复用；必要时降低常量 |
| R-03 | 并发完成顺序不同导致输出顺序漂移 | P0 | worker 返回 index；主线程按原列表顺序回填和输出 |
| R-04 | 多线程 print 输出交错影响可读性 | P2 | worker 尽量不打印进度；主线程统一打印每篇结果 |
| R-05 | 网络波动导致 perf_profile 对比不稳定 | P2 | 用同日期、相近时间窗口对比；报告注明外部网络和 LLM 波动 |

## 11. 决策追踪

| 决策 | 状态 | 覆盖章节 | 说明 |
|---|---|---|---|
| D-001@v1 | accepted | §2, §3, §5 | Phase15 范围只做 step6 + step7 并发 |
| D-002@v1 | accepted | §5, §7 | 实现方案选 ThreadPoolExecutor 保守并发 |
| D-003@v1 | accepted | §3, §8, §9 | 保持 CLI、文件契约、产物语义不变 |
| D-004@v1 | accepted | §5, §10 | 并发上限采用保守默认值，失败按单篇 fallback |

无未解决决策。

## 12. 自审

| 检查项 | 结果 |
|---|---|
| 需求覆盖 | PASS：覆盖用户确认的 B 范围和方案A |
| Grill/决策覆盖 | PASS：design.md 引用 D-001@v1 至 D-004@v1 |
| 约束一致性 | PASS：符合文件接力、同步脚本、无新增第三方依赖约定 |
| 真实性 | PASS：函数名来自真实代码；新增 helper 已标注新增 |
| YAGNI | PASS：未纳入 step1_3、chromium 复用、asyncio 或 UI 改造 |
| 验收标准 | PASS：py_compile、dry-run、perf_profile 可验证 |
| 非目标清晰 | PASS：§3 明确排除项 |
| 兼容策略 | PASS：§9 覆盖 CLI、文件、失败和回退路径 |
| 风险识别 | PASS：列出限流、chromium、顺序、日志、性能波动 |
| 生命周期契约表 | PASS：本变更不涉及会话租约、后台守护、心跳或状态流转契约 |
