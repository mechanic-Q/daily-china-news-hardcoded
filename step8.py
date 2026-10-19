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
from daily.common import BASE_DIR, COLUMN_ORDER, WEEKDAYS, parse_common_args as parse_args
from daily.http import CHROMIUM

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None
    ImageChops = None


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


# build_html 里 html/body 的 background —— 改页面样式需同步这里
BODY_BG = (0xDD, 0xD5, 0xC9)


def crop_bottom_whitespace(png_path):
    if Image is None or ImageChops is None:
        return False, "Pillow unavailable"
    try:
        img = Image.open(png_path).convert("RGB")
        # 背景色是自家 HTML 的已知常量, 按容差比对全图找内容包围盒。
        # 旧实现采样左下角单像素当背景色: 该像素被任何 1px 渲染毛边污染时,
        # 裁剪随机失效(输出整图 4320x20000, 见 10-11/10-13)或过裁(10-12 的 392px 条)。
        diff = ImageChops.difference(img, Image.new("RGB", img.size, BODY_BG))
        bbox = diff.point(lambda p: 255 if p > 6 else 0).getbbox()
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


# 截图窗口与缩放：整窗高度 = 这些值相乘。裁剪后若高度仍等于整窗高度，
# 说明内容包围盒就是整图（裁剪失效），不能当成合格产物（10-02/10-06/10-11/10-19 实录）。
SCREENSHOT_WIDTH = 2160
SCREENSHOT_HEIGHT = 10000
SCREENSHOT_SCALE = 2
# chromium 进程退出与文件落盘不是原子的：进程先退出、--screenshot 的结果
# 随后才写完（10-19 实录：进程 0.5s 内返回，文件 4s 后才落盘）。退出后必须
# 轮询等待文件真正稳定，否则会把「还在写」误判成「没生成」。
SCREENSHOT_WAIT_SECONDS = 30.0
SCREENSHOT_SETTLE_SECONDS = 0.3


def _wait_for_screenshot(png_path, deadline):
    """等 --screenshot 落盘并写稳。返回 True 表示拿到了稳定的非空文件。

    chromium 退出码并不代表截图成功，文件存在也不代表写完，所以判据只能是
    「文件存在 + 大小 > 0 + 大小在 SETTLE 窗口内不再变化」。
    """
    last_size = -1
    stable_since = None
    while time.time() < deadline:
        try:
            size = png_path.stat().st_size
        except FileNotFoundError:
            last_size, stable_since = -1, None
            time.sleep(0.1)
            continue
        if size > 0 and size == last_size:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= SCREENSHOT_SETTLE_SECONDS:
                return True
        else:
            stable_since = None
        last_size = size
        time.sleep(0.1)
    return False


def screenshot_and_crop(html_path, png_path):
    file_url = html_path.resolve().as_uri()
    chromium = CHROMIUM
    if not Path(chromium).exists():
        print(f"  ⚠ chromium not found at {CHROMIUM}")
        return False

    base_cmd = [
        chromium,
        "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--force-device-scale-factor={SCREENSHOT_SCALE}",
        f"--window-size={SCREENSHOT_WIDTH},{SCREENSHOT_HEIGHT}",
        f"--screenshot={str(png_path.resolve())}",
        file_url,
    ]
    # 尝试1 带 virtual-time-budget (等渲染/字体就绪, 防半渲染截图);
    # 尝试2 不带 —— 该 flag 偶发让 chrome 写完文件后不退出 (2026-10-13 15:52 实测
    # 撞 120s 超时: 文件已落盘, 裁剪却被跳过, 输出 4320x20000 整图)。
    attempts = [base_cmd + ["--virtual-time-budget=10000"], base_cmd]
    try:
        png_path.unlink()   # 防上一轮残留文件被误当本轮产物
    except FileNotFoundError:
        pass
    proc, timed_out = None, False
    for i, cmd in enumerate(attempts, 1):
        started = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            proc, timed_out = None, True
        # 退出 ≠ 落盘：等文件写稳再判断，别把「还在写」当成「没生成」
        if _wait_for_screenshot(png_path, time.time() + SCREENSHOT_WAIT_SECONDS):
            if timed_out:
                print("  ℹ chromium 120s 未退出, 但截图文件已写出, 继续裁剪")
            elif proc is not None and proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()[:200]
                print(f"  ℹ chromium 退出码 {proc.returncode}, 截图已生成{'; ' + err if err else ''}")
            break
        waited = time.time() - started
        print(f"  ⚠ 截图第 {i} 次未生成 (等待 {waited:.1f}s)" + ("，重试..." if i < len(attempts) else ""))
    else:
        print("  ⚠ 截图失败: 两次尝试均未产出文件")
        return False

    cropped_ok, crop_msg = crop_bottom_whitespace(png_path)
    if not cropped_ok:
        print(f"  ⚠ 截图失败: 裁剪未生效 ({crop_msg})，不产出未裁剪图")
        try:
            png_path.unlink()
        except FileNotFoundError:
            pass
        return False

    print(f"  ✅ 截图已裁白边: {crop_msg}")
    with Image.open(png_path) as _im:
        width, cropped_h = _im.size
    full_h = SCREENSHOT_HEIGHT * SCREENSHOT_SCALE
    if cropped_h >= full_h:
        # 包围盒 = 整图 → 裁剪形同虚设，产物是一张 4320x20000 的整窗图
        print(f"  ⚠ 截图失败: 裁剪后仍是整窗高度 {width}x{cropped_h}，裁剪未生效")
        try:
            png_path.unlink()
        except FileNotFoundError:
            pass
        return False
    if cropped_h < 1200:
        print(f"  ⚠ 裁剪后高度 {cropped_h}px 异常偏小, 截图可能不完整 (HTML 可用)")
    return True


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
