#!/usr/bin/env python3
"""
archive_enrich.py — 归档正文 + 首图增强 helper 与 CLI
读 archive/articles/YYYY-MM.jsonl，对所有记录补正文、对 top10 补首图。
"""

import json
import os
import sys
import time
import traceback
import re
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timezone, timedelta
from pathlib import Path

from news_archive import (
    ARCHIVE_DIR, IMAGES_DIR, SCHEMA_VERSION,
    load_month_records, write_month_records, month_path, article_id,
)
from step6 import fetch_and_extract, needs_chromium, chromium_dom, fetch_html_static

CST = timezone(timedelta(hours=8))

AUTO_MAX_SECONDS = 180
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

BODY_STATUS_MISSING = "missing"
BODY_STATUS_EXTRACTED = "extracted"
BODY_STATUS_FAILED = "failed"
BODY_STATUS_SKIPPED = "skipped"

IMAGE_STATUS_NOT_SELECTED = "not_selected"
IMAGE_STATUS_MISSING = "missing"
IMAGE_STATUS_DOWNLOADED = "downloaded"
IMAGE_STATUS_NOT_FOUND = "not_found"
IMAGE_STATUS_FAILED = "failed"
IMAGE_STATUS_SKIPPED = "skipped"

ARCHIVE_STATUS_METADATA = "metadata-only"
ARCHIVE_STATUS_BODY_ENRICHED = "body-enriched"
ARCHIVE_STATUS_BODY_IMAGE = "body-image-enriched"
ARCHIVE_STATUS_BODY_FAILED = "body-failed"


def parse_args():
    date_str = None
    missing_only = "--missing-only" in sys.argv
    dry_run = "--dry-run" in sys.argv
    max_seconds = 0
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
        if a == "--max-seconds" and i + 1 < len(sys.argv):
            try:
                max_seconds = int(sys.argv[i + 1])
            except ValueError:
                print(f"错误: --max-seconds 无效: {sys.argv[i+1]}")
                sys.exit(1)
    if not date_str:
        today = datetime.now(CST).strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            today = date_str
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    return today, missing_only, dry_run, max_seconds


def image_month_dir(today_str):
    return IMAGES_DIR / today_str[:7]


def image_path_for(today_str, article_id_str, ext):
    return image_month_dir(today_str) / f"{article_id_str}{ext}"


def should_enrich_body(record, missing_only):
    status = record.get("body_status", BODY_STATUS_MISSING)
    if missing_only:
        return status in (BODY_STATUS_MISSING, BODY_STATUS_FAILED)
    return status in (BODY_STATUS_MISSING, BODY_STATUS_FAILED, BODY_STATUS_SKIPPED)


def should_enrich_image(record, missing_only):
    if not record.get("selected_in_top10"):
        return False
    status = record.get("image_status", IMAGE_STATUS_MISSING)
    if missing_only:
        return status in (IMAGE_STATUS_MISSING, IMAGE_STATUS_FAILED)
    return status in (IMAGE_STATUS_MISSING, IMAGE_STATUS_FAILED, IMAGE_STATUS_SKIPPED)


def enrich_body(record):
    url = record.get("url", "")
    title = record.get("title", "")
    now = datetime.now(CST).isoformat()
    result = {
        "body_extracted_at": now,
        "body_source_url": url,
    }
    try:
        body, err = fetch_and_extract(url, title)
        if body:
            result["body"] = body
            result["body_status"] = BODY_STATUS_EXTRACTED
            result["body_error"] = None
        else:
            result["body_status"] = BODY_STATUS_FAILED
            result["body_error"] = err
    except Exception as e:
        result["body_status"] = BODY_STATUS_FAILED
        result["body_error"] = str(e)
    return result


def fetch_html_for_image(record):
    url = record.get("url", "")
    try:
        if needs_chromium(url):
            return chromium_dom(url)
        return fetch_html_static(url)
    except Exception:
        return None


def extract_first_image_url(html, article_url):
    if not html:
        return None
    m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
    if m:
        img = urllib.parse.urljoin(article_url, m.group(1))
        if img.startswith("http://") or img.startswith("https://"):
            return img
        return None
    m = re.search(r'<meta[^>]*name="twitter:image"[^>]*content="([^"]+)"', html, re.I)
    if m:
        img = urllib.parse.urljoin(article_url, m.group(1))
        if img.startswith("http://") or img.startswith("https://"):
            return img
        return None
    m = re.search(r'<img[^>]+src="([^"]+)"', html, re.I)
    if m:
        img_src = m.group(1)
        if img_src.startswith("http://") or img_src.startswith("https://"):
            return img_src
        resolved = urllib.parse.urljoin(article_url, img_src)
        if resolved.startswith("http://") or resolved.startswith("https://"):
            return resolved
        return None
    return None


def guess_extension(content_type, url):
    ct = (content_type or "").lower()
    for pattern, ext in IMAGE_EXT_BY_TYPE.items():
        if pattern in ct:
            return ext
    _, dot = os.path.splitext(urllib.parse.urlparse(url).path)
    if dot and dot.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return dot.lower().replace("jpeg", "jpg")
    return ".jpg"


def download_image(image_url, image_path, dry_run=False):
    if dry_run:
        return "skipped", None, None
    try:
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 Daily/14B"},
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            if len(data) > MAX_IMAGE_BYTES:
                return "failed", "图片超过 5MB", None
            content_type = resp.headers.get("Content-Type", "")
            ext = guess_extension(content_type, image_url)
            final_path = image_path.with_suffix(ext) if ext else image_path
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_bytes(data)
            return "downloaded", None, str(final_path)
    except Exception as e:
        return "failed", str(e), None


def enrich_image(record, today_str, dry_run=False):
    now = datetime.now(CST).isoformat()
    if not record.get("selected_in_top10"):
        return {
            "image_status": IMAGE_STATUS_NOT_SELECTED,
        }
    url = record.get("url", "")
    article_id_val = record.get("id", "")
    html = fetch_html_for_image(record)
    image_url = extract_first_image_url(html, url)
    if not image_url:
        return {
            "image_status": IMAGE_STATUS_NOT_FOUND,
            "image_downloaded_at": now,
        }
    ext = guess_extension(None, image_url)
    ipath = image_path_for(today_str, article_id_val, ext)
    dl_status, dl_error, dl_final_path = download_image(image_url, ipath, dry_run)
    result = {
        "image_url": image_url,
        "image_path": dl_final_path if dl_status == "downloaded" else None,
        "image_status": dl_status,
        "image_error": dl_error,
        "image_downloaded_at": now,
    }
    return result


def enrich_records(today_str, records, selected=None, missing_only=False, dry_run=False, max_seconds=0):
    selected_urls = {a["url"] for a in selected} if selected else set()
    updated = []
    stats = {
        "total": len(records),
        "body_extracted": 0, "body_failed": 0, "body_skipped": 0,
        "image_downloaded": 0, "image_not_found": 0,
        "image_failed": 0, "image_not_selected": 0, "image_skipped": 0,
        "elapsed_seconds": 0.0,
    }
    start = time.time()
    for r in records:
        record = dict(r)
        if selected is not None:
            record["selected_in_top10"] = record.get("url") in selected_urls
        budget = max_seconds > 0 and (time.time() - start) >= max_seconds
        if budget:
            if should_enrich_body(record, missing_only):
                record["body_status"] = BODY_STATUS_SKIPPED
                stats["body_skipped"] += 1
            if should_enrich_image(record, missing_only):
                record["image_status"] = IMAGE_STATUS_SKIPPED
                stats["image_skipped"] += 1
            elif not record.get("selected_in_top10"):
                record.setdefault("image_status", IMAGE_STATUS_NOT_SELECTED)
                stats["image_not_selected"] += 1
            record.setdefault("archive_status", ARCHIVE_STATUS_METADATA)
            updated.append(record)
            continue
        if should_enrich_body(record, missing_only):
            body_update = enrich_body(record)
            record.update(body_update)
            if body_update.get("body_status") == BODY_STATUS_EXTRACTED:
                stats["body_extracted"] += 1
            else:
                stats["body_failed"] += 1
        else:
            stats["body_skipped"] += 1
        if should_enrich_image(record, missing_only):
            img_update = enrich_image(record, today_str, dry_run)
            record.update(img_update)
            ista = img_update.get("image_status")
            if ista == IMAGE_STATUS_DOWNLOADED:
                stats["image_downloaded"] += 1
            elif ista == IMAGE_STATUS_NOT_FOUND:
                stats["image_not_found"] += 1
            elif ista == IMAGE_STATUS_FAILED:
                stats["image_failed"] += 1
            else:
                stats["image_not_selected"] += 1
        elif record.get("selected_in_top10"):
            stats["image_skipped"] += 1
        else:
            record.setdefault("image_status", IMAGE_STATUS_NOT_SELECTED)
            stats["image_not_selected"] += 1
        body_status = record.get("body_status", BODY_STATUS_MISSING)
        image_status = record.get("image_status", IMAGE_STATUS_MISSING)
        if body_status == BODY_STATUS_EXTRACTED and image_status == IMAGE_STATUS_DOWNLOADED:
            record["archive_status"] = ARCHIVE_STATUS_BODY_IMAGE
        elif body_status == BODY_STATUS_EXTRACTED:
            record["archive_status"] = ARCHIVE_STATUS_BODY_ENRICHED
        elif body_status == BODY_STATUS_FAILED:
            record["archive_status"] = ARCHIVE_STATUS_BODY_FAILED
        else:
            record["archive_status"] = ARCHIVE_STATUS_METADATA
        updated.append(record)
    stats["elapsed_seconds"] = round(time.time() - start, 2)
    return updated, stats


def enrich_archive(today_str, selected=None, missing_only=False, dry_run=False, max_seconds=0):
    mp = month_path(today_str)
    records = load_month_records(mp)
    if not records:
        print(f"  无记录: {mp}")
        return
    today_records = [r for r in records.values() if r.get("date") == today_str]
    if not today_records:
        print(f"  当日无记录: {today_str}")
        return
    updated, stats = enrich_records(today_str, today_records, selected, missing_only, dry_run, max_seconds)
    print(f"  正文: {stats['body_extracted']}提取 {stats['body_failed']}失败 {stats['body_skipped']}跳过")
    print(f"  图片: {stats['image_downloaded']}下载 {stats['image_not_found']}无图 {stats['image_failed']}失败 {stats['image_not_selected']}非top10 {stats['image_skipped']}跳过")
    print(f"  耗时: {stats['elapsed_seconds']}秒")
    if dry_run:
        print(f"  [dry-run] 不写 JSONL，不下载图片")
        return
    for r in updated:
        rid = r["id"]
        records[rid] = r
    write_month_records(mp, records)
    print(f"  ✅ 已更新: {len(updated)}条 → {mp}")


def enrich_archive_best_effort(today_str, selected=None, dry_run=False):
    try:
        enrich_archive(today_str, selected, missing_only=True, dry_run=dry_run, max_seconds=AUTO_MAX_SECONDS)
    except Exception as e:
        traceback.print_exc()
        print(f"⚠ 归档正文/首图补全失败: {e}", file=sys.stderr)


def main():
    today_str, missing_only, dry_run, max_seconds = parse_args()
    print(f"═══ 归档增强 ═══")
    print(f"日期: {today_str}  补缺失: {missing_only}  dry-run: {dry_run}  max秒: {max_seconds}")
    enrich_archive(today_str, missing_only=missing_only, dry_run=dry_run, max_seconds=max_seconds)


if __name__ == "__main__":
    main()
