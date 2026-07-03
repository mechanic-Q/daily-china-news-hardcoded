---
author: lmr
created_at: 2026-07-03 14:44:13
schema_version: 1
doc_type: requirements
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: design-confirmed
---

# Requirements · Phase 15F · disable automatic image collection

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 运行 `run_all.sh` / `step4.py` 自动流水线 |
| 维护者 | 维护 `archive_enrich.py` 归档增强逻辑 |
| 月报读者 | 读取正文归档增强后的新闻内容 |

## 功能需求

### FR-01: 自动流水线禁用图片增强

覆盖决策：D-001@v1, D-002@v2

Given `step4.py` 自动归档增强运行  
When 调用 `archive_enrich.enrich_archive_best_effort()`  
Then 不执行图片 URL 抽取、图片下载或本地图片写入。

### FR-02: 自动流水线保留正文增强

覆盖决策：D-001@v1, D-002@v2

Given 当日归档记录缺少正文  
When `step4.py` 自动归档增强运行  
Then 仍执行 `fetch_and_extract()` 并更新 `body` / `body_status`。

### FR-03: 直接 CLI 默认兼容

覆盖决策：D-001@v1, D-002@v2

Given 维护者直接运行 `python3 archive_enrich.py --date YYYY-MM-DD`  
When 未显式传入新参数  
Then 默认行为仍允许图片增强，避免破坏手工维护路径。

### FR-04: 不改变归档 schema

覆盖决策：D-001@v1

Given 历史 JSONL 记录包含 `image_url`、`image_path`、`image_status`  
When Phase 15F 完成  
Then 不删除历史字段、不新增字段、不新增状态。

## 非功能需求

- 禁用图片收集不得阻塞正文归档。
- 变更应最小化，避免新增配置文件或新模块。
- 现有 archive enrichment 单测继续通过。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-02, FR-03, FR-04 | 禁用范围限定为 `step4.py` 自动图片收集，正文增强和 CLI 默认兼容保留 |
| D-002@v2 | FR-01, FR-02, FR-03 | 使用 `include_images` 参数开关，避免遮蔽 `enrich_image()` 函数 |
