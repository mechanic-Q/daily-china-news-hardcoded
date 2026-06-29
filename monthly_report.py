#!/usr/bin/env python3
import datetime
import html
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from news_archive import ARCHIVE_DIR, ARTICLES_DIR, IMAGES_DIR

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None
    ImageChops = None

ARCHIVE_DIR = Path("/mnt/e/每日新中国/archive")
ARTICLES_DIR = ARCHIVE_DIR / "articles"
IMAGES_DIR = ARCHIVE_DIR / "images"
MONTHLY_DIR = ARCHIVE_DIR / "monthly"
CST = datetime.timezone(datetime.timedelta(hours=8))
DEFAULT_TOP_PER_COLUMN = 3
DEFAULT_MAX_LLM_SECONDS = 30
LLM_MODEL = "glm-4-flash"
LLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
OVERVIEW_MAX_CHARS = 700
BODY_SNIPPET_CHARS = 300

COLUMN_ORDER = [
    "\U0001f52c \u4e16\u754c\u6027\u79d1\u7814\u7a81\u7834",
    "\U0001f916 AI\u667a\u80fd\u524d\u6cbf",
    "\U0001f33c \u519c\u4e1a",
    "\U0001f91d \u6276\u8d2b",
    "\u26a1 \u80fd\u6e90",
    "\U0001f3e5 \u533b\u7597",
    "\U0001f680 \u79d1\u6280",
    "\U0001f9f1 \u6750\u6599",
    "\U0001f396\ufe0f \u519b\u4e8b",
]


def parse_args():
    dry_run = "--dry-run" in sys.argv
    no_llm = "--no-llm" in sys.argv
    month = None
    top_per_column = DEFAULT_TOP_PER_COLUMN
    max_llm_seconds = DEFAULT_MAX_LLM_SECONDS
    for i, a in enumerate(sys.argv):
        if a == "--month" and i + 1 < len(sys.argv):
            month = sys.argv[i + 1]
        if a == "--top-per-column" and i + 1 < len(sys.argv):
            try:
                v = int(sys.argv[i + 1])
            except ValueError:
                print("\u9519\u8bef: --top-per-column \u975e\u6cd5\u503c")
                sys.exit(1)
            if v < 1 or v > 10:
                print("\u9519\u8bef: --top-per-column \u5fc5\u987b\u5728 1~10 \u4e4b\u95f4")
                sys.exit(1)
            top_per_column = v
        if a == "--max-llm-seconds" and i + 1 < len(sys.argv):
            try:
                v = int(sys.argv[i + 1])
            except ValueError:
                print("\u9519\u8bef: --max-llm-seconds \u975e\u6cd5\u503c")
                sys.exit(1)
            if v < 1:
                print("\u9519\u8bef: --max-llm-seconds \u5fc5\u987b\u22651")
                sys.exit(1)
            max_llm_seconds = v
    if month:
        try:
            datetime.datetime.strptime(month, "%Y-%m")
        except ValueError:
            print(f"\u9519\u8bef: \u6708\u4efd\u683c\u5f0f\u65e0\u6548: {month}")
            sys.exit(1)
    else:
        month = datetime.datetime.now(CST).strftime("%Y-%m")
    return month, dry_run, no_llm, top_per_column, max_llm_seconds


def load_month_jsonl(month):
    path = ARTICLES_DIR / f"{month}.jsonl"
    if not path.exists():
        print(f"\u274c archive\u7f3a\u5931: {path}")
        sys.exit(1)
    records = []
    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"\u26a0 JSON\u89e3\u6790\u5931\u8d25\u5df2\u8df3\u8fc7: {line[:80]}")
    return records


def normalize_record(rec):
    r = dict(rec)
    r.setdefault("body_status", "missing")
    r.setdefault("body", "")
    r.setdefault("image_status", "missing")
    r.setdefault("image_path", "")
    r.setdefault("image_url", "")
    r.setdefault("archive_status", "metadata-only")
    r.setdefault("selected_in_top10", False)
    r.setdefault("aggregate_score", 0)
    r.setdefault("archived_at", "")
    r.setdefault("source", "")
    r.setdefault("column", "")
    r.setdefault("url", "")
    r.setdefault("title", "")
    return r


def compute_stats(records, month):
    total = len(records)
    by_column = {}
    by_source = {}
    by_date = {}
    body_cov = {"extracted": 0, "failed": 0, "missing": 0, "skipped": 0}
    image_cov = {"downloaded": 0, "not_selected": 0, "not_found": 0, "failed": 0, "missing": 0, "skipped": 0}
    for r in records:
        col = r.get("column", "") or "(未分类)"
        by_column[col] = by_column.get(col, 0) + 1
        src = r.get("source", "") or "(未知)"
        by_source[src] = by_source.get(src, 0) + 1
        d = r.get("date", "")[:10]
        if d:
            by_date[d] = by_date.get(d, 0) + 1
        bs = r.get("body_status") if r.get("body_status") else "missing"
        body_cov[bs] = body_cov.get(bs, 0) + 1
        img_st = r.get("image_status") if r.get("image_status") else "missing"
        image_cov[img_st] = image_cov.get(img_st, 0) + 1
    sorted_column = dict(sorted(by_column.items(), key=lambda x: -x[1]))
    sorted_source = dict(sorted(by_source.items(), key=lambda x: -x[1]))
    sorted_date = dict(sorted(by_date.items()))
    top_kw = top_keywords(records, 20)
    return {
        "month": month,
        "total_records": total,
        "by_column": sorted_column,
        "by_source": sorted_source,
        "by_date": sorted_date,
        "body_coverage": body_cov,
        "image_coverage": image_cov,
        "top_keywords": top_kw,
    }


def top_keywords(records, limit=20):
    try:
        from step4 import CATEGORY_KEYWORDS
        flat = set()
        for words in CATEGORY_KEYWORDS.values():
            for w in words:
                flat.add(w)
    except Exception:
        return []
    counts = {}
    for r in records:
        title = r.get("title", "")
        body = (r.get("body", "") or "")[:BODY_SNIPPET_CHARS]
        text = title + " " + body
        for kw in flat:
            if kw in text:
                counts[kw] = counts.get(kw, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:limit]


def pick_top_per_column(records, top_n):
    groups = {}
    for r in records:
        col = r.get("column", "") or "(未分类)"
        groups.setdefault(col, []).append(r)
    result = {}
    for col in groups:
        items = sorted(groups[col], key=lambda x: (
            x.get("selected_in_top10", False),
            x.get("aggregate_score", 0) or 0,
            x.get("body_status") == "extracted",
            x.get("archived_at", "") or "",
        ), reverse=True)
        result[col] = items[:top_n]
    ordered = {}
    for col in COLUMN_ORDER:
        if col in result:
            ordered[col] = result[col]
    for col in result:
        if col not in ordered:
            ordered[col] = result[col]
    return ordered


def build_grounding_context(stats, picks):
    sys_lines = [
        "你是每日新中国月报撰写助手。",
        "基于下方提供的事实（统计和候选新闻）撰写月报总述与趋势解读。",
        "规则：",
        "- 只使用上方提供的事实，不在上方出现的事实禁止编造",
        "- 引用具体新闻用 [article_id] 格式",
        "- 输出两段：第一段月报总述（本月概况），第二段趋势解读（亮点栏目 / 变化 / 数据趋势）",
        "- 仅中文，总字数不超过700字",
        "- 不写标题，不写问候语",
    ]
    user_lines = [f"## 月度统计 ({stats['month']})"]
    user_lines.append(f"总归档: {stats['total_records']} 条")
    cols_top = list(stats['by_column'].items())[:5]
    user_lines.append(f"Top栏目: {', '.join(f'{c}({n})' for c, n in cols_top)}")
    srcs_top = list(stats['by_source'].items())[:3]
    user_lines.append(f"主要信源: {', '.join(f'{c}({n})' for c, n in srcs_top)}")
    bc = stats['body_coverage']
    user_lines.append(f"正文覆盖率: extracted={bc.get('extracted',0)} failed={bc.get('failed',0)} missing={bc.get('missing',0)}")
    user_lines.append("")
    user_lines.append("## 候选代表新闻")
    for col, items in picks.items():
        for r in items:
            aid = r.get("id", "")[:12]
            title = r.get("title", "")
            body = (r.get("body", "") or "")[:BODY_SNIPPET_CHARS]
            user_lines.append(f"[{aid}] {title} ({r.get('source','')} · {r.get('date','')})")
            if body:
                user_lines.append(f"  {body.replace(chr(10), ' ')}")
    return "\n".join(sys_lines), "\n".join(user_lines)


def llm_monthly_overview(context, max_seconds):
    key = os.environ.get("ZHIPU_API_KEY")
    if not key:
        return None
    system_msg, user_msg = context
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LLM_BASE_URL, api_key=key)
        result = [None]
        stop = [False]

        def do_call():
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                max_tokens=1200,
                timeout=max_seconds,
            )
            if not stop[0]:
                result[0] = resp.choices[0].message.content or None

        import threading
        t = threading.Thread(target=do_call, daemon=True)
        t.start()
        t.join(timeout=max_seconds)
        if t.is_alive():
            stop[0] = True
            return None
        return result[0]
    except Exception:
        return None


def sanitize_llm_text(text, valid_ids):
    if not text:
        return None
    import re
    found = set(re.findall(r'\[([a-f0-9]{6,40})\]', text))
    bad_ids = found - valid_ids
    for bid in bad_ids:
        text = text.replace(f"[{bid}]", "")
    if re.search(r'<[^>]+>', text):
        ascii_ratio = sum(1 for c in text if ord(c) < 128 and c.isalpha()) / max(len(text), 1)
        if ascii_ratio >= 0.3:
            return None
    if len(text) > OVERVIEW_MAX_CHARS:
        text = text[:OVERVIEW_MAX_CHARS]
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else None


def fallback_overview(stats, picks):
    total = stats["total_records"]
    top_cols = list(stats["by_column"].items())[:3]
    top_srcs = list(stats["by_source"].items())[:3]
    cols_str = "、".join(f"{c}({n}\u6761)" for c, n in top_cols)
    srcs_str = "、".join(f"{c}" for c, n in top_srcs)
    dates = list(stats["by_date"].keys())
    peak_count = max(stats["by_date"].values()) if stats["by_date"] else 0
    bc = stats["body_coverage"]
    img_cov = stats["image_coverage"]
    overview = (
        f"\u672c\u6708\u5171\u5f52\u6863432{f'{total}\u6761'}, "
        f"\u805a\u7126\u5728 {cols_str}\u3002"
        f"\u4e3b\u8981\u4fe1\u6e90\uff1a{srcs_str}\u3002"
    )
    trend = (
        f"\u65e5\u8d8b\u52bf\u5cf0\u503c {peak_count}\u6761/{dates[-1] if dates else ''}, "
        f"body\u8986\u76d6\u7387 {bc.get('extracted',0)}/{total}, "
        f"image\u4e0b\u8f7d {img_cov.get('downloaded',0)}\u5f20\u3002"
    )
    return f"{overview}\n\n{trend}\n\n\u26a0 \u672c\u671f\u4f7f\u7528\u89c4\u5219\u6a21\u677f\uff08LLM\u672a\u542f\u7528\u6216\u5931\u8d25\uff09"


def render_markdown(month, stats, picks, overview):
    lines = [f"# \u6bcf\u65e5\u65b0\u4e2d\u56fd \xb7 \u6708\u62a5 \xb7 {month}", ""]
    if overview:
        lines.append(overview)
        lines.append("")
    lines.append("## \u6708\u5ea6\u7edf\u8ba1")
    lines.append(f"- \u5f52\u6863\u603b\u6570: {stats['total_records']}")
    lines.append(f"- \u680f\u76ee\u5206\u5e03: {', '.join(f'{c}{n}' for c,n in list(stats['by_column'].items())[:5])}")
    lines.append(f"- \u4fe1\u6e90\u5206\u5e03: {', '.join(f'{c}{n}' for c,n in list(stats['by_source'].items())[:3])}")
    bc = stats['body_coverage']
    lines.append(f"- \u6b63\u6587: extracted={bc.get('extracted',0)} failed={bc.get('failed',0)} missing={bc.get('missing',0)}")
    lines.append("")
    for col in COLUMN_ORDER:
        if col not in picks:
            continue
        items = picks[col]
        lines.append(f"## {col}")
        for r in items:
            title = r.get("title", "")
            url = r.get("url", "")
            src = r.get("source", "")
            date = (r.get("date", "") or "")[:10]
            body = (r.get("body", "") or "")[:200]
            ipath = r.get("image_path", "")
            img = f" \U0001f5bc {ipath}" if ipath else ""
            lines.append(f"- [{title}]({url}) \u2014 {src} \xb7 {date}{img}")
            if body:
                lines.append(f"  {body.replace(chr(10), ' ')}")
    for col in picks:
        if col in COLUMN_ORDER:
            continue
        items = picks[col]
        lines.append(f"## {col}")
        for r in items:
            lines.append(f"- [{r.get('title','')}]({r.get('url','')})")
    return "\n".join(lines)


def render_html(month, stats, picks, overview):
    md = render_markdown(month, stats, picks, overview)
    esc = html.escape(md.replace("\n", "<br>\n"))
    return f"""<!DOCTYPE html><html lang=zh-CN><meta charset=utf-8><title>\u6708\u62a5 {month}</title>
<body style="max-width:960px;margin:0 auto;background:#f5f3ee;padding:20px">
<div style=background:#fffdf8;padding:32px;border:1px solid #d8d2c4>
{esc}
</div></body></html>"""


def render_png(html_path, png_path):
    try:
        subprocess.run(
            ["/snap/bin/chromium", "--headless", "--no-sandbox",
             f"--screenshot={png_path}", "--window-size=1280,2000",
             f"file://{html_path}"],
            timeout=60, check=True,
        )
    except Exception:
        return False
    if Image and ImageChops and png_path.exists():
        try:
            img = Image.open(png_path)
            bg = Image.new(img.mode, img.size, (255, 255, 255))
            diff = ImageChops.difference(img, bg)
            bbox = diff.getbbox()
            if bbox:
                img.crop(bbox).save(png_path)
        except Exception:
            pass
    return True


def write_outputs(month, md, html_content, stats, picks, dry_run):
    month_dir = MONTHLY_DIR / month
    if dry_run:
        print(f"  [dry-run] \u76ee\u6807\u76ee\u5f55: {month_dir}")
        print(f"  [dry-run] \u5c06\u5199: {month}_\u6708\u62a5.md / {month}_\u6708\u62a5.html / {month}_\u6708\u62a5.png / {month}_\u7edf\u8ba1.json")
        return True
    month_dir.mkdir(parents=True, exist_ok=True)
    md_path = month_dir / f"{month}_\u6708\u62a5.md"
    md_path.write_text(md, encoding="utf-8")
    html_path = month_dir / f"{month}_\u6708\u62a5.html"
    html_path.write_text(html_content, encoding="utf-8")
    stats_path = month_dir / f"{month}_\u7edf\u8ba1.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    png_path = month_dir / f"{month}_\u6708\u62a5.png"
    ok = render_png(html_path, png_path)
    if not ok:
        print("\u26a0 chromium\u622a\u56fe\u5931\u8d25\uff0c\u5176\u4ed6\u4e09\u4ef6\u5957\u5df2\u751f\u6210")
        return False
    return True


def main():
    month, dry_run, no_llm, top_n, max_llm_sec = parse_args()
    records = load_month_jsonl(month)
    records = [normalize_record(r) for r in records]
    stats = compute_stats(records, month)
    picks = pick_top_per_column(records, top_n)
    overview = None
    if not no_llm:
        ctx = build_grounding_context(stats, picks)
        raw = llm_monthly_overview(ctx, max_llm_sec)
        if raw:
            valid_ids = set()
            for items in picks.values():
                for r in items:
                    valid_ids.add(r.get("id", ""))
            overview = sanitize_llm_text(raw, valid_ids)
        if not overview:
            overview = fallback_overview(stats, picks)
    else:
        overview = fallback_overview(stats, picks)
    md = render_markdown(month, stats, picks, overview)
    html_content = render_html(month, stats, picks, overview)
    ok = write_outputs(month, md, html_content, stats, picks, dry_run)
    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
