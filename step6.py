#!/usr/bin/env python3
"""
Step 6: 正文提取 — 从 1新闻_链接.md 提取正文，生成 2新闻_已审核.md
支持多策略提取和信源分流（urllib/chromium）

用法:
    python3 step6.py                      # 处理今天
    python3 step6.py --date 2026-05-10     # 处理指定日期
    python3 step6.py --dry-run              # 预览，不写文件
"""

import datetime
import re
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path("/mnt/e/每日新中国")
CHROMIUM = "/snap/bin/chromium"
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


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


def chromium_dom(url, timeout=35, budget=20000):
    r = subprocess.run(
        [CHROMIUM, "--headless=new", "--disable-gpu",
         f"--virtual-time-budget={budget}", "--dump-dom", url],
        capture_output=True, text=True, timeout=timeout
    )
    return r.stdout


def fetch_html_static(url):
    """urllib 获取页面 HTML"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=12, context=ssl_ctx).read().decode("utf-8", errors="replace")


def extract_body(html, url):
    """多策略正文提取"""

    # 策略1: TRS_Editor（人民日报、中科院、部分新华社）
    m = re.search(r'<div[^>]*class=["\']TRS_Editor["\'][^>]*>(.*?)</div>', html, re.I | re.S)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 100:
            return text[:2000]

    # 策略2: article 或常见内容容器
    for pat in [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class=["\']article-content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']detail["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']main-content["\'][^>]*>(.*?)</div>',
    ]:
        m = re.search(pat, html, re.I | re.S)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1))
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 100:
                return text[:2000]

    # 策略3: 参考消息关键词定位（正文不在 <p> 标签中）
    if 'ckxxapp' in url or 'cankaoxiaoxi' in url:
        for kw in ['据美国《', '据路透社', '据法新社', '据新华社', '报道称', '北京']:
            idx = html.find(kw)
            if idx > 0:
                end = html.find('责任编辑', idx) if '责任编辑' in html[idx:] else idx + 5000
                snippet = html[idx:end] if end > 0 else html[idx:idx + 5000]
                text = re.sub(r'<[^>]+>', ' ', snippet)
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 200:
                    return text[:2000]

    # 策略4: 通用 <p> 标签兜底
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.I | re.S)
    valid = [re.sub(r'<[^>]+>', '', p).strip() for p in paras
             if len(re.sub(r'<[^>]+>', '', p).strip()) > 20]
    if valid:
        return ' '.join(valid)[:2000]

    return None


def needs_chromium(url):
    """判断是否需要 chromium 渲染"""
    return any(k in url for k in [
        'cctv.com', 'military.cctv', 'cnnc.com.cn', 'news.cctv'])


def fetch_and_extract(url, title):
    """获取 URL 并提取正文"""
    try:
        if needs_chromium(url):
            html = chromium_dom(url, timeout=40, budget=30000)
        else:
            html = fetch_html_static(url)

        if not html or len(html) < 500:
            return None, "页面过短或为空"

        body = extract_body(html, url)
        if body:
            return body, None
        return None, "未找到正文区域"

    except Exception as e:
        return None, str(e)


def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "1新闻_链接.md"

    print(f"═══ Step 6: 正文提取 ═══")
    print(f"日期: {today_str}")
    print(f"数据: {input_path}\n")

    if not input_path.exists():
        print("❌ 1新闻_链接.md 不存在 — 请先运行 step4.py")
        return

    content = input_path.read_text("utf-8")
    articles = []
    for m in re.finditer(r'### \[(.*?)\] (.*?)\nURL：(https?://[^\s]+)', content):
        articles.append({'src': m.group(1), 'title': m.group(2), 'url': m.group(3)})

    print(f"共 {len(articles)} 条，提取正文中...\n")

    success = 0
    for a in articles:
        body, err = fetch_and_extract(a['url'], a['title'])
        a['body'] = body or f'[正文提取失败: {err or "未知错误"}]'
        status = '✅' if body else '❌'
        print(f"  {status} [{a['src']}] {a['title'][:40]}... ({len(a['body'])}字)")
        if body:
            success += 1

    print(f"\n成功: {success}/{len(articles)}")

    lines = [f"# {today_str} 新闻（已审核）\n"]
    for a in articles:
        lines.append(f"\n## 【{a['src']}】{a['title']}\n")
        lines.append(f"来源：{a['src']}  发布时间：{today_str}\n")
        lines.append(f"正文：{a['body']}\n")

    output_path = BASE_DIR / today_str / "2新闻_已审核.md"

    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        preview = "\n".join(lines)
        print(preview[:2000])
    else:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
