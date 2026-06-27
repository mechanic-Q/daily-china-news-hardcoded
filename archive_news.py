#!/usr/bin/env python3
"""
archive_news.py — 独立历史日期补跑新闻归档
用法: python3 archive_news.py --date YYYY-MM-DD [--dry-run]
"""

import datetime
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from step4 import build_classification_result
from news_archive import archive_articles


def parse_args():
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry


def main():
    today, dry_run = parse_args()
    today_str = today.strftime("%Y-%m-%d")

    print(f"═══ 新闻归档: {today_str} ═══")

    classified, selected = build_classification_result(today)

    if not classified:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    all_articles = []
    for items in classified.values():
        all_articles.extend(items)

    try:
        new, upd = archive_articles(all_articles, today_str, selected, dry_run)
        print(f"✅ 归档完成: {new}新 {upd}更新")
    except Exception as e:
        traceback.print_exc()
        print(f"⚠ 归档失败: {e}")


if __name__ == "__main__":
    main()
