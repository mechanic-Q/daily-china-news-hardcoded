#!/usr/bin/env python3
"""
news_archive.py — 新闻归档 helper 模块
按月度 JSONL 分片存储 metadata + score/signals，支持幂等 upsert。

用法:
    from news_archive import archive_articles_best_effort
    archive_articles_best_effort(today_str, classified, selected)
"""

import hashlib
import json
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path("/mnt/e/每日新中国")
ARCHIVE_DIR = BASE_DIR / "archive"
ARTICLES_DIR = ARCHIVE_DIR / "articles"
IMAGES_DIR = ARCHIVE_DIR / "images"
SCHEMA_VERSION = 2

__all__ = ["BASE_DIR", "ARCHIVE_DIR", "ARTICLES_DIR", "IMAGES_DIR",
           "SCHEMA_VERSION",
           "archive_articles", "archive_articles_best_effort",
           "load_month_records", "write_month_records",
           "build_record", "month_path", "article_id", "infer_source"]

CST = timezone(timedelta(hours=8))


def normalize_url(url):
    if not url:
        return ""
    url = url.rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    if url.startswith("www."):
        url = url[4:]
    if "?" in url:
        url = url.split("?")[0]
    return url


def article_id(url):
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()


def month_path(today_str):
    return ARTICLES_DIR / f"{today_str[:7]}.jsonl"


def infer_source(url, article):
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
    now = datetime.now(CST).isoformat()
    url = article.get('url', '')
    return {
        "schema_version": SCHEMA_VERSION,
        "id": article_id(url),
        "date": today_str,
        "archived_at": now,
        "updated_at": now,
        "source": infer_source(url, article),
        "url": url,
        "normalized_url": normalize_url(url),
        "title": article.get('title', ''),
        "column": article.get('category'),
        "category": article.get('category'),
        "rank_within_column": article.get('rank_within_column'),
        "aggregate_score": article.get('aggregate_score'),
        "priority": article.get('priority', 0),
        "selected_in_top10": url in selected_urls,
        "score_source": article.get('score_source', 'unknown'),
        "signals": article.get('signals'),
        "archive_status": "metadata-only",
    }


def migrate_record(record):
    r = record.copy()
    version = r.get('schema_version', 1)

    if version == SCHEMA_VERSION:
        return r

    if version == 1:
        if 'normalized_url' not in r:
            r['normalized_url'] = normalize_url(r.get('url', ''))
        if 'selected_in_top10' not in r:
            r['selected_in_top10'] = False
        if 'score_source' not in r:
            r['score_source'] = 'unknown'
        if 'archive_status' not in r:
            r['archive_status'] = 'metadata-only'
        if 'body_status' not in r:
            r['body_status'] = 'missing'
        if 'image_status' not in r:
            r['image_status'] = 'missing'
        if 'updated_at' not in r:
            r['updated_at'] = datetime.now(CST).isoformat()
        r['schema_version'] = SCHEMA_VERSION
        return r

    r['schema_version'] = SCHEMA_VERSION
    return r


def load_month_records(month_path):
    records = {}
    if month_path.exists():
        for line in month_path.read_text("utf-8").splitlines():
            line = line.strip()
            if line:
                r = json.loads(line)
                r = migrate_record(r)
                records[r['id']] = r
    return records


def write_month_records(month_path, records):
    month_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(records[k], ensure_ascii=False) for k in sorted(records)]
    month_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive_articles(articles, today_str, selected, dry_run=False):
    selected_urls = {a['url'] for a in selected} if selected else set()
    mp = month_path(today_str)
    existing = load_month_records(mp) if not dry_run else {}
    new_count = 0
    update_count = 0

    BODY_IMAGE_FIELDS = [
        'body', 'body_status', 'body_error', 'body_extracted_at', 'body_source_url',
        'image_url', 'image_path', 'image_status', 'image_error', 'image_downloaded_at',
    ]

    for a in articles:
        r = build_record(a, today_str, selected_urls)
        rid = r['id']
        if rid in existing:
            old = existing[rid]
            r['archived_at'] = old.get('archived_at', r['archived_at'])
            for f in BODY_IMAGE_FIELDS:
                if f in old:
                    r[f] = old[f]
            old_archive_status = old.get('archive_status', 'metadata-only')
            if old_archive_status not in ('metadata-only',):
                r['archive_status'] = old_archive_status
            existing[rid] = r
            update_count += 1
        else:
            existing[rid] = r
            new_count += 1

    if dry_run:
        print(f"  [dry-run] 归档: {new_count}新 {update_count}更新 → {mp}")
    else:
        write_month_records(mp, existing)
        print(f"  ✅ 已归档: {new_count}新 {update_count}更新 → {mp}")

    return new_count, update_count


def archive_articles_best_effort(today_str, classified, selected, dry_run=False):
    try:
        all_articles = []
        for col, items in classified.items():
            all_articles.extend(items)
        new, upd = archive_articles(all_articles, today_str, selected, dry_run)
        print(f"✅ 新闻归档: {new}新 {upd}更新")
    except Exception as e:
        traceback.print_exc()
        print(f"⚠ 新闻归档失败: {e}")
