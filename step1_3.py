#!/usr/bin/env python3
"""
Step 1-3 硬编码版：《每日新中国》新闻采集 + 三淘汰验证
替代原 daily-china-news skill 的 AI 驱动采集流程。

用法:
    python3 step1_3.py                   # 采集今天
    python3 step1_3.py --date 2026-05-10  # 采集指定日期
    python3 step1_3.py --dry-run           # 预览，不写文件
"""

import asyncio
import aiohttp
import datetime
import re
import ssl
import subprocess
import sys
import json
import time
import urllib.request
from pathlib import Path

# ── 全局配置 ────────────────────────────────────────────
BASE_DIR = Path("/mnt/e/每日新中国")
CHROMIUM = "/snap/bin/chromium"  # snap chromium v147

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


# ============================================================
# Step 1+2: 日期确认 + 工作目录
# ============================================================

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
            print(f"错误: 日期格式无效: {date_str}，应为 YYYY-MM-DD")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry


def init(today):
    """Step 1: 日期确认 → Step 2: 建目录"""
    today_str = today.strftime("%Y-%m-%d")
    workdir = BASE_DIR / today_str
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"═══ Step 1+2 ═══")
    print(f"日期: {today_str}")
    print(f"目录: {workdir}")
    return today, workdir


# ============================================================
# 工具函数
# ============================================================

def chromium_dom(url, timeout=35, budget=20000):
    """chromium --dump-dom 获取页面 DOM"""
    r = subprocess.run(
        [CHROMIUM, "--headless=new", "--disable-gpu",
         f"--virtual-time-budget={budget}", "--dump-dom", url],
        capture_output=True, text=True, timeout=timeout
    )
    return r.stdout


def fetch_title(html):
    """从 HTML 提取标题 (h1 → og:title → title)"""
    for pat in [
        r'<h1[^>]*>(.*?)</h1>',
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        r'<title>(.*?)</title>',
    ]:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            t = re.sub(r'[-_|·].*(?:新华网|央视网|人民网|社科院|中科院).*$', '', t).strip()
            if t and len(t) > 4:
                return t
    return ""


def fetch_date_from_page(html, url=""):
    """从页面 HTML 提取发布日期"""
    patterns = [
        r'<meta[^>]+name=["\']PubDate["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']publishdate["\'][^>]+content=["\']([^"\']+)["\']',
        r'<span[^>]*>(\d{4}年\d{1,2}月\d{1,2}日)</span>',
        r'<span[^>]*class=["\'][^"\']*time[^"\']*["\'][^>]*>(\d{4}-\d{2}-\d{2})',
        r'"pubDate"\s*:\s*"([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y年%m月%d日"]:
                try:
                    return datetime.datetime.strptime(raw[:fmt.count('%') * 2 + 4], fmt).date()
                except ValueError:
                    continue
            m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})', raw)
            if m2:
                return datetime.date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    return None


def check_date_in_url(url, today):
    """检查 URL 中是否含今日日期（兜底：URL 日期匹配即通过）"""
    patterns = [
        today.strftime("%Y-%m-%d"),
        today.strftime("%Y/%m/%d"),
        today.strftime("%Y%m%d"),
        today.strftime("%Y%m/%d"),
    ]
    for p in patterns:
        if p in url:
            return True
    return False


def http_200(url):
    """单个 URL HTTP 检查"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=10, context=ssl_ctx).getcode() == 200
    except Exception:
        return False


async def http_200_async(session, url):
    """异步 HTTP 检查"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12), ssl=ssl_ctx) as r:
            return r.status == 200
    except Exception:
        return False


# ============================================================
# 7信源采集函数
# ============================================================

def fetch_xinhuanet(today):
    """新华社: chromium --dump-dom news.cn → 正则 YYYYMMDD/c.html"""
    today8 = today.strftime("%Y%m%d")
    html = chromium_dom("https://www.news.cn/", budget=25000)
    urls = list(dict.fromkeys(
        re.findall(rf'https?://[^"\'\s]*news\.cn/[^"\'\s]*/{today8}/[a-z0-9]+/c\.html', html)
    ))
    results = []
    for u in urls:
        t = fetch_title(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=10, context=ssl_ctx
        ).read().decode("utf-8", errors="replace"))
        if t:
            results.append({"url": u, "title": t})
    return results


def fetch_ckxx(today):
    """参考消息: urllib JSON API — 扫全部 9 个频道"""
    aliases = ['zhongguo','gj','junshi','kejiyy','wenhualy','diyiguanzhu','yaowen','ruick','guandian']
    ts = int(time.time() * 1000)
    seen = set()
    results = []
    today_str = today.strftime("%Y-%m-%d")

    for alias in aliases:
        url = f"https://china.cankaoxiaoxi.com/json/channel/{alias}/list.json?_t={ts}"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://china.cankaoxiaoxi.com/"
            })
            data = json.loads(urllib.request.urlopen(req, timeout=8, context=ssl_ctx).read())
        except Exception as e:
            print(f"    频道 {alias} 失败: {e}")
            continue

        for item in data.get("list", []):
            d = item.get("data", item) if isinstance(item, dict) else {}
            if not isinstance(d, dict):
                continue
            createtime = d.get("createtime", "")
            if not createtime.startswith(today_str):
                continue
            u = d.get("url", "")
            title = d.get("title", "")
            if not u or not title:
                continue
            key = u.split("/")[-1].split(".")[0]
            if key not in seen:
                seen.add(key)
                results.append({"url": u, "title": title})

    return results


def fetch_cctv_news(today):
    """央视新闻: chromium --dump-dom → 从首页 DOM 提取 (URL, title) 对"""
    today_path = today.strftime("%Y/%m/%d")
    html = chromium_dom("https://news.cctv.com/", budget=20000)
    links = re.findall(r'href=["\']([^"\']+)["\']>([^<]{8,60})<', html)
    results = []
    seen = set()
    for l, t_raw in links:
        if "news.cctv.com" not in l or today_path not in l or ".shtml" not in l:
            continue
        u = l if l.startswith("http") else f"https:{l}" if l.startswith("//") else f"https://news.cctv.com{l}"
        if u in seen:
            continue
        seen.add(u)
        t = t_raw.strip()
        if t and len(t) > 4:
            results.append({"url": u, "title": t})
    return results


def fetch_cctv_military(today):
    """央视军事: chromium --dump-dom → 从首页 DOM 提取 (URL, title) 对"""
    today_path = today.strftime("%Y/%m/%d")
    html = chromium_dom("https://military.cctv.com/", budget=15000)
    links = re.findall(r'href=["\']([^"\']+)["\']>([^<]{8,60})<', html)
    results = []
    seen = set()
    for l, t_raw in links:
        if "military.cctv.com" not in l or today_path not in l or ".shtml" not in l:
            continue
        u = l if l.startswith("http") else f"https:{l}" if l.startswith("//") else f"https://military.cctv.com{l}"
        if u in seen:
            continue
        seen.add(u)
        t = t_raw.strip()
        if t and len(t) > 4:
            results.append({"url": u, "title": t})
    return results


def fetch_cas(today):
    """中科院: urllib 首页 → 匹配 YYYYMM 前缀（兼容 tYYYYMMDD_* 和 /YYYYMM/ 格式）"""
    req = urllib.request.Request("https://www.cas.cn/", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15, context=ssl_ctx).read().decode("utf-8", errors="replace")
    # 匹配 //www.cas.cn/../../ 后的所有含 YYYYMM 前缀的链接
    yyyymm = today.strftime("%Y%m")
    raw_urls = re.findall(rf'//www\.cas\.cn/\.\./\.\./([^"\'\s]*{yyyymm}[^"\'\s]*\.shtml)', html)
    results = []
    seen = set()
    for raw in raw_urls:
        parts = [p for p in raw.split("/") if p and p != ".."]
        u = f"https://www.cas.cn/{'/'.join(parts)}"
        if u in seen:
            continue
        seen.add(u)
        t = fetch_title(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=10, context=ssl_ctx
        ).read().decode("utf-8", errors="replace"))
        if t:
            results.append({"url": u, "title": t})
    return results


def fetch_cnnc_chromium(today):
    """中核集团 → 方案1: chromium --dump-dom cnnc.com.cn"""
    today8 = today.strftime("%Y%m%d")
    html = chromium_dom("https://www.cnnc.com.cn/", budget=25000)
    links_titles = re.findall(
        r'<a[^>]+href=["\']([^"\']*cnnc[^"\']*202[56]\d{4}[^"\']*)["\'][^>]*>([^<]{4,60})<',
        html
    )
    results = []
    for href, title in links_titles[:8]:
        t = title.strip()
        if t and len(t) > 3:
            u = href if href.startswith("http") else f"https://www.cnnc.com.cn{href}"
            results.append({"url": u, "title": t})
    return results


def fetch_cnnc_cnnpn(today):
    """中核集团 → 方案2: cnnpn.cn 聚合站（CF 绕过）"""
    html = chromium_dom("https://www.cnnpn.cn/", budget=20000)
    today_str = today.strftime("%Y-%m-%d")
    # 提取文章链接
    links = re.findall(r'href=["\']([^"\']*cnnpn\.cn[^"\']*article[^"\']*)["\']', html)
    links = list(dict.fromkeys(links))
    results = []
    for l in links[:8]:
        u = l if l.startswith("http") else f"https://www.cnnpn.cn{l}" if l.startswith("/") else f"https://www.cnnpn.cn/{l}"
        try:
            h = urllib.request.urlopen(
                urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=10, context=ssl_ctx
            ).read().decode("utf-8", errors="replace")
            t = fetch_title(h)
            if t and len(t) > 4:
                results.append({"url": u, "title": t})
        except Exception:
            continue
    return results


def fetch_cnnc(today):
    """中核集团: 三级降级链
    ① chromium --dump-dom cnnc.com.cn
    ② cnnpn.cn 聚合站（CF 绕过）
    ③ 不可达
    """
    items = fetch_cnnc_chromium(today)
    if items:
        return items, "chromium --dump-dom cnnc.com.cn"

    items = fetch_cnnc_cnnpn(today)
    if items:
        return items, "cnnpn.cn 聚合站"

    return [], "技术不可达"


def fetch_rmrb(today):
    """人民日报: urllib 版面索引 → content_*.html"""
    results = []
    seen = set()
    for node in range(1, 10):
        layout_url = f"https://paper.people.com.cn/rmrb/pc/layout/{today.strftime('%Y%m')}/{today.strftime('%d')}/node_{node:02d}.html"
        try:
            req = urllib.request.Request(layout_url, headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(req, timeout=10, context=ssl_ctx).read().decode("utf-8", errors="replace")
        except Exception:
            continue
        hrefs = re.findall(r'href=["\']([^"\']*content_\d+\.html)["\']', html)
        for raw in hrefs:
            filename = raw.split("/")[-1]
            u = f"https://paper.people.com.cn/rmrb/pc/content/{today.strftime('%Y%m')}/{today.strftime('%d')}/{filename}"
            if u in seen:
                continue
            seen.add(u)
            try:
                h = urllib.request.urlopen(
                    urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                    timeout=10, context=ssl_ctx
                ).read().decode("utf-8", errors="replace")
                t = fetch_title(h)
                if t:
                    results.append({"url": u, "title": t})
            except Exception:
                continue
    return results


# ============================================================
# 三淘汰验证 + aiohttp 并发
# ============================================================

def _check_title_date_match(item, html, today):
    """检查标题和日期是否匹配，返回 (通过?, 失败原因)"""
    h1 = fetch_title(html)
    page_date = fetch_date_from_page(html, item["url"])
    date_ok = (page_date == today) or check_date_in_url(item["url"], today)
    title_ok = h1 and any(kw in h1 for kw in item["title"][:10].split("|")[0].split()[:3] if len(kw) > 1)
    if title_ok and date_ok:
        return True, ""
    reason = []
    if not title_ok:
        reason.append(f"h1不匹配({h1[:30] if h1 else '无h1'})")
    if not date_ok:
        reason.append(f"日期不符({page_date})")
    return False, " | ".join(reason) or "未知"


async def _fetch_and_check(session, item, today):
    """并发获取 URL 并检查标题/日期"""
    try:
        async with session.get(item["url"], timeout=aiohttp.ClientTimeout(total=12), ssl=ssl_ctx) as r:
            if r.status != 200:
                return "fail", {"item": item, "reason": "HTTP非200"}
            html = await r.text()
    except Exception as e:
        return "fail", {"item": item, "reason": f"HTTP异常: {e}"}

    ok, reason = _check_title_date_match(item, html, today)
    if ok:
        return "pass", item
    return "fail", {"item": item, "reason": reason}


async def verify_static_source(name, items, today):
    """对静态源用 aiohttp 并发获取 + 标题/日期检查"""
    if not items:
        return [], [], []

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=30)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_and_check(session, it, today) for it in items]
        results = await asyncio.gather(*tasks)

    passed, failed = [], []
    for status, data in results:
        if status == "pass":
            passed.append(data)
        else:
            failed.append(data)

    return passed, failed, []


def verify_js_source(items, today):
    """对 JS 渲染源逐条 chromium 验证（央视系）"""
    if not items:
        return [], [], []

    passed, failed = [], []
    for item in items:
        try:
            html = chromium_dom(item["url"], timeout=40, budget=25000)
            if not html or len(html) < 500:
                failed.append({"item": item, "reason": "chromium 返回空或过短"})
                continue
            ok, reason = _check_title_date_match(item, html, today)
            if ok:
                passed.append(item)
            else:
                failed.append({"item": item, "reason": reason})
        except Exception as e:
            failed.append({"item": item, "reason": f"验证异常: {e}"})

    return passed, failed, []


async def verify_api_source(items, today):
    """对 API 信源只验 HTTP 200（API 已提供结构化数据，无需 h1/日期验证）"""
    if not items:
        return [], [], []

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=30)
    async with aiohttp.ClientSession(connector=connector) as session:
        urls = [it["url"] for it in items]
        statuses = await asyncio.gather(*[http_200_async(session, u) for u in urls])

    passed, failed = [], []
    for item, ok in zip(items, statuses):
        if ok:
            passed.append(item)
        else:
            failed.append({"item": item, "reason": "HTTP非200"})

    return passed, failed, []


def verify_cnnc_source(items, today):
    """中核集团: 用 chromium 验证（CF 保护需要浏览器级访问）"""
    if not items:
        return [], [], []

    passed, failed = [], []
    for item in items:
        try:
            html = chromium_dom(item["url"], timeout=40, budget=25000)
            if not html or len(html) < 500:
                failed.append({"item": item, "reason": "chromium 返回空或过短"})
                continue
            url_has_date = any(p in item["url"] for p in [
                today.strftime("%Y%m%d"), today.strftime("%Y-%m-%d"),
            ])
            if url_has_date:
                passed.append(item)
            else:
                failed.append({"item": item, "reason": "日期不匹配"})
        except Exception as e:
            failed.append({"item": item, "reason": f"验证异常: {e}"})

    return passed, failed, []


# ============================================================
# 输出
# ============================================================

def write_0(today, entries, dry_run):
    """写入 0新闻_粗筛.md"""
    output_path = BASE_DIR / today.strftime("%Y-%m-%d") / "0新闻_粗筛.md"
    today_str = today.strftime("%Y-%m-%d")

    lines = [f"# {today_str} 新闻候选（粗筛）\n"]

    for entry in entries:
        name = entry["source"]
        passed = entry["passed"]
        failed = entry["failed"]
        total = len(passed) + len(failed)
        tool = entry.get("tool", "")

        if not passed and total > 0:
            # 所有条目都被过滤（通常是日期不匹配）
            all_date_filtered = all("日期" in f.get("reason", "") for f in failed)
            if all_date_filtered:
                status = "✅通过（今日无可用文章）"
            else:
                status = "❌失败"
        elif total > 1 or (total == 1 and passed):
            status = "✅通过"
        else:
            status = "❌失败"

        lines.append(f"## {name}（通过{len(passed)}条 / 淘汰{len(failed)}条 / 汇总{total}条 → {status}）")
        lines.append(f"工具: {tool}")

        for item in passed:
            t = item["title"].replace("\n", " ")[:80]
            lines.append(f"- [{today_str}] {t} | {item['url']} ✅")

        for f_item in failed:
            it = f_item["item"]
            t = it["title"].replace("\n", " ")[:60]
            lines.append(f"（淘汰）{t} | {it['url']} | {f_item['reason']}")

        if not passed and not failed:
            lines.append("（技术不可达）")

        lines.append("")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print(content[:3000])
    else:
        output_path.write_text(content, encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")
    return len([e for e in entries if e["passed"]])


# ============================================================
# 主流程
# ============================================================

# 7信源定义: (名称, fetcher, 工具名, 验证方式, multi_return)
SOURCES = [
    ("新华社",    fetch_xinhuanet,    "chromium --dump-dom news.cn", "static", False),
    ("参考消息",  fetch_ckxx,         "urllib JSON API",              "api",   False),
    ("央视新闻",  fetch_cctv_news,    "chromium --dump-dom cctv",     "js",    False),
    ("央视军事",  fetch_cctv_military,"chromium --dump-dom military", "js",    False),
    ("中科院",    fetch_cas,          "urllib cas.cn",                "static", False),
    ("中核集团",  fetch_cnnc,         "降级链",                       "cnnc",   True),
    ("人民日报",  fetch_rmrb,         "urllib 版面索引",              "static", False),
]

def main():
    today, dry_run = parse_args()
    today, workdir = init(today)
    today_str = today.strftime("%Y-%m-%d")

    print(f"\n═══ Step 3: 7信源采集 + 三淘汰验证 ═══\n")

    all_entries = []

    for i, (name, fetcher, tool, verify_type, multi_return) in enumerate(SOURCES, 1):
        print(f"[{i}/7] {name}...", end=" ", flush=True)

        try:
            # ① 采集
            if multi_return:
                items, tool = fetcher(today)
            else:
                items = fetcher(today)

            if not items:
                print(f"→ 0条 → ❌失败")
                all_entries.append({
                    "source": name, "passed": [], "failed": [], "tool": tool
                })
                continue

            print(f"→ {len(items)}条")

            # ② 三淘汰验证
            if verify_type == "js":
                passed, failed, _ = verify_js_source(items, today)
            elif verify_type == "api":
                passed, failed, _ = asyncio.run(verify_api_source(items, today))
            elif verify_type == "cnnc":
                passed, failed, _ = verify_cnnc_source(items, today)
            else:
                passed, failed, _ = asyncio.run(verify_static_source(name, items, today))

            print(f"    ✅{len(passed)} / ❌{len(failed)}")

            all_entries.append({
                "source": name, "passed": passed, "failed": failed, "tool": tool
            })

        except Exception as e:
            print(f"❌ 异常: {e}")
            all_entries.append({
                "source": name, "passed": [], "failed": [], "tool": tool
            })

    # ③ 写入
    passed_count = write_0(today, all_entries, dry_run)

    # 汇总
    print(f"\n═══ 汇总 ═══")
    for entry in all_entries:
        p = len(entry["passed"])
        f = len(entry["failed"])
        if p > 0:
            print(f"  ✅ {entry['source']}: {p}条通过")
        elif f > 0 and all("日期" in r.get("reason", "") for r in entry["failed"]):
            print(f"  ✅ {entry['source']}: 工具通（今日无新稿）")
        elif p == 0 and f > 0:
            print(f"  ⚠ {entry['source']}: {p}条通过, {f}条淘汰")
        else:
            print(f"  ❌ {entry['source']}: 不可达")

    print(f"\n产出: {passed_count}/7 信源有通过条目")
    if dry_run:
        print("模式: --dry-run (未写文件)")
    else:
        print(f"文件: {workdir / '0新闻_粗筛.md'}")


if __name__ == "__main__":
    main()
