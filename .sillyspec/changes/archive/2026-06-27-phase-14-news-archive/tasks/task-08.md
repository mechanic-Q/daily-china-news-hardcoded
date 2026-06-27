---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-08
title: 新增 tests/test_news_archive.py
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07]
blocks: [task-09]
requirement_ids: [FR-09]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-008@v1, D-009@v1, D-010@v1]
allowed_paths:
  - tests/test_news_archive.py
  - tests/__init__.py
---

# task-08: 新增 tests/test_news_archive.py

## 修改文件
- `tests/test_news_archive.py`（新文件）

## 覆盖来源
- Requirements: FR-09 (测试覆盖)
- Decisions: D-001~D-010@v1

## 实现要求

创建 `tests/test_news_archive.py`，使用 `unittest.TestCase` + `unittest.mock`，独立可跑：

必须覆盖的测试用例（≥15 个）：
- `test_normalize_url`: 去掉尾部 `/`、`?query`
- `test_article_id_stability`: 同 URL 同 id
- `test_month_path`: "2026-06-15" → Path("archive/articles/2026-06.jsonl")
- `test_infer_source_xinhua`: url 含 news.cn → "新华社"
- `test_infer_source_cankaoxiaoxi`: url 含 cankaoxiaoxi → "参考消息"
- `test_build_record_all_keys`: record 含 12 个 key
- `test_build_record_selected_in_top10`: url 在 selected → True
- `test_build_record_signals_none`: 缺 signals → None
- `test_load_empty_month`: 不存在文件 → `{}`
- `test_write_and_load_roundtrip`: 写 3 条 → 读回 3 条
- `test_upsert_keep_archived_at`: 旧 archived_at 保留
- `test_upsert_update_other_fields`: title 更新
- `test_dry_run_no_write`: dry_run=True → 文件不变
- `test_best_effort_catches_exception`: archive_articles 抛错 → 不传播
- `test_archive_imports`: `rg "from step4" news_archive.py` 无匹配

## 接口定义

```python
import unittest
from unittest import mock
import tempfile
from pathlib import Path
import json

from news_archive import (
    normalize_url, article_id, month_path,
    infer_source, build_record,
    load_month_records, write_month_records, archive_articles,
    archive_articles_best_effort,
)
```

## 边界处理

1. 所有测试用 `tempfile.TemporaryDirectory` 隔离不污染 `/mnt/e/每日新中国`
2. mock `step4.build_classification_result` 测试 archive_news.py
3. 测试包含 URL 带 unicode/非 ASCII 情况
4. 文件可独立执行：`python3 tests/test_news_archive.py`
5. 文件可被 pytest 发现
6. 不调真实 LLM，不调真实网络
7. `tests/__init__.py` 若不存在则创建空文件

## 非目标
- 不覆盖 step4 原有评分逻辑（已有 test_column_scoring.py）
- 不做集成/端到端测试

## 参考
- tests/test_column_scoring.py 作为样式参考
- design.md §7 接口定义
- design.md §8 数据模型

## TDD 步骤
1. 写所有 test_* 骨架（空 body 或 skipTest）
2. 逐个填充
3. 跑 `python3 tests/test_news_archive.py`
4. 全部通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `python3 tests/test_news_archive.py` 通过 | exit 0 |
| AC-02 | ≥15 个 test_ 函数 | `rg "^    def test_" tests/test_news_archive.py | wc -l` ≥ 15 |
| AC-03 | 不调真实 LLM | 无 `call_llm` 调用 |
| AC-04 | 不依赖外部文件 | 用 mock/TemporaryDirectory |
| AC-05 | 独立可跑 | `python3 tests/test_news_archive.py` 不报 ImportError |
