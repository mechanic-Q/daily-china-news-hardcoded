---
author: lmr
created_at: 2026-06-29 16:20:00
schema_version: 1
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# 模块影响分析

## 跨引验证

| 来源 | 文件列表 |
|------|----------|
| 声明范围 (design.md) | `archive_enrich.py`(新增), `step4.py`(修改), `news_archive.py`(修改), `tests/test_archive_enrich.py`(新增), `tests/test_news_archive.py`(修改) |
| 真实变更 (worktree git diff + untracked) | `archive_enrich.py`(新增), `step4.py`(修改), `news_archive.py`(修改), `tests/test_archive_enrich.py`(新增), `tests/test_news_archive.py`(修改), `meta.json`(新增, 测试残留) |
| 最终依据 | git diff 为准，排除 `meta.json`(测试产物，不归档) |

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| classifier | 调用关系变更 | `step4.py` | 在 `run()` 的 14A 归档后追加 try/except 调用 `archive_enrich.enrich_archive_best_effort` | false |
| extractor | 调用关系变更 | （通过 step6.fetch_and_extract） | `archive_enrich.enrich_body` 复用 `step6.fetch_and_extract`，但契约不变 | false |

## 更新结果

| 目标文件 | 操作 | 状态 |
|---------|------|------|
| `_module-map.yaml` | +archiver 模块条目 | ✅ 已写入 |
| `_module-map.yaml` | extractor.used_by +archiver | ✅ 已写入 |
| `_module-map.yaml` | orchestrator.depends_on +archiver | ✅ 已写入 |
| `_module-map.yaml` | source_commit/generated_at 刷新 | ✅ 已写入 |
| `modules/archiver.md` | 新建模块卡片 | ✅ 已写入 |
| `modules/extractor.md` | 注意事项追加 archiver 调用 | ✅ 已写入 |

## 未匹配文件

以下文件未匹配到现有模块映射中的任何 path glob。建议后续 scan 更新模块映射以包含 archiver 模块。

| 文件 | 操作 | 建议模块 | 说明 |
|------|------|----------|------|
| `archive_enrich.py` | 新增 | archiver | Phase 14B 归档增强核心模块。现有模块映射（source_commit=5f76a1a）不包含 archiver |
| `news_archive.py` | 修改 | archiver | Phase 14A 归档模块；新增 `SCHEMA_VERSION=2`、`IMAGES_DIR`、`BODY_IMAGE_FIELDS` |
| `tests/test_archive_enrich.py` | 新增 | tests | 33 条，覆盖 archive_enrich 全部核心行为 |
| `tests/test_news_archive.py` | 修改 | tests | 扩展 6 条，覆盖 schema v2 与 upsert 字段保留 |
