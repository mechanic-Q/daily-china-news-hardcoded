---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-03
title: 新增 news_archive.py JSONL load/write/upsert
priority: P0
depends_on: [task-01]
blocks: [task-04]
requirement_ids: [FR-04]
decision_ids: [D-008@v1]
allowed_paths:
  - news_archive.py
---

# task-03: 新增 news_archive.py JSONL load/write/upsert

## 修改文件
- `news_archive.py`（追加函数）

## 覆盖来源
- Requirements: FR-04 (JSONL 月度分片，upsert 幂等)
- Decisions: D-008@v1 (archived_at 保留 + updated_at 刷新)

## 实现要求

1. `load_month_records(mp)`: 读 `.jsonl` 文件 → `{id: record}` dict
2. `write_month_records(mp, records)`: 写回 jsonl（字典按 key 排序，每行 `json.dumps`）
3. `archive_articles(articles, today_str, selected, dry_run)`: 主函数
   - 调 `build_record` 构造每条 record
   - 调 `load_month_records` 读取已有记录
   - upsert: 若 id 已存在 → 保留 `archived_at`，刷新 `updated_at` 和其他字段
   - 新 record → 设 `archived_at` 和 `updated_at` 均为当前时间
   - `dry_run` 时只打印统计，不写入文件

## 接口定义

```python
def load_month_records(month_path):
    """返回 {id: record}，空文件返回 {}"""
    records = {}
    if month_path.exists():
        for line in month_path.read_text("utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                records[r['id']] = r
    return records

def write_month_records(month_path, records):
    """records dict → JSONL 文件"""
    month_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(records[k], ensure_ascii=False) for k in sorted(records)]
    month_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def archive_articles(articles, today_str, selected, dry_run=False):
    """
    articles: [article dict]
    today_str: "YYYY-MM-DD"
    selected: [article dict] (top-10)
    dry_run: 只统计不写
    返回: (new_count, updated_count)
    """
```

## 边界处理

1. JSONL 文件不存在 → `load_month_records` 返回 `{}`
2. JSONL 空/空行 → 返回 `{}`
3. JSONL 行损坏 → `json.JSONDecodeError` 向上抛，由 best-effort wrapper 捕获
4. `dry_run=True` → 不调用 `write_month_records`
5. upsert 保留 `archived_at`：`r['archived_at'] = old.get('archived_at', r['archived_at'])`
6. upsert 刷新 `updated_at` 和其他字段
7. 目录不存在时 `write_month_records` 自动 `mkdir(parents=True)`
8. 不写 type hints

## 非目标
- 不实现正文/图片归档
- 不实现月报生成
- 不压缩 JSONL

## 参考
- design.md §5.2 数据流
- design.md §8 record schema
- D-008@v1 upsert 策略

## TDD 步骤
1. 写 test_load_empty、test_write、test_upsert_keep_archived_at、test_dry_run_no_write
2. 确认失败
3. 实现
4. 通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | 空 JSONL → `load_month_records` 返回 `{}` | `len(result) == 0` |
| AC-02 | 写 3 条 → `load_month_records` 读回 3 条 | `len(result) == 3` |
| AC-03 | upsert 旧 record → `archived_at` 不变，`updated_at` 更新 | `old_at == new_at` |
| AC-04 | dry_run=True → 原文件未修改 | `before == after` |
| AC-05 | JSONL 行 sorted by id | 行 id 递增 |
