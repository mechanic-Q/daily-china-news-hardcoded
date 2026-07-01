from __future__ import annotations

import datetime
import os
import sys
from datetime import date, timezone, timedelta
from pathlib import Path
from typing import Tuple


BASE_DIR: Path = Path(os.environ.get("DAILY_OUTPUT_DIR", "/mnt/e/每日新中国"))

CST: timezone = timezone(timedelta(hours=8))

COLUMN_ORDER: list[str] = [
    '🔬 世界性科研突破',
    '🤖 AI智能前沿',
    '🌾 农业',
    '🤝 扶贫',
    '⚡ 能源',
    '🏥 医疗',
    '🚀 科技',
    '🧱 材料',
    '🎖️ 军事',
]

WEEKDAYS: list[str] = [
    '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'
]


def today_cst() -> date:
    return datetime.datetime.now(CST).date()


def parse_common_args() -> Tuple[date, bool]:
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}，应为 YYYY-MM-DD")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry


def detect_source(url: str) -> str:
    if not url:
        return '综合'
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


def workdir(d: date) -> Path:
    return BASE_DIR / d.strftime("%Y-%m-%d")
