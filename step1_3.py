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
import html as html_lib
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

from daily.common import BASE_DIR, parse_common_args as parse_args
from daily.http import CHROMIUM, ssl_ctx, fetch_html_static, chromium_dom

import httpx
import tenacity
from tenacity import stop_after_attempt, wait_exponential, wait_random

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))

HEALTH_FILE = BASE_DIR / "archive" / "sources_health.jsonl"


@dataclass
class HealthRecord:
    date: str
    source: str
    passed: int
    failed: int
    total: int
    tool: str
    elapsed_ms: int
    status: str
    recorded_at: str


def write_health_record(record, dry_run=False):
    """Best-effort 写入一条 health JSONL 记录。"""
    try:
        HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(record) if hasattr(record, '__dataclass_fields__') else record, ensure_ascii=False)
        if dry_run:
            print(f"  [dry-run] would-write health: {line}")
        else:
            with open(HEALTH_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        logger.warning("写入 health 记录失败: %s", e)


def _read_recent_health(source, today_str, days=7):
    """读取 HEALTH_FILE 最近 N 天同 source 记录，失败返回空列表。"""
    try:
        if not HEALTH_FILE.exists():
            return []
        records = []
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("source") != source:
                    continue
                rec_date = rec.get("date", "")
                if not rec_date or rec_date > today_str:
                    continue
                td = datetime.strptime(today_str, "%Y-%m-%d").date()
                rd = datetime.strptime(rec_date, "%Y-%m-%d").date()
                if (td - rd).days >= days:
                    continue
                records.append(rec)
        records.sort(key=lambda r: r.get("date", ""))
        return records
    except Exception:
        logger.warning("读取 health JSONL 失败，跳过 warning 检查")
        return []


def _emit_health_warnings(name, passed_count, today_str):
    """根据当天 results 和历史记录输出 warning banner 到 stderr。"""
    if passed_count == 0:
        print(f"\u26a0\ufe0f  [WARNING] \u4fe1\u6e90\u5065\u5eb7: {name} passed=0 ({today_str})", file=sys.stderr)

    records = _read_recent_health(name, today_str)
    if not records:
        return

    daily = {}
    for r in records:
        daily[r.get("date", "")] = r

    sorted_dates = sorted(daily.keys())
    recent_dates = [d for d in sorted_dates if d <= today_str][-3:]

    if len(recent_dates) >= 3:
        recent = [daily[d] for d in recent_dates]
        if all(int(r.get("passed", 0)) < 5 for r in recent):
            vals = ", ".join(str(r.get("passed", 0)) for r in recent)
            print(f"\u26a0\ufe0f  [WARNING] \u4fe1\u6e90\u5065\u5eb7: {name} \u8fde\u7eed3\u5929 passed<5 ({vals}, {recent_dates[0]}~{recent_dates[-1]})", file=sys.stderr)


# ============================================================
# Step 1+2: 日期确认 + 工作目录
# ============================================================

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

def _is_static_sufficient(html, min_len=500, required_selectors=None):
    if not html or len(html) < min_len:
        return False
    if required_selectors:
        return all(re.search(sel, html, re.DOTALL | re.IGNORECASE) for sel in required_selectors)
    return '<a' in html or '<article' in html or '<div' in html

def fetch_home_html(url, required_selectors=None):
    try:
        html = fetch_html_static(url)
        if _is_static_sufficient(html, required_selectors=required_selectors):
            return html
    except Exception:
        pass
    return chromium_dom(url)


def clean_anchor_text(raw):
    text = re.sub(r'<[^>]+>', '', raw)
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def fetch_url_title(url):
    try:
        return fetch_title(fetch_html_static(url, timeout=10))
    except Exception:
        return ""


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


def _fmt_date_from_yyyymmdd(raw):
    if not raw or len(raw) != 8:
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _date_from_url(url):
    for pat in [r'/((?:20)\d{6})/', r't((?:20)\d{6})_', r'((?:20)\d{6})']:
        m = re.search(pat, url)
        if m:
            return _fmt_date_from_yyyymmdd(m.group(1))
    m = re.search(r'/((?:20)\d{2})/(\d{2})/(\d{2})/', url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _date_from_html(html):
    patterns = [
        r'(?:发布时间|发布日期|发稿时间|时间)[:：]\s*((?:20)\d{2})[-年](\d{1,2})[-月](\d{1,2})',
        r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|pubdate|publishdate|publishdate)["\'][^>]+content=["\']((?:20)\d{2})[-/](\d{1,2})[-/](\d{1,2})',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{y}-{mo:02d}-{d:02d}"
    return None


def fetch_published_at(url):
    date = _date_from_url(url)
    if date:
        return date
    try:
        return _date_from_html(fetch_html_static(url, timeout=10))
    except Exception:
        return None


def _article(url, title, published_at=None):
    return {"url": url, "title": title, "published_at": published_at}


def split_by_publish_date(items, today):
    today_str = today.strftime("%Y-%m-%d")
    passed, failed = [], []
    for item in items:
        published_at = item.get("published_at")
        item["published_at"] = published_at
        if not published_at:
            failed.append({"item": item, "reason": "无可信发布日期"})
        elif published_at != today_str:
            failed.append({"item": item, "reason": f"非当日发布:{published_at}"})
        else:
            passed.append(item)
    return passed, failed


async def http_200_async(session, url):
    """异步 HTTP 检查（最多试 3 次，返回 (ok, reason)）"""
    reasons = []
    for attempt in range(3):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=12), ssl=ssl_ctx) as r:
                if r.status == 200:
                    return True, None
                reasons.append(f"HTTP {r.status}")
        except asyncio.TimeoutError:
            reasons.append("timeout")
        except aiohttp.ClientError as e:
            reasons.append(str(e))
        except Exception as e:
            reasons.append(str(e))
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))
    return False, "; ".join(reasons)


# ============================================================
# 7信源采集函数
# ============================================================

def fetch_xinhuanet(today):
    """新华社: news.cn 首页 → 正则 YYYYMMDD/c.html"""
    today8 = today.strftime("%Y%m%d")
    html = fetch_home_html("https://www.news.cn/", required_selectors=[r'news\.cn', r'c\.html'])
    anchor_titles = {}
    for href, raw in re.findall(r'<a[^>]+href=["\']([^"\']*news\.cn[^"\']*' + today8 + r'[^"\']*c\.html)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
        title = clean_anchor_text(raw)
        if title and len(title) > 4:
            anchor_titles.setdefault(href, title)
    urls = list(dict.fromkeys(
        re.findall(rf'https?://[^"\'\s]*news\.cn/[^"\'\s]*/{today8}/[a-z0-9]+/c\.html', html)
    ))
    results = []
    for u in urls:
        t = anchor_titles.get(u) or fetch_url_title(u)
        if t:
            results.append(_article(u, t, today.strftime("%Y-%m-%d")))
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
            req_ = Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://china.cankaoxiaoxi.com/"
            })
            data = json.loads(urlopen(req_, timeout=8, context=ssl_ctx).read())
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
                results.append(_article(u, title, createtime[:10]))

    return results


def fetch_cctv_news(today):
    """央视新闻: 首页 DOM 提取 (URL, title) 对"""
    today_path = today.strftime("%Y/%m/%d")
    html = fetch_home_html("https://news.cctv.com/", required_selectors=[r'cctv\.com.*?\.shtml'])
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    results = []
    seen = set()
    for l, t_raw in links:
        if "cctv.com" not in l or today_path not in l or ".shtml" not in l:
            continue
        u = l if l.startswith("http") else f"https:{l}" if l.startswith("//") else f"https://news.cctv.com{l}"
        if u in seen:
            continue
        seen.add(u)
        t = clean_anchor_text(t_raw) or fetch_url_title(u)
        if t and len(t) > 4:
            results.append(_article(u, t, today.strftime("%Y-%m-%d")))
    return results


def fetch_cctv_military(today):
    """央视军事: 首页 DOM 提取 (URL, title) 对"""
    today_path = today.strftime("%Y/%m/%d")
    html = fetch_home_html("https://military.cctv.com/", required_selectors=[r'military\.cctv\.com.*?\.shtml'])
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    results = []
    seen = set()
    for l, t_raw in links:
        if "military.cctv.com" not in l or today_path not in l or ".shtml" not in l:
            continue
        u = l if l.startswith("http") else f"https:{l}" if l.startswith("//") else f"https://military.cctv.com{l}"
        if u in seen:
            continue
        seen.add(u)
        t = clean_anchor_text(t_raw) or fetch_url_title(u)
        if t and len(t) > 4:
            results.append(_article(u, t, today.strftime("%Y-%m-%d")))
    return results


def fetch_cas(today):
    """中科院: urllib 首页 → URL 发布日期必须为当天。"""
    html = fetch_html_static("https://www.cas.cn/", timeout=15)
    today8 = today.strftime("%Y%m%d")
    raw_urls = re.findall(rf'//www\.cas\.cn/\.\./\.\./([^"\'\s]*t{today8}_[^"\'\s]*\.shtml)', html)
    seen = set()
    urls = []
    for raw in raw_urls:
        parts = [p for p in raw.split("/") if p and p != ".."]
        u = f"https://www.cas.cn/{'/'.join(parts)}"
        if u not in seen:
            seen.add(u)
            urls.append(u)
    htmls = _fetch_many_sync(urls)
    results = []
    for u, h in zip(urls, htmls):
        if h:
            t = fetch_title(h)
            if t:
                results.append(_article(u, t, today.strftime("%Y-%m-%d")))
    return results


def fetch_cnnc_chromium(today):
    """中核集团 → 方案1: cnnc.com.cn"""
    try:
        html = fetch_html_static("https://www.cnnc.com.cn/", timeout=8)
    except Exception:
        return []
    today8 = today.strftime("%Y%m%d")
    links_titles = re.findall(
        r'<a[^>]+href=["\']([^"\']*cnnc[^"\']*' + today8 + r'[^"\']*)["\'][^>]*>(.*?)</a>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    results = []
    for href, title in links_titles[:8]:
        t = clean_anchor_text(title)
        if t and len(t) > 3:
            u = href if href.startswith("http") else f"https://www.cnnc.com.cn{href}"
            results.append(_article(u, t, today.strftime("%Y-%m-%d")))
    return results


def fetch_cnnc_cnnpn(today):
    """中核集团 → 方案2: cnnpn.cn 聚合站（CF 绕过）"""
    try:
        html = fetch_html_static("https://www.cnnpn.cn/", timeout=8)
    except Exception:
        return []
    anchors = re.findall(r'<a[^>]+href=["\']([^"\']*cnnpn\.cn[^"\']*article[^"\']*)["\'][^>]*>(.*?)</a>', html, re.S | re.I)
    seen = set()
    results = []
    for l, raw_title in anchors:
        if l in seen:
            continue
        seen.add(l)
        u = l if l.startswith("http") else f"https://www.cnnpn.cn{l}" if l.startswith("/") else f"https://www.cnnpn.cn/{l}"
        published_at = _date_from_url(u)
        t = clean_anchor_text(raw_title)
        if t and len(t) > 4:
            results.append(_article(u, t, published_at))
        if len(results) >= 8:
            break
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
    yyyymm = today.strftime("%Y%m")
    dd = today.strftime("%d")
    layout_urls = [
        f"https://paper.people.com.cn/rmrb/pc/layout/{yyyymm}/{dd}/node_{node:02d}.html"
        for node in range(1, 10)
    ]
    layout_htmls = _fetch_many_sync(layout_urls)
    seen = set()
    content_urls = []
    for html in layout_htmls:
        if not html:
            continue
        hrefs = re.findall(r'href=["\']([^"\']*content_\d+\.html)["\']', html)
        for raw in hrefs:
            filename = raw.split("/")[-1]
            u = f"https://paper.people.com.cn/rmrb/pc/content/{yyyymm}/{dd}/{filename}"
            if u not in seen:
                seen.add(u)
                content_urls.append(u)
    content_htmls = _fetch_many_sync(content_urls)
    results = []
    for u, h in zip(content_urls, content_htmls):
        if h:
            t = fetch_title(h)
            if t:
                results.append(_article(u, t, today.strftime("%Y-%m-%d")))
    return results


# ============================================================
# 三淘汰验证 + aiohttp 并发
# ============================================================

async def verify_http(items, today):
    """通用 HTTP 200 验证（Python 不编造 URL，仅确认页面可达）"""
    if not items:
        return [], [], []

    items, date_failed = split_by_publish_date(items, today)
    if not items:
        return [], date_failed, []

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=30)
    async with aiohttp.ClientSession(connector=connector, headers={"User-Agent": "Mozilla/5.0"}) as session:
        urls = [it["url"] for it in items]
        results = await asyncio.gather(*[http_200_async(session, u) for u in urls])

    passed, failed = [], []
    for item, (ok, reason) in zip(items, results):
        if ok:
            passed.append(item)
        else:
            failed.append({"item": item, "reason": reason or "HTTP非200"})

    return passed, date_failed + failed, []


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
            status = "❌失败"
        elif total > 1 or (total == 1 and passed):
            status = "✅通过"
        else:
            status = "❌失败"

        lines.append(f"## {name}（通过{len(passed)}条 / 淘汰{len(failed)}条 / 汇总{total}条 → {status}）")
        lines.append(f"工具: {tool}")

        for item in passed:
            t = item["title"].replace("\n", " ")[:80]
            published_at = item.get("published_at") or item.get("date")
            if not published_at:
                raise ValueError(f"通过条目缺少 published_at: {item['url']}")
            lines.append(f"- [{published_at}] {t} | {item['url']} ✅")

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
# async helper
# ============================================================

async def _async_fetch_many(urls, semaphore=None, max_concurrent=5):
    """受控并发抓取多个 URL，保持输入顺序。失败条目返回 None。"""
    if semaphore is None:
        semaphore = asyncio.Semaphore(max_concurrent)

    @tenacity.retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10) + wait_random(0, 2)
    )
    async def _fetch_one(client, url):
        async with semaphore:
            resp = await client.get(url, timeout=httpx.Timeout(12.0))
            resp.raise_for_status()
            return resp.text

    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        results = await asyncio.gather(
            *[_fetch_one(client, u) for u in urls],
            return_exceptions=True
        )
    return [r if not isinstance(r, Exception) else None for r in results]


def _fetch_many_sync(urls, max_concurrent=5):
    """同步调用 _async_fetch_many。"""
    return asyncio.run(_async_fetch_many(urls, max_concurrent=max_concurrent))


# ============================================================
# 主流程
# ============================================================

# 7信源定义: (名称, fetcher, 工具名)
SOURCES = [
    ("新华社",    fetch_xinhuanet,    "urllib 首页 + chromium 降级"),
    ("参考消息",  fetch_ckxx,         "urllib JSON API"),
    ("央视新闻",  fetch_cctv_news,    "urllib 首页 + chromium 降级"),
    ("央视军事",  fetch_cctv_military,"urllib 首页 + chromium 降级"),
    ("中科院",    fetch_cas,          "urllib cas.cn"),
    ("中核集团",  fetch_cnnc,         "降级链"),
    ("人民日报",  fetch_rmrb,         "urllib 版面索引"),
]

def main():
    today, dry_run = parse_args()
    today, workdir = init(today)
    today_str = today.strftime("%Y-%m-%d")

    print(f"\n═══ Step 3: 7信源采集 + 三淘汰验证 ═══\n")

    all_entries = []

    for i, (name, fetcher, tool) in enumerate(SOURCES, 1):
        t0 = time.time()
        print(f"[{i}/7] {name}...", end=" ", flush=True)

        try:
            # ① 采集
            if name == "中核集团":
                items, tool = fetcher(today)
            else:
                items = fetcher(today)

            if not items:
                elapsed_ms = int((time.time() - t0) * 1000)
                print(f"→ 0条 → ❌失败 ({elapsed_ms / 1000:.1f}s)")
                all_entries.append({
                    "source": name, "passed": [], "failed": [], "tool": tool
                })
                hr = HealthRecord(
                    date=today_str, source=name, passed=0, failed=0,
                    total=0, tool=tool, elapsed_ms=elapsed_ms,
                    status="failed",
                    recorded_at=datetime.now(_CST).isoformat(),
                )
                write_health_record(hr, dry_run)
                continue

            # ② 仅 HTTP 200 验证（Python 不编造 URL）
            passed, failed, _ = asyncio.run(verify_http(items, today))
            elapsed_ms = int((time.time() - t0) * 1000)

            print(f"→ {len(items)}条 ({elapsed_ms / 1000:.1f}s)")
            print(f"    ✅{len(passed)} / ❌{len(failed)}")

            all_entries.append({
                "source": name, "passed": passed, "failed": failed, "tool": tool
            })
            hr = HealthRecord(
                date=today_str, source=name, passed=len(passed),
                failed=len(failed), total=len(items), tool=tool,
                elapsed_ms=elapsed_ms,
                status="ok" if len(passed) > 0 else "failed",
                recorded_at=datetime.now(_CST).isoformat(),
            )
            write_health_record(hr, dry_run)

        except Exception as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"→ ❌ 异常 ({elapsed_ms / 1000:.1f}s): {e}")
            all_entries.append({
                "source": name, "passed": [], "failed": [], "tool": tool
            })
            hr = HealthRecord(
                date=today_str, source=name, passed=0, failed=0,
                total=0, tool=tool, elapsed_ms=elapsed_ms,
                status="failed",
                recorded_at=datetime.now(_CST).isoformat(),
            )
            write_health_record(hr, dry_run)

    # ③ 写入
    passed_count = write_0(today, all_entries, dry_run)

    # 汇总
    print(f"\n═══ 汇总 ═══")
    for entry in all_entries:
        p = len(entry["passed"])
        f = len(entry["failed"])
        if p > 0:
            print(f"  ✅ {entry['source']}: {p}条通过")
        elif p == 0 and f > 0:
            print(f"  ⚠ {entry['source']}: {p}条通过, {f}条淘汰")
        else:
            print(f"  ❌ {entry['source']}: 不可达")

    # health warning banners
    for entry in all_entries:
        _emit_health_warnings(entry["source"], len(entry["passed"]), today_str)

    print(f"\n产出: {passed_count}/7 信源有通过条目")
    if dry_run:
        print("模式: --dry-run (未写文件)")
    else:
        print(f"文件: {workdir / '0新闻_粗筛.md'}")


if __name__ == "__main__":
    main()
