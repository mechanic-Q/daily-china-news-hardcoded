---
author: lmr
created_at: 2026-07-03 15:38:00
---

# 模块影响分析

## 三重交叉验证

| 来源 | 文件清单 |
|---|---|
| 声明范围 (design.md) | archive_enrich.py, step4.py, tests/test_archive_enrich.py |
| 真实变更 (git diff HEAD) | archive_enrich.py, step4.py, tests/test_archive_enrich.py |
| 一致 | ✅ 声明=真实 |

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|---|---|---|---|---|
| archiver | 逻辑变更 | archive_enrich.py | `enrich_records`/`enrich_archive`/`enrich_archive_best_effort` 增加 `include_images=True` 参数；`False` 时跳过图片分支、图片统计和 BODY_IMAGE 状态标记。尾入接口向前兼容。 | false |
| classifier | 调用关系变更 | step4.py | `archive_enrich.enrich_archive_best_effort()` 调用增加 `include_images=False`；`archive_articles_best_effort` 调用未改，正文增强继续执行。 | false |

## 未匹配文件

| 文件 | 说明 |
|---|---|
| tests/test_archive_enrich.py | 测试文件，不映射到生产模块。 |
| .sillyspec/changes/.../ | 变更规范文档，非源码模块。 |
| .sillyspec/.runtime/ | 运行时追踪文件，非源码模块。 |
| __pycache__/ | Python 字节码缓存，非源码模块。 |

## 跨模块影响

| 上游模块 | 下游模块 | 影响评估 |
|---|---|---|
| classifier (step4.py) | extractor (step6.py) | 无影响。`include_images` 是 `archive_enrich` 内部参数，不改变 step4 的数据产出。 |
| archiver (archive_enrich.py) | monthly (monthly_report.py) | 无影响。`include_images` 默认 `True`，monthly 直接 CLI 调用不改。 |

## 更新结果

| 目标 | 操作 | 状态 |
|---|---|---|
| `modules/archiver.md` | 定位行添加"直接 CLI 可用；step4 自动流水线自 Phase 15F 起默认禁用图片下载"；注意事项更新 step4 自动路径不再下载图片 | ✅ 已写入 |
| `_module-map.yaml` | 无需更新（paths/entrypoints/main_symbols/depends_on/used_by/status 均无变化） | ⏭️ 跳过 |
| `modules/classifier.md` | 无需更新（step4.py 调用参数变化不影响 classifier 模块契约） | ⏭️ 跳过 |
