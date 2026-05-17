#!/usr/bin/env python3
"""
Step 6: 正文提取 — 从 1新闻_链接.md 提取正文，输出 2新闻_已审核.md
5 层策略链，静态源 urllib / 央视系 chromium 分流

用法:
    python3 step6.py                      # 处理今天
    python3 step6.py --date 2026-05-10     # 处理指定日期
    python3 step6.py --dry-run              # 预览，不写文件
"""

import datetime
import html
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

EXCLUDE_PARAS = ['copyright', 'icp', '京ICP', '沪ICP', '登录', '注册',
                 '央视网', '二维码', '责编', '责任编辑', '温馨提示']


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


def chromium_dom(url, timeout=45, budget=30000):
    r = subprocess.run(
        [CHROMIUM, "--headless=new", "--disable-gpu",
         f"--virtual-time-budget={budget}", "--dump-dom", url],
        capture_output=True, text=True, timeout=timeout)
    return r.stdout


def fetch_html_static(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=12, context=ssl_ctx).read().decode("utf-8", errors="replace")


def _preprocess_html(html):
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.S)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.I | re.S)
    return html


def extract_body(html, url):
    """5 层策略链正文提取"""
    html = _preprocess_html(html)

    m = re.search(r'<div[^>]*class=["\']TRS_Editor["\'][^>]*>(.*?)</div>', html, re.I | re.S)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 100:
            return text

    for pat in [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class=["\']article-content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']detail["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']main-content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*id=["\']ozoom["\'][^>]*>(.*?)</div>',
    ]:
        m = re.search(pat, html, re.I | re.S)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1))
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 100:
                return text

    if 'ckxxapp' in url or 'cankaoxiaoxi' in url:
        for kw in ['据美国《', '据路透社', '据法新社', '据新华社', '报道称', '北京']:
            idx = html.find(kw)
            if idx > 0:
                end = html.find('责任编辑', idx) if '责任编辑' in html[idx:] else idx + 5000
                snippet = html[idx:end] if end > 0 else html[idx:idx + 5000]
                text = re.sub(r'<[^>]+>', ' ', snippet)
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 200:
                    return text

    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.I | re.S)
    valid = []
    for p in paras:
        t = re.sub(r'<[^>]+>', '', p).strip()
        if len(t) > 20 and not any(k in t.lower() for k in EXCLUDE_PARAS):
            valid.append(t)
    if valid:
        return ' '.join(valid)

    return None


def needs_chromium(url):
    return any(k in url for k in ['cctv.com', 'military.cctv', 'cnnc.com.cn', 'news.cctv'])


def fetch_and_extract(url, title):
    try:
        if needs_chromium(url):
            html = chromium_dom(url)
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
        print("\n".join(lines)[:2000])
    else:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
