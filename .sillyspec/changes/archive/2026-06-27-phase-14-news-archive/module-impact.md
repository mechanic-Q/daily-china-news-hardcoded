---
author: lmr
created_at: 2026-06-28T03:35:00
schema_version: 1
doc_type: module-impact
change_id: 2026-06-27-news-archive-core
phase: 14A
---

# Module Impact · Phase 14A News Archive Core

## 模块映射状态

`.sillyspec/docs/Daily/modules/_module-map.yaml` 不存在。建议运行 scan 生成模块映射。

## 影响文件清单（git diff 为准）

### 新增文件
| 文件 | 模块 | 影响类型 | 说明 |
|------|------|----------|------|
| `news_archive.py` | unmapped | 新增 | 归档 helper 模块: 常量/URL/id/JSONL upsert/best-effort |
| `archive_news.py` | unmapped | 新增 | 独立补跑 CLI: --date/--dry-run |
| `tests/test_news_archive.py` | unmapped | 新增 | 17 单元测试 |

### 修改文件
| 文件 | 模块 | 影响类型 | 说明 |
|------|------|----------|------|
| `step4.py` | unmapped | 逻辑变更 + 数据结构变更 + 接口变更 | Phase 13 9栏评分函数 + build_classification_result + run() archive 集成 |
| `step7.py` | unmapped | 配置变更 | COLUMN_ORDER 同步为 9 栏（含🤖 AI智能前沿） |
| `step8.py` | unmapped | 配置变更 | COLUMN_ORDER 同步为 9 栏（含🤖 AI智能前沿） |
| `llm.yaml` | unmapped | 配置变更 | 新增 column-score call site |

### 不变文件（确认无 diff）
- `run_all.sh` — 未修改

## 更新内容摘要

1. **news_archive.py**: 新增 JSONL 归档模块，自包含信源推断，无 import step4
2. **step4.py**: 新增9栏COLUMN_ORDER/score_signals/aggregate_scores/assign_category/_validate_signals/build_classification_result；run()重构为build_classification_result + best-effort archive调用
3. **step7/step8.py**: COLUMN_ORDER 同步9栏（与step4保持一致）
4. **llm.yaml**: 新增 column-score 配置 (max_tokens=256, temperature=0.0, timeout=30)
5. **archive_news.py**: 独立补跑 CLI，复用 build_classification_result
6. **tests/test_news_archive.py**: 17 测试覆盖 URL normalize/id/record/upsert/dry-run/best-effort

## 部署注意事项

- 运行 `python3 archive_news.py --date YYYY-MM-DD --dry-run` 验证归档写入
- 归档目录 `/mnt/e/每日新中国/archive/articles/` 在首次写入时自动创建
- `step4.run()` 已自动接入归档（best-effort），无需修改 `run_all.sh`
