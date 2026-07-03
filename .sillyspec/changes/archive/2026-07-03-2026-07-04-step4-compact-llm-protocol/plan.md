---
author: lmr
created_at: 2026-07-04 00:37:20
plan_level: light
---

# 轻量计划：Step4 Compact LLM Protocol

## 来源

直接引用 brainstorm 结论：修复 step4 在 9router `low` 下 LLM 空响应/评分失效；采用紧凑协议主路径，涉华 batch 输出位串，栏目评分输出矩阵；parser 还原旧 `signals`；`low` 调用使用 `reasoning_effort="none"` 和 `max_tokens=262144`；不改评分算法和归档/月报结构。

## 范围

- `step4.py`: 位串 parser、矩阵 parser、涉华 batch prompt、栏目评分 prompt、fallback 衔接。
- `llm_client.py`: 空 content 诊断和 `LLMCallError`。
- `llm.yaml`: `low`/紧凑协议输出预算与 timeout 配置。
- `tests/test_step4.py`: parser 与 mock batch 端到端测试。
- `tests/test_llm_client.py`: 空 content 诊断测试。

## Wave 1

- [x] task-01: 新增涉华位串 parser 与单元测试（覆盖：FR-01, D-001@v1）
- [x] task-02: 新增栏目评分矩阵 parser 与单元测试（覆盖：FR-02, FR-03, D-003@v1）
- [x] task-03: 增强 `llm_client` 空 content 诊断（覆盖：FR-05, D-004@v1）

## Wave 2

- [x] task-04: 切换涉华 batch 到位串协议并保留 fallback（覆盖：FR-01, D-001@v1, D-002@v1）
- [x] task-05: 切换栏目评分 batch/单条 fallback 到矩阵协议（覆盖：FR-02, FR-03, D-001@v1, D-003@v1）
- [x] task-06: 为 `low` 调用注入 reasoning 和输出预算（覆盖：FR-04, D-004@v1）

## Wave 3

- [x] task-07: 增加 mock batch 端到端兼容测试（覆盖：FR-01, FR-02, FR-03, FR-06）

## Wave 4

- [x] task-08: 运行测试套件和 `2026-07-03` dry-run 验收（覆盖：全部 FR/D）

## 任务卡索引

| 任务 | 执行卡 | 主要文件 | 产出 |
|---|---|---|---|
| task-01 | `tasks/task-01.md` | `step4.py`, `tests/test_step4.py` | 涉华位串 parser 与单测 |
| task-02 | `tasks/task-02.md` | `step4.py`, `tests/test_step4.py` | 栏目评分矩阵 parser 与单测 |
| task-03 | `tasks/task-03.md` | `llm_client.py`, `tests/test_llm_client.py` | 空 content 诊断与 fail-fast 测试 |
| task-04 | `tasks/task-04.md` | `step4.py`, `tests/test_step4.py` | 涉华 batch 切到位串协议，保留 fallback |
| task-05 | `tasks/task-05.md` | `step4.py`, `tests/test_step4.py` | 栏目 batch/单条评分切到矩阵协议，保留 fallback |
| task-06 | `tasks/task-06.md` | `step4.py`, `llm.yaml`, `tests/test_step4.py`, `tests/test_llm_client.py` | `low` 紧凑协议调用使用 `reasoning_effort=none` 与 `max_tokens=262144` |
| task-07 | `tasks/task-07.md` | `tests/test_step4.py`, `news_archive.py` | mock batch E2E 与归档兼容测试 |
| task-08 | `tasks/task-08.md` | `step4.py`, `llm_client.py`, `llm.yaml`, `tests/` | 全量测试与 `2026-07-03` dry-run 验收 |

## 依赖链

| 下游任务 | 依赖 | 原因 |
|---|---|---|
| task-04 | task-01 | 涉华 batch 先依赖位串 parser |
| task-05 | task-02 | 栏目评分先依赖矩阵 parser |
| task-06 | task-03 | `low` 调用参数依赖空 content 诊断可观测性 |
| task-07 | task-04, task-05, task-06 | E2E 需要两类协议和 `low` 参数都落地 |
| task-08 | task-07 | dry-run 前先通过 mock 端到端验证 |

## 实施边界

- 不改 `aggregate_scores()`。
- 不改 `assign_category()`。
- 不改 `priority_score()`。
- 不改 `COLUMN_ORDER`。
- 不改 `news_archive.py`、`monthly_report.py` 的数据结构。
- 不引入新依赖。
- 不把紧凑协议文本写入归档字段。
- 解析失败只进入现有 fallback，不让流水线崩溃。
- 空 `message.content` 在 `llm_client.py` fail-fast 并记录诊断，避免下游误判为 JSON/parser 错误。

## 验证顺序

- `python3 -m pytest tests/test_step4.py -k bitstring -v`
- `python3 -m pytest tests/test_step4.py -k matrix -v`
- `python3 -m pytest tests/test_llm_client.py -v`
- `python3 -m pytest tests/test_step4.py tests/test_llm_client.py -v`
- `python3 -m pytest tests/ -v`
- `python3 step4.py --date 2026-07-03 --dry-run`

## 验收

- AC-01: `python3 -m pytest tests/` 通过。
- AC-02: 位串 parser 拒绝长度不匹配或非 `0/1` 输出。
- AC-03: 矩阵 parser 拒绝缺行、重复 index、列数不是 9、数值超出 0-10 的输出。
- AC-04: 矩阵 parser 输出保持旧 `signals` 结构，可被 `aggregate_scores()` 和 `assign_category()` 使用。
- AC-05: 空 `message.content` 抛出 `LLMCallError`，日志包含 `finish_reason/content_len/reasoning_len`。
- AC-06: `python3 step4.py --date 2026-07-03 --dry-run` 不出现 `empty LLM response`。
- AC-07: dry-run 中非高置信关键词候选出现非空 `signals`，`score_source` 不再全部是 `keyword-fallback`。
- AC-08: `news_archive.py` 和 `monthly_report.py` 不需要代码变更。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02, task-04, task-05 | AC-02, AC-03, AC-06, AC-07 |
| D-002@v1 | task-04, task-05, task-08 | AC-04, AC-08 |
| D-003@v1 | task-02, task-05, task-07 | AC-03, AC-04 |
| D-004@v1 | task-03, task-06, task-08 | AC-05, AC-06 |
| FR-01 | task-01, task-04, task-07 | AC-02, AC-06 |
| FR-02 | task-02, task-05, task-07 | AC-03, AC-07 |
| FR-03 | task-02, task-05, task-07 | AC-04 |
| FR-04 | task-06, task-08 | AC-06 |
| FR-05 | task-03 | AC-05 |
| FR-06 | task-07, task-08 | AC-08 |

## 自检结果

- plan_level 标注为 light。
- 包含来源、范围、任务列表、验收、覆盖矩阵。
- 来源直接引用 brainstorm 结论，未扩写新目标。
- 所有任务使用 `- [ ] task-XX:` checkbox 格式。
- 验收标准具体可运行/可检查。
- D-001@v1/D-002@v1/D-003@v1/D-004@v1 全部可追踪。
- 无 P0/P1 unresolved blocker。
- 无 Mermaid、估时、泛泛风险分析、代码示例。
- 文件范围与 design.md 文件变更清单一致。
