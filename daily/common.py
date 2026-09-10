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


import re

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


BLOCKED_NEWS_TERMS: list[str] = ['习近平', '习主席', '习总书记']

# "习主席"/"习总书记" 会被 "学习主席讲话""练习主席台"这类动词+主席/总书记的
# 边界误切。只排除确定为学习动词的前字（学习/练习/复习/预习/补习/温习）；
# 不排除 实、见 等，因为"落实习主席""会见习主席"是真指称，误伤更危险。
# 注意"学习习主席重要讲话"里 习主席 的前字是 习 而非 学，仍能正确命中。
# "习近平"无此歧义，直接子串匹配。
_BLOCKED_TERM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'习近平'),
    re.compile(r'(?<![学练复预补温])习(?:主席|总书记)'),
]


def contains_blocked_term(text: str) -> bool:
    """news 文本（标题或正文）是否带有需整体剔除的敏感词。"""
    if not text:
        return False
    return any(p.search(text) for p in _BLOCKED_TERM_PATTERNS)


def detect_source(url: str) -> str:
    if not url:
        return ''
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
    return ''


def clean_news_title(title: str) -> str:
    if not title:
        return title
    t = title.strip()
    t = re.sub(r'^【[^】]{2,20}(?:报|网|社|台|新闻|新闻网|科学院|客户端)】\s*', '', t)
    t = re.sub(r'[-—＿_\|]{1,4}\s*(?:中国科学院|中国新闻网|中新网|新华网|央视网|人民网|中科院|光明网|光明日报|央视新闻|中国新闻|科学网)$', '', t)
    return t.strip()


def workdir(d: date) -> Path:
    return BASE_DIR / d.strftime("%Y-%m-%d")
