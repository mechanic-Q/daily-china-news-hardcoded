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

    # Layer 1: TRS_Editor (safe to strip script/style — content in normal HTML)
    html_clean = _preprocess_html(html)
    m = re.search(r'<div[^>]*class=["\']TRS_Editor["\'][^>]*>(.*?)</div>', html_clean, re.I | re.S)
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
        m = re.search(pat, html_clean, re.I | re.S)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1))
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 100:
                return text

    if 'ckxxapp' in url or 'cankaoxiaoxi' in url:
        for kw in ['据美国《', '据路透社', '据法新社', '据新华社', '报道称', '北京']:
            idx = html.find(kw)
            if idx > 0:
                end = idx + 200
                for marker in ['责任编辑', '";', '编译/']:
                    pos = html[idx:].find(marker)
                    if pos > -1:
                        cand = idx + pos + len(marker)
                        if cand > end:
                            end = cand
                snippet = html[idx:end] if end > 0 else html[idx:idx + 5000]
                text = re.sub(r'<[^>]+>', ' ', snippet)
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 200:
                    return text

    paras = re.findall(r'<p[^>]*>(.*?)</p>', html_clean, re.I | re.S)
    valid = []
    for p in paras:
        t = re.sub(r'<[^>]+>', '', p).strip()
        if len(t) > 20 and not any(k in t.lower() for k in EXCLUDE_PARAS):
            valid.append(t)
    if valid:
        return ' '.join(valid)

    return None


def _postprocess_text(text):
    text = html.unescape(text)
    text = re.sub(r'\[!--begin:htmlVideoCode--\].*?\[!--end:htmlVideoCode--\]', '', text, flags=re.S)
    ui_pats = [
        r'静音\(m\)', r'全屏\(f\)',
        r'ADCountdown\s*(Time|时间)?', r'广告关闭广告',
        r'正在加载[\s\S]*?视频播放器', r'播放视频播放\([pP]\)',
        r'播放\([pP]\)', r'当前时间[\s\S]*?时长[\s\S]*?\d+:\d+',
        r'媒体流类型[\s\S]*?高清', r'高清画质超清高清',
        r'加载完成:\s*\d+%-?\d*:\d*',
        r'您上次观看至[\s\S]*?已为您续播',
        r'尊贵的用户[\s\S]*?跳过广告',
    ]
    for pat in ui_pats:
        text = re.sub(pat, '', text, flags=re.S)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    parts = re.split(r'(?<=[。；])', text)
    deduped = []
    for s in parts:
        s_stripped = s.strip()
        if s_stripped and (not deduped or s_stripped != deduped[-1].strip()):
            deduped.append(s)
    return ''.join(deduped)


def _is_contaminated(text):
    css_signals = ['font-family', 'margin:', 'padding:', 'line-height:', 'border-spacing']
    js_signals = ['var ih =', 'var p =', 'document.getElementById', 'console.log']
    for s in css_signals:
        if s in text:
            return True
    for s in js_signals:
        if s in text:
            return True
    nav_kws = ['日报', '周报', '杂志']
    if all(kw in text for kw in nav_kws):
        positions = [text.index(kw) for kw in nav_kws]
        if max(positions) - min(positions) < 100:
            return True
    return False


def _aggressive_clean(html, url=None):
    if url and ('ckxxapp' in url or 'cankaoxiaoxi' in url):
        return html
    html = _preprocess_html(html)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'\sstyle="[^"]*"', '', html, flags=re.I)
    return html


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
            processed = _postprocess_text(body)
            if _is_contaminated(processed):
                cleaned_html = _aggressive_clean(html)
                body2 = extract_body(cleaned_html, url)
                if body2:
                    processed2 = _postprocess_text(body2)
                    if not _is_contaminated(processed2):
                        return processed2, None
                return None, "提取结果被污染"
            return processed, None
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
