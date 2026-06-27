---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-01
title: 新增 news_archive.py 常量与 URL/id 工具
priority: P0
depends_on: []
blocks: [task-03, task-04]
requirement_ids: [FR-03]
decision_ids: [D-002@v1]
allowed_paths:
  - news_archive.py
---

# task-01: 新增 news_archive.py 常量与 URL/id 工具

## 修改文件
- `news_archive.py`（新文件）

## 覆盖来源
- Requirements: FR-03 (JSONL 归档每个合格文章)
- Decisions: D-002@v1 (14A 只存 metadata + score/signals)

## 实现要求

1. 创建 `news_archive.py`，不含外部依赖
2. 定义常量：
   - `BASE_DIR = Path("/mnt/e/每日新中国")`
   - `ARCHIVE_DIR = BASE_DIR / "archive"`
   - `ARTICLES_DIR = ARCHIVE_DIR / "articles"`
   - `SCHEMA_VERSION = 1`
3. `normalize_url(url)`: 去尾部 `/`、去 `www.`、去 `?` 后 query string
4. `article_id(url)`: `sha1(normalize_url(url)).hexdigest()`，用 `hashlib.sha1`
5. `month_path(today_str)`: `ARTICLES_DIR / f"{today_str[:7]}.jsonl"`（如 `2026-06.jsonl`）

## 接口定义

```python
def normalize_url(url):
    """去尾部/、去www.、去query，返回纯路径"""
    ...

def article_id(url):
    """基于 normalize_url 的稳定 sha1 hex string"""
    import hashlib
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()

def month_path(today_str):
    """today_str YYYY-MM-DD → ARCHIVE_DIR/YYYY-MM.jsonl"""
    from pathlib import Path
    return Path(f"archive/articles/{today_str[:7]}.jsonl")
```

## 边界处理

1. URL 为 None → normalize_url 返回空字符串
2. 不同 query string 的同 URL → normalize 后同 id（去重依赖）
3. `ARTICLE_DIR` 不存在 → `write_month_records` 生产端 `mkdir(parents=True)`
4. SHA1 碰撞风险可忽略（URL 长度远小于 2^80）
5. month_path 只返回 Path 对象，不保证文件存在
6. 不写 type hints

## 非目标
- 不实现 JSONL 读写（task-03）
- 不实现 record 构造（task-02）
- 不处理 URL 编码/解码（urllib 天然）

## 参考
- design.md §5.3 数据流
- design.md §7.1 news_archive 模块接口

## TDD 步骤
1. 先写 tests/test_news_archive.py 的 test_normalize_url、test_article_id_stability、test_month_path
2. 确认失败
3. 实现
4. 通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `normalize_url("https://example.com/path/")` | `"example.com/path"` |
| AC-02 | 同 URL 不同 query 产生同 `article_id` | `article_id(a) == article_id(b)` |
| AC-03 | `month_path("2026-06-15")` | `Path("archive/articles/2026-06.jsonl")` |
| AC-04 | `article_id` 对空字符串也返回稳定值 | `isinstance(h, str) and len(h) == 40` |
| AC-05 | 文件不含 type hints | `rg "->" news_archive.py` 无匹配 |
