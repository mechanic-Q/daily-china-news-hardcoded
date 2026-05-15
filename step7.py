#!/usr/bin/env python3
"""
Step 7: 摘要生成 — 从 2新闻_已审核.md 生成 3新闻_概述.md
调用 MiniMax M2.7 API 逐条摘要，API 不可用时规则回退

用法:
    python3 step7.py                      # 处理今天
    python3 step7.py --date 2026-05-10     # 处理指定日期
    python3 step7.py --dry-run              # 预览，不写文件
"""

import datetime
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

BASE_DIR = Path("/mnt/e/每日新中国")

COLUMN_ORDER = [
    '🔬 世界性科研突破', '🌾 农业', '🤝 扶贫', '⚡ 能源',
    '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事',
]


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


def parse_1news(path, today_str):
    """解析 1新闻_链接.md → {normalized_title: {title, category}}"""
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return None
    content = path.read_text("utf-8")
    result = {}
    current_cat = None
    for line in content.splitlines():
        m = re.match(r'^##\s+(.+)', line)
        if m:
            cat = m.group(1).strip()
            if cat in COLUMN_ORDER:
                current_cat = cat
            else:
                current_cat = None
            continue
        m = re.match(r'^###\s+\[(.+?)\]\s+(.+)', line)
        if m and current_cat:
            title_raw = m.group(2).strip()
            key = re.sub(r'\s+', '', title_raw)
            result[key] = {"title": title_raw, "category": current_cat}
    return result


def parse_2news(path, today_str):
    """解析 2新闻_已审核.md → {normalized_title: {title, src, body}}"""
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return None
    content = path.read_text("utf-8")
    result = {}
    for block in content.split("\n## "):
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        title_line = lines[0]
        m = re.match(r'^【(.+?)】(.+)', title_line)
        if m:
            src = m.group(1).strip()
            title_raw = m.group(2).strip()
        else:
            src = ""
            title_raw = title_line.strip()
        body = ""
        for line in lines:
            if line.startswith("正文："):
                body = line[3:].strip()
                break
        key = re.sub(r'\s+', '', title_raw)
        result[key] = {"title": title_raw, "src": src, "body": body}
    return result


def fallback_summarize(title, body):
    """规则截取回退：取首句+末句"""
    if not body or len(body) < 20:
        return title[:80]
    for noise in ['【纠错】', '【责任编辑', '责任编辑', '记者', '编辑', '来源', '免责声明']:
        body = body.replace(noise, '')
    sents = re.findall(r'[^。！？]+[。！？]?', body)
    sents = [s.strip().rstrip('。！？') for s in sents if len(s.strip()) > 10]
    if not sents:
        return body[:100]
    lead = sents[0][:120]
    if len(sents) > 1:
        last = sents[-1][:80].strip().rstrip('。！？')
        if lead and last and lead != last:
            return lead + '。' + last + '。'
    return lead + '。'


def llm_summarize(title, body):
    """调用 MiniMax M2.7 API 摘要（含 1 次重试）"""
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("  ⚠ MINIMAX_API_KEY 未设置，使用规则回退")
        return None

    import time
    for attempt in range(2):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.minimax.chat/v1",
                api_key=api_key,
            )
            prompt = f"""用2-3句中文概括以下新闻。直接输出摘要，不要输出思考过程。

标题：{title}
正文：{body}"""

            resp = client.chat.completions.create(
                model="minimax-m2.7",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
                timeout=30,
            )
            raw = resp.choices[0].message.content.strip()
            if raw:
                cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
                return cleaned if cleaned else None
            return None
        except Exception as e:
            if attempt == 0:
                print(f"  ⚠ API 调用失败，重试中... ({e})")
                time.sleep(2)
            else:
                print(f"  ⚠ API 调用失败: {e}")
                return None


def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")
    path_1 = BASE_DIR / today_str / "1新闻_链接.md"
    path_2 = BASE_DIR / today_str / "2新闻_已审核.md"

    print(f"═══ Step 7: 摘要生成 ═══")
    print(f"日期: {today_str}\n")

    news1 = parse_1news(path_1, today_str)
    if news1 is None:
        return
    news2 = parse_2news(path_2, today_str)
    if news2 is None:
        return

    matched = []
    for key, a1 in news1.items():
        if key in news2:
            a2 = news2[key]
            matched.append({
                "title": a1["title"],
                "category": a1["category"],
                "src": a2["src"],
                "body": a2["body"],
            })
        else:
            print(f"  ⚠ 未匹配到正文: {a1['title'][:40]}")

    print(f"共 {len(matched)} 条，正在生成摘要...\n")

    for i, a in enumerate(matched):
        summary = llm_summarize(a["title"], a["body"])
        if not summary:
            summary = fallback_summarize(a["title"], a["body"])
            a["fallback"] = True
        else:
            a["fallback"] = False
        a["summary"] = summary
        fb = "⚡" if a["fallback"] else "✅"
        print(f"  {fb} [{a['src']}] {a['title'][:40]}... ({len(a['summary'])}字)")
        if not a["fallback"] and i < len(matched) - 1:
            time.sleep(0.5)

    success = sum(1 for a in matched if not a["fallback"])
    print(f"\nAPI成功: {success}/{len(matched)}  规则回退: {len(matched) - success}")

    lines = [f"# {today_str} 新闻概述\n"]

    for col in COLUMN_ORDER:
        col_articles = [a for a in matched if a["category"] == col]
        lines.append(f"\n## {col}\n")
        if col_articles:
            for a in col_articles:
                lines.append(f"### {a['title']}")
                lines.append(a["summary"])
                lines.append("")
        else:
            lines.append("（当日无真实报道，栏目留空）\n")

    output_path = BASE_DIR / today_str / "3新闻_概述.md"

    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print("\n".join(lines)[:2000])
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
