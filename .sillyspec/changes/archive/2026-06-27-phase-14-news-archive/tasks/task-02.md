---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-02
title: 新增 news_archive.py record 构造
priority: P0
depends_on: [task-01]
blocks: [task-04]
requirement_ids: [FR-02, FR-08]
decision_ids: [D-002@v1, D-009@v1]
allowed_paths:
  - news_archive.py
---

# task-02: 新增 news_archive.py record 构造

## 修改文件
- `news_archive.py`（追加函数）

## 覆盖来源
- Requirements: FR-02 (record schema)、FR-08 (selected_in_top10)
- Decisions: D-002@v1 (metadata-only)、D-009@v1 (不 import step4)

## 实现要求

1. `infer_source(url, article)`: 从 url 推断信源名称，逻辑复用 `step4.detect_source` 的域名匹配但不 import step4
2. `build_record(article, today_str, selected_urls)`: 构造 archive record dict
3. Record schema：
```python
{
    "id": article_id(article['url']),
    "url": article['url'],
    "title": article['title'],
    "source": infer_source(article['url'], article),
    "date": today_str,
    "column": article.get('category'),
    "score": article.get('priority', 0),
    "score_source": article.get('score_source', 'unknown'),
    "selected_in_top10": article['url'] in selected_urls,
    "signals": article.get('signals'),  # 可为 None
    "archived_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "archive_status": "metadata-only"
}
```

## 接口定义

```python
def infer_source(url, article):
    """从 url 推断信源，与 step4.detect_source 逻辑一致但不 import step4"""
    if 'cankaoxiaoxi' in url or 'ckxxapp' in url:
        return '参考消息'
    if 'military.cctv' in url:
        return '央视军事'
    if 'news.cctv' in url:
        return '央视新闻'
    if 'cas.cn' in url:
        return '中科院'
    if 'cnnpn.cn' in url or 'cnnc.com' in url:
        return '中核集团'
    if 'people.com.cn' in url:
        return '人民日报'
    if 'news.cn' in url or 'xinhuanet' in url:
        return '新华社'
    return '综合'

def build_record(article, today_str, selected_urls):
    """article dict → archive record dict"""
```

## 边界处理

1. `article['category']` 不存在 → record `column` 字段为 `None`
2. `article['priority']` 不存在 → `score` 为 0
3. `article.get('signals')` 为 None → record 中 `signals` 为 `None`（合法）
4. `selected_in_top10` 判断用 `article['url'] in selected_urls`
5. `archived_at` 和 `updated_at` 调用时用 `datetime.now().isoformat()`
6. 不 import step4 — `infer_source` 自包含域名匹配逻辑
7. 不写 type hints

## 非目标
- 不实现 JSONL 写入（task-03）
- 不处理正文/图片
- 不检查 URL 合法性

## 参考
- design.md §8 record schema
- step4.py detect_source (L406-421)

## TDD 步骤
1. 写 test_infer_source、test_build_record_fields、test_selected_in_top10
2. 确认失败
3. 实现
4. 通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `infer_source("https://news.cn/...")` | `"新华社"` |
| AC-02 | record 含全部 12 个 key | `set(record.keys())` 匹配预期 |
| AC-03 | url 在 selected_urls → selected_in_top10 = True | assert True |
| AC-04 | article 缺 signals → signals=None | assert record['signals'] is None |
| AC-05 | `rg "from step4" news_archive.py` | 无匹配 |
