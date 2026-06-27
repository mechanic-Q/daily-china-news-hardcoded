#!/usr/bin/env python3
import datetime
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None
    ImageChops = None

BASE_DIR = Path("/mnt/e/每日新中国")

COLUMN_ORDER = [
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

WEEKDAYS = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']


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


def parse_md(md_path):
    if not md_path.exists():
        print(f"❌ 文件不存在: {md_path}")
        return None
    content = md_path.read_text("utf-8")
    title_line = None
    sections = []
    current_heading = None
    current_title = None
    current_summary = []

    for line in content.splitlines():
        if title_line is None:
            m = re.match(r'^#\s+(.+)', line)
            if m:
                title_line = m.group(1).strip()
                continue
            if line.strip() and not line.startswith('#'):
                title_line = line.strip()
                continue
        m = re.match(r'^##\s+(.+)', line)
        if m:
            if current_title and current_summary:
                summary_text = '\n'.join(current_summary).strip()
                if '栏目留空' not in summary_text:
                    sections.append({
                        "heading": current_heading,
                        "title": current_title,
                        "summary": summary_text,
                    })
            current_heading = m.group(1).strip()
            current_title = None
            current_summary = []
            continue
        m = re.match(r'^###\s+(.+)', line)
        if m:
            if current_title and current_summary:
                summary_text = '\n'.join(current_summary).strip()
                if '栏目留空' not in summary_text:
                    sections.append({
                        "heading": current_heading,
                        "title": current_title,
                        "summary": summary_text,
                    })
            current_title = m.group(1).strip()
            current_summary = []
            continue
        if line.strip() and not line.startswith('#') and current_title:
            current_summary.append(line.strip())

    if current_title and current_summary:
        summary_text = '\n'.join(current_summary).strip()
        if '栏目留空' not in summary_text:
            sections.append({
                "heading": current_heading,
                "title": current_title,
                "summary": summary_text,
            })

    return title_line, sections


def _chinese_ordinal(n):
    if n <= 0:
        return str(n)
    units = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    if n <= 10:
        return '第' + units[n] + '期'
    if n <= 19:
        return '第十' + units[n - 10] + '期'
    if n <= 99:
        tens = n // 10
        ones = n % 10
        return '第' + units[tens] + '十' + (units[ones] if ones else '') + '期'
    return '第' + str(n) + '期'


def _compute_issue(target_date):
    start = datetime.date(2026, 4, 19)
    issue_num = (target_date - start).days + 1
    return _chinese_ordinal(issue_num)


def _format_weekday(d):
    return WEEKDAYS[d.weekday()]


def _estimate_weight(group):
    items = group.get("items", [])
    return sum(len(item.get("title", "")) + len(item.get("summary", "")) for item in items)


def balance_columns(sections):
    groups = {}
    for sec in sections:
        groups.setdefault(sec["heading"], []).append(sec)

    ordered = []
    for heading, items in groups.items():
        weight = _estimate_weight({"heading": heading, "items": items})
        ordered.append({"heading": heading, "items": items, "weight": weight})

    n = len(ordered)
    if n == 0:
        return [], []
    if n == 1:
        return [ordered[0]], []

    best_mask = 0
    best_diff = float("inf")

    for mask in range(1 << n):
        left_weight = 0
        right_weight = 0
        for i in range(n):
            if mask & (1 << i):
                right_weight += ordered[i]["weight"]
            else:
                left_weight += ordered[i]["weight"]
        diff = abs(left_weight - right_weight)
        if diff < best_diff:
            best_diff = diff
            best_mask = mask

    left = []
    right = []
    for i in range(n):
        if best_mask & (1 << i):
            right.append(ordered[i])
        else:
            left.append(ordered[i])

    return left, right


def esc(text):
    return html.escape(str(text), quote=True)


def build_html(target_date, sections, left_sections, right_sections):
    issue = _compute_issue(target_date)
    date_text = f"{target_date.year}年{target_date.month}月{target_date.day}日 {_format_weekday(target_date)}"

    def render_column(col_groups):
        html_parts = []
        for group in col_groups:
            items_html = ""
            for item in group["items"]:
                items_html += f'<li><strong>{esc(item["title"])}</strong> {esc(item["summary"])}</li>'
            html_parts.append(f'''<div class="section-card">
      <h2>{esc(group["heading"])}</h2>
      <ul>{items_html}</ul>
    </div>''')
        return "\n".join(html_parts)

    left_html = render_column(left_sections)
    right_html = render_column(right_sections)

    left_col = f'<div class="content-col col-left">\n{left_html}\n</div>' if left_html else ""
    right_col = f'<div class="content-col col-right">\n{right_html}\n</div>' if right_html else ""

    if left_html and right_html:
        story_main_html = f"""{left_col}
      <div class="col-divider"></div>
      {right_col}"""
        wrap_class = "story-wrap"
    elif left_html:
        story_main_html = f"""<div class="content-col single-col">\n{left_html}\n</div>"""
        wrap_class = "story-wrap single-col"
    else:
        story_main_html = f"""<div class="content-col single-col">\n{right_html}\n</div>"""
        wrap_class = "story-wrap single-col"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>每日新中国</title>
  <style>
    :root {{
      --paper: #f6f1e6;
      --ink: #141414;
      --muted: #5d5a53;
      --line: #1d1d1d;
      --soft-line: #c8beb0;
      --accent: #6f5a44;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: #ddd5c9; color: var(--ink); }}
    body {{
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
      display: flex;
      justify-content: center;
      padding: 32px 0;
    }}
    .page {{
      width: 1080px;
      background: var(--paper);
      padding: 0 32px 24px;
      position: relative;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      border-top: 6px solid var(--line);
      border-bottom: 2px solid var(--line);
      padding: 8px 0 5px;
      margin-bottom: 8px;
    }}
    .topbar-left {{ display: flex; flex-direction: column; gap: 2px; }}
    .paper-title {{
      font-size: 52px;
      font-weight: 900;
      letter-spacing: 2px;
      line-height: 1;
      color: var(--ink);
    }}
    .paper-tagline {{
      font-size: 30px;
      font-weight: 700;
      color: #c0392b;
      line-height: 1.2;
    }}
    .issue-date {{
      font-size: 18px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .story-wrap {{
      display: grid;
      grid-template-columns: 1fr 2px 1fr;
      gap: 0;
      position: relative;
    }}
    .story-wrap.single-col {{
      display: block;
    }}
    .content-col {{
      min-width: 0;
    }}
    .content-col.single-col {{
      max-width: 660px;
      margin: 0 auto;
    }}
    .col-divider {{
      background: var(--line);
      width: 2px;
    }}
    .section-card {{
      border-top: 2px solid var(--line);
      padding-top: 10px;
      margin-bottom: 18px;
    }}
    .section-card h2 {{
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.2;
      font-weight: 900;
      color: var(--ink);
    }}
    .section-card ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .section-card li {{
      font-size: 24px;
      line-height: 1.73;
      text-align: justify;
      padding-left: 32px;
      position: relative;
      margin-bottom: 10px;
    }}
    .section-card li::before {{
      content: "";
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: var(--ink);
      position: absolute;
      left: 4px;
      top: 8px;
    }}
    .footer {{
      margin-top: 10px;
      padding-top: 6px;
      border-top: 2px solid var(--line);
      font-size: 16px;
      color: #c0392b;
      display: flex;
      justify-content: space-between;
    }}
    .stamp {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}
    .stamp::before {{
      content: "";
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: var(--ink);
      display: inline-block;
    }}
  </style>
</head>
<body>
  <article class="page">
    <header class="topbar">
      <div class="topbar-left">
        <div class="paper-title">每日新中国</div>
        <div class="paper-tagline">中国很大 我想去看看</div>
      </div>
      <div class="issue-date">{esc(date_text)} {esc(issue)}</div>
    </header>

    <div class="{wrap_class}">
      {story_main_html}
    </div>

    <footer class="footer">
      <div>来源：新华社/央视新闻 ｜ 每日新中国出品</div>
      <div class="stamp">Mobile Brief</div>
    </footer>
  </article>
</body>
</html>"""


def crop_bottom_whitespace(png_path):
    if Image is None or ImageChops is None:
        return False, "Pillow unavailable"
    try:
        img = Image.open(png_path).convert("RGB")
        bg = Image.new("RGB", img.size, img.getpixel((0, img.height - 1)))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if not bbox:
            return False, "image is empty"
        left, top, right, bottom = bbox
        pad = 24
        crop_box = (
            max(0, left - pad),
            max(0, top - pad),
            min(img.width, right + pad),
            min(img.height, bottom + pad),
        )
        cropped = img.crop(crop_box)
        cropped.save(png_path)
        return True, f"cropped to {cropped.size[0]}x{cropped.size[1]}"
    except Exception as exc:
        return False, str(exc)


def screenshot_and_crop(html_path, png_path):
    file_url = html_path.resolve().as_uri()
    chromium = "/snap/bin/chromium"
    if not Path(chromium).exists():
        print("  ⚠ chromium not found at /snap/bin/chromium")
        return False

    cmd = [
        chromium,
        "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size=2160,10000",
        f"--screenshot={str(png_path.resolve())}",
        file_url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and png_path.exists():
            cropped_ok, crop_msg = crop_bottom_whitespace(png_path)
            if cropped_ok:
                print(f"  ✅ 截图已裁白边: {crop_msg}")
            else:
                print(f"  ℹ️  截图未裁白边: {crop_msg}")
            return True
        print(f"  ⚠ 截图失败: {(proc.stderr or proc.stdout or 'unknown error').strip()[:200]}")
        return False
    except subprocess.TimeoutExpired:
        print("  ⚠ 截图超时 (120s)")
        return False
    except Exception as e:
        print(f"  ⚠ 截图异常: {e}")
        return False


def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")
    issue = _compute_issue(today)
    input_path = BASE_DIR / today_str / "3新闻_概述.md"
    html_path = BASE_DIR / today_str / f"{today_str}_每日新中国_{issue}.html"
    png_path = BASE_DIR / today_str / f"{today_str}_每日新中国_{issue}.png"

    print(f"═══ Step 8: 报纸渲染 ═══")
    print(f"日期: {today_str}\n")

    parsed = parse_md(input_path)
    if parsed is None:
        return
    title_line, sections = parsed

    print(f"解析到 {len(sections)} 条新闻")
    for s in sections:
        print(f"  [{s['heading']}] {s['title'][:40]}")

    left_col, right_col = balance_columns(sections)
    left_count = sum(len(g["items"]) for g in left_col)
    right_count = sum(len(g["items"]) for g in right_col)
    print(f"\n左右栏分配: 左{len(left_col)}栏目/{left_count}条 → 右{len(right_col)}栏目/{right_count}条")

    html_content = build_html(today, sections, left_col, right_col)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_content, encoding="utf-8")
    print(f"\n✅ HTML: {html_path} ({html_path.stat().st_size} bytes)")

    if dry_run:
        print(f"\n  --dry-run: HTML 已写入，截图已跳过")
        return

    print(f"\n◆ 正在截图...")
    ok = screenshot_and_crop(html_path, png_path)
    if ok:
        size = png_path.stat().st_size
        print(f"✅ PNG: {png_path} ({size} bytes)")
    else:
        print(f"⚠ PNG: 截图未生成，HTML 可用")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
