---
author: lmr
created_at: 2026-07-03 14:46:30
plan_level: light
---

# 轻量计划：禁用 step4 自动图片收集

## 来源

直接引用 brainstorm 结论：15F 从图片质量优化改为禁用 `step4.py` 自动流水线图片收集；正文归档增强继续运行；`archive_enrich.py` 直接 CLI 默认仍可收集图片；参数名使用 `include_images`，避免遮蔽 `enrich_image()` 函数。

## 范围

- `archive_enrich.py`：归档增强聚合调用链增加 `include_images` 参数，禁用时跳过图片分支。
- `step4.py`：自动归档增强调用传 `include_images=False`。
- `tests/test_archive_enrich.py`：覆盖 body-only 行为和默认兼容行为。

## Wave 1

- [x] task-01: 为 `archive_enrich` 调用链增加 `include_images` 图片开关（覆盖：FR-01, FR-02, FR-03, D-001@v1, D-002@v2）
- [x] task-02: 在 `step4.py` 自动流程禁用图片增强（覆盖：FR-01, FR-02, D-001@v1, D-002@v2）
- [x] task-03: 增加 archive enrichment 回归测试（覆盖：FR-01, FR-02, FR-03, D-001@v1, D-002@v2）

## 验收

- AC-01: `step4.py` 调用 `archive_enrich.enrich_archive_best_effort(..., include_images=False)`。
- AC-02: `include_images=False` 时 `enrich_records()` 不调用 `enrich_image()`，但仍调用 `enrich_body()`。
- AC-03: 默认调用路径不传 `include_images` 时仍保持旧行为，会调用图片分支。
- AC-04: `include_images=False` 时不新增图片统计输出，不误导运行者。
- AC-05: `python3 -m unittest discover -s tests -p 'test_archive_enrich.py' -v` 通过。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02, task-03 | AC-01, AC-02, AC-05 |
| D-002@v2 | task-01, task-02, task-03 | AC-01, AC-02, AC-03 |
| FR-01 | task-01, task-02, task-03 | AC-01, AC-02, AC-05 |
| FR-02 | task-01, task-02, task-03 | AC-02, AC-05 |
| FR-03 | task-01, task-03 | AC-03, AC-05 |
| FR-04 | task-01 | AC-03 |

## 自检

- [x] 输出明确标注 `plan_level: light`。
- [x] 有来源、范围、任务列表、验收标准四个部分。
- [x] 来源直接引用已有文档，未重新扩写。
- [x] 任务列表清晰且无实现细节。
- [x] 任务使用 checkbox 格式。
- [x] 验收标准具体可验证。
- [x] 当前版本决策 D-001@v1、D-002@v2 在 plan.md 中可追踪。
- [x] 不存在 P0/P1 unresolved blocker。
- [x] 没有 Mermaid 图、估时、风险分析。
- [x] 没有函数签名、代码示例等实现细节。
- [x] plan.md 与 design.md 的文件变更清单一致。
