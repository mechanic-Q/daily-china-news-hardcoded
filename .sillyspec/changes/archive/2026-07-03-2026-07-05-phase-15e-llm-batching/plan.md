---
author: lmr
created_at: 2026-07-03 02:52:00
schema_version: 1
doc_type: plan
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
plan_level: light
---

# 轻量计划：Phase 15E · LLM batching

## 来源

来自 `proposal.md`：Phase 15E 目标是在保持输出语义和运行步骤不变的前提下，把明显高置信度条目从 LLM 路径剥离，并把剩余低置信度条目做批处理，减少调用次数。

来自 `design.md`：重点落在 `step4.py` 的高置信度直通、批量涉华判断、批量栏目评分；`step7.py` 已有 `ThreadPoolExecutor(max_workers=3)`，本 phase 只做契约化验证和必要补强。

## 范围

- `step4.py` / classifier：批量涉华判断、批量栏目评分、高置信度关键词直通、解析与 fallback。
- `step7.py` / summarizer：确认并发摘要顺序和失败回退，必要时补强异常处理。
- `llm_client.py` / llm-client：默认不修改；仅在执行中确认必须时添加兼容薄 helper。
- `tests/manual/test_15e_llm_call_count.py`：新增手工验证脚本，统计调用次数与输出差异。

## Wave 1（可并行）

- [x] task-01: 新增 Phase 15E 手工调用计数与输出对比脚本（覆盖：FR-01, FR-02, FR-03, FR-04）
- [x] task-02: 在 `step4.py` 增加高置信度关键词直通，跳过明显无须 LLM 的栏目评分（覆盖：FR-01）
- [x] task-03: 在 `step4.py` 增加批量涉华判断，并保留现有单条 fallback（覆盖：FR-02, FR-04）
- [x] task-05: 验证 `step7.py` 摘要并发契约，必要时补强单条失败回退（覆盖：FR-05）

## Wave 2（依赖 task-02）

- [x] task-04: 在 `step4.py` 增加批量栏目评分，并保留现有单条评分与关键词 fallback（覆盖：FR-03, FR-04）

## Wave 3（依赖 task-01 至 task-05）

- [x] task-06: 运行 Phase 15E 验收检查，记录 LLM 调用次数、输出差异和 fallback 行为（覆盖：全部）

## 验收

- AC-01：`python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30` 可输出 `step4` LLM 调用计数；若样本不存在，输出清晰的缺样本提示。
- AC-02：`step4.py` 对高置信度标题不调用栏目评分 LLM，并仍写出与现有格式一致的 `1新闻_链接.md`。
- AC-03：批量涉华 JSON 解析失败、缺项或类型错误时，该批次回退到现有 `llm_is_china_related()` 单条路径。
- AC-04：批量栏目评分 JSON 解析失败、缺项或校验失败时，相关条目回退到现有 `score_signals()` / 关键词分类路径。
- AC-05：以 2026-06-30 样本验证时，`step4` 单日 LLM 调用次数 `<=30`，或报告明确说明未达标原因。
- AC-06：分类输出与 15A baseline 差异 `<=5%`，或报告列出差异供人工确认。
- AC-07：`step7.py` 摘要输出顺序保持与 `1新闻_链接.md` 一致；单条摘要失败时仍生成规则回退摘要。
- AC-08：`python3 -m py_compile step4.py step7.py llm_client.py` 通过。

## 自检

- [x] 输出明确标注 `plan_level: light`。
- [x] 有来源、范围、Wave 任务列表、验收标准四个部分。
- [x] 来源直接引用已有文档，未重新扩写。
- [x] 任务列表清晰且无实现细节。
- [x] 任务使用 execute 可解析的 `## Wave N` + checkbox 格式 `- [ ] task-XX:`。
- [x] 验收标准具体可验证。
- [x] 本 change 不存在 `decisions.md`，无 D-xxx@vN 需要追踪。
- [x] 不存在 P0/P1 unresolved blocker。
- [x] 没有 Mermaid 图、估时、风险分析。
- [x] 没有函数签名、代码示例等实现细节。
- [x] `plan.md` 与 `design.md` 的文件变更清单一致。
