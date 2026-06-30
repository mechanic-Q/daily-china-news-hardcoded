---
author: lmr
created_at: 2026-06-30 01:29:41
change: 2026-06-29-perf-optimize
doc_type: requirements
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 实现和验证 Daily 流水线性能优化的人 |
| 运行者 | 使用 `run_all.sh` 或单步脚本生成每日新闻的人 |
| 维护者 | 后续维护 step6/step7、排查失败和性能回退的人 |

## 功能需求

### FR-01: step6 正文提取文章级并发

覆盖决策：D-001@v1, D-002@v1, D-004@v1

Given `1新闻_链接.md` 存在且包含多篇文章 URL
When 运行 `python3 step6.py --date YYYY-MM-DD`
Then `step6.py` 使用受限线程池并发调用单篇正文提取逻辑
And 输出 `2新闻_已审核.md` 的文章顺序与输入顺序一致
And 单篇失败写入 `[正文提取失败: ...]`，不阻断其他文章

### FR-02: step7 摘要生成文章级并发

覆盖决策：D-001@v1, D-002@v1, D-004@v1

Given `1新闻_链接.md` 与 `2新闻_已审核.md` 存在且可匹配
When 运行 `python3 step7.py --date YYYY-MM-DD`
Then `step7.py` 使用受限线程池并发调用单篇摘要逻辑
And 每篇摘要失败时仍调用 `fallback_summarize()`
And 输出 `3新闻_概述.md` 仍按 `COLUMN_ORDER` 分栏目

### FR-03: CLI 与文件接力契约不变

覆盖决策：D-003@v1

Given 运行者使用现有命令
When 执行 `python3 step6.py --date YYYY-MM-DD [--dry-run]` 或 `python3 step7.py --date YYYY-MM-DD [--dry-run]`
Then CLI 参数、默认日期行为、dry-run 行为保持兼容
And `run_all.sh` 不需要修改即可继续调用 step6 和 step7

### FR-04: Markdown 产物格式不变

覆盖决策：D-003@v1

Given `step6.py` 和 `step7.py` 完成运行
When 下游 `step7.py` 或 `step8.py` 读取产物
Then `2新闻_已审核.md` 保持 `## 【来源】标题` + `正文：...` 格式
And `3新闻_概述.md` 保持栏目标题与摘要段落格式
And 下游无需修改解析逻辑

### FR-05: 并发风险受控

覆盖决策：D-004@v1

Given 外部网络、chromium 或 LLM 可能波动
When 多篇文章并发处理
Then `step6.py` 和 `step7.py` 使用保守默认并发上限
And worker 不直接写最终文件
And 主线程统一回填结果、统计成功数量和写文件

### FR-06: 性能可对比验证

覆盖决策：D-001@v1

Given Phase 12 已有 `perf_profile.py`
When 运行 `python3 perf_profile.py --date YYYY-MM-DD --dry-run`
Then 验证记录应能对比 `step6.py` 与 `step7.py` 变更前后耗时
And 如网络或 LLM 波动影响结论，应在验证记录中说明

## 非功能需求

- 兼容性：不改变 `run_all.sh`、CLI、文件名、Markdown 契约、栏目顺序。
- 可回退：可把 `run()` 中并发循环替回原串行循环，保留 helper 不影响外部接口。
- 可测试：至少通过 `py_compile`、step6/step7 dry-run、perf_profile dry-run。
- 可靠性：单篇失败不阻断全局；LLM 失败仍 fallback。
- 依赖控制：只使用 Python 标准库 `concurrent.futures`，不新增第三方依赖。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-02, FR-06 | 范围只做 step6 + step7 并发 |
| D-002@v1 | FR-01, FR-02 | ThreadPoolExecutor 保守并发 |
| D-003@v1 | FR-03, FR-04 | 文件接力与产物语义不变 |
| D-004@v1 | FR-01, FR-02, FR-05 | 保守并发上限与单篇失败处理 |
