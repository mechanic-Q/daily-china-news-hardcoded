---
author: lmr
created_at: 2026-07-03 14:44:13
schema_version: 1
doc_type: design
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: design-confirmed
---

# Design · Phase 15F · disable automatic image collection

## 目标/背景/问题描述

`step4.py` 当前在精选新闻写入后调用 `archive_enrich.enrich_archive_best_effort(today_str, selected, dry_run=dry_run)`。该调用会在一个 best-effort 流程内同时补正文和补 top10 首图。

用户当前不想继续自动收集图片，但仍需要正文归档增强。15F 因此从“提升图片质量”改为“禁用自动流水线图片收集”。核心问题是：现有 `archive_enrich` 没有 body-only 调用入口，直接删除 `step4.py` 调用会误伤正文增强，全局禁用图片逻辑又会破坏直接 CLI 兼容。

## 背景

自动图片下载会增加外部网络请求、磁盘写入和 `AUTO_MAX_SECONDS=180` 的归档预算消耗。图片字段和历史文件仍需保持兼容，因为已有月报统计和历史 JSONL 记录会引用 `image_status` / `image_path` / `image_url`。

## 设计目标

- `step4.py` 自动流程不再收集图片。
- 正文增强继续运行。
- `archive_enrich.py` 直接 CLI 默认行为保持兼容。
- 不改变 JSONL schema 或 `image_status` 状态集合。
- 通过现有 archive enrichment 测试验证回归。

## 非目标

- 不删除历史图片文件。
- 不清空历史 `image_url` / `image_path` 字段。
- 不新增全局配置文件或环境变量。
- 不重写图片候选提取、过滤、尺寸校验逻辑。
- 不改月报图片统计逻辑。

## 拆分判断

本次变更只影响 `archive_enrich.py` 和 `step4.py` 两个文件，不涉及多角色权限、跨页面状态、批量模板生成或多个可独立交付模块。无需拆分子阶段，也不走批量模式。

## 决策/方案选择

用户选择方案 A：参数开关。

| 方案 | 核心思路 | 结果 |
|---|---|---|
| A 参数开关 | 给 `archive_enrich` 调用链增加 `include_images=True` 参数，`step4.py` 传 `False` | 采纳 |
| B 全局禁用 | 让 `should_enrich_image()` 永远返回 `False` | 拒绝，破坏 CLI 兼容 |
| C 新增 body-only wrapper | 新建 `enrich_archive_body_best_effort()` | 拒绝，新增函数更多且容易复制逻辑 |

采纳理由：A 是最小可逆改动，能精确表达“只禁用 step4 自动图片收集”，同时不破坏直接 CLI 默认行为。

## 总体方案

在 `archive_enrich.py` 中把图片增强从固定行为改为可选参数：

1. `enrich_records(..., include_images=True)`：参数为 `False` 时跳过图片预算标记、`should_enrich_image()` 判断、`enrich_image()` 调用和图片统计更新。
2. `enrich_archive(..., include_images=True)`：将参数传给 `enrich_records()`，并在禁用图片时不打印图片统计行。
3. `enrich_archive_best_effort(..., include_images=True)`：将参数传给 `enrich_archive()`。
4. `step4.py` 自动流程调用 `enrich_archive_best_effort(today_str, selected, dry_run=dry_run, include_images=False)`。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `archive_enrich.py` | 为归档增强调用链增加 `include_images` 参数，禁用时跳过图片分支 |
| 修改 | `step4.py` | 自动流水线传 `include_images=False`，仅保留正文增强 |
| 修改 | `tests/test_archive_enrich.py` | 增加 body-only 参数行为回归测试 |

## 接口定义

新增参数保持默认兼容：

```python
def enrich_records(today_str, records, selected=None, missing_only=False,
                   dry_run=False, max_seconds=0, include_images=True):
    ...

def enrich_archive(today_str, selected=None, missing_only=False,
                   dry_run=False, max_seconds=0, include_images=True):
    ...

def enrich_archive_best_effort(today_str, selected=None, dry_run=False,
                               include_images=True):
    ...
```

`step4.py` 调用：

```python
archive_enrich.enrich_archive_best_effort(
    today_str, selected, dry_run=dry_run, include_images=False
)
```

## 数据模型

无 JSONL schema 变更。保留现有字段：

- `image_url`
- `image_path`
- `image_status`
- `image_error`
- `image_downloaded_at`

## 兼容策略

- 新参数默认 `True`，未配置新功能时行为不变。
- `python3 archive_enrich.py --date YYYY-MM-DD` 继续默认尝试图片增强。
- `step4.py` 是唯一自动禁用图片收集的入口。
- 历史图片字段和历史本地图片文件不迁移、不删除。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 禁用图片后统计输出仍显示图片指标，误导运行者 | P2 | `enrich_archive()` 在 `include_images=False` 时跳过图片统计行 |
| R-02 | 参数名与函数名 `enrich_image` 重名导致默认路径调用布尔值 | P1 | Design Grill 修正为 `include_images` 参数 |
| R-03 | 直接 CLI 默认行为被误改为禁用图片 | P1 | 默认参数必须为 `True`，测试覆盖默认仍调用图片分支 |

## 决策追踪

- D-001@v1 覆盖 FR-01、FR-02、FR-03：禁用范围只限 `step4.py` 自动图片收集，正文增强继续，直接 CLI 默认兼容。
- D-002@v2 覆盖 FR-01、FR-03：选择方案 A 参数开关，参数名为 `include_images`，拒绝全局禁用和新增 wrapper。

## 自审

| 检查项 | 结果 |
|---|---|
| 需求覆盖 | PASS：覆盖禁用自动图片收集、保留正文、CLI 默认兼容 |
| Grill/决策覆盖 | PASS：引用 D-001@v1、D-002@v2 |
| 约束一致性 | PASS：符合现有 Python 脚本式结构，无新依赖 |
| 真实性 | PASS：函数名和文件路径来自真实代码 |
| YAGNI | PASS：未新增配置文件、模块或抽象 |
| 验收标准 | PASS：可用单测验证图片分支未调用、正文分支仍调用 |
| 非目标清晰 | PASS：明确不删除历史图片、不改 schema |
| 兼容策略 | PASS：默认参数保持旧行为 |
| 风险识别 | PASS：列出统计输出、默认行为、命名遮蔽风险并已修正 |

自审结论：通过。
