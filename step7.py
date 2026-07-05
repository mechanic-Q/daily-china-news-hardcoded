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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from daily.common import BASE_DIR, COLUMN_ORDER, parse_common_args as parse_args
load_dotenv(Path(__file__).parent / '.env')

STEP7_MAX_WORKERS = 3

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


COT_LEAK_PATTERNS = [
    '用户要求我', '让我分析', '我需要确保', 'Potential answer', 'The user wants',
    'I need to', '核心要点应该', '用1-2句话', '直接输出摘要',
    '让我总结', '关键在于', '主要信息', '关键点', 'core points',
]


def _why_invalid(summary, body):
    """诊断摘要失败原因，返回 None 表示有效，否则返回原因字符串"""
    if not summary or len(summary) < 20:
        return "too_short"
    if len(summary) > 200:
        return "too_long"
    if summary in body:
        return "body_copy"
    if len(summary) < len(body) * 0.02 and len(summary) < 30:
        return "too_short"
    for pat in COT_LEAK_PATTERNS:
        if pat in summary:
            return "cot_leak"
    return None


RETRY_PROMPTS = {
    "cot_leak": "不要输出你的思考过程或分析步骤，直接输出摘要结果。只输出结果。",
    "too_long": "输出严格限制在1-2句话，简洁概括核心要点，不要超过100字。",
    "body_copy": "用自己的话重新组织概括，不要直接复制原文中的句子。",
    "too_short": "请输出完整一句话的摘要，至少包含一个完整的结论。",
}


def llm_summarize(title, body):
    """调用 LLM 逐条摘要（智能重试：诊断失败原因→针对性修复 prompt→重试）。
    失败返回 None，上游用 fallback_summarize 兜底。"""
    import time
    from llm_client import call_llm, LLMCallError

    base_prompt = f"用1-2句话精炼概括以下新闻的核心要点。全文控制在200字以内。简短、准确、完整，直接输出摘要。\n\n标题：{title}\n正文：{body}"

    failures = set()
    for attempt in range(3):
        try:
            prompt = base_prompt
            if attempt > 0 and failures:
                prompt += "\n\n" + "注意：" + " ".join(RETRY_PROMPTS.get(f, "") for f in failures)

            raw = call_llm("summarize", messages=[{"role": "user", "content": prompt}])
            if not raw:
                continue
            cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            reason = _why_invalid(cleaned, body)
            if not reason:
                return cleaned
            failures.add(reason)
            if attempt < 2:
                print(f"  ⚠ {reason}, 重试中...")
                time.sleep(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if attempt < 2:
                print(f"  ⚠ API 异常: {e}, 重试中...")
                time.sleep(2)
            else:
                print(f"  ⚠ API 异常: {e}")
    return None


def summarize_article_worker(index, article):
    summary = llm_summarize(article['title'], article['body'])
    fallback = False
    if not summary:
        summary = fallback_summarize(article['title'], article['body'])
        fallback = True
    summary = summary.replace("习近平", "")
    return index, summary, fallback


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

    with ThreadPoolExecutor(max_workers=STEP7_MAX_WORKERS) as executor:
        futures = {executor.submit(summarize_article_worker, idx, a): idx for idx, a in enumerate(matched)}
        results = {}
        for future in as_completed(futures):
            try:
                idx, summary, fallback = future.result()
                results[idx] = (summary, fallback)
            except Exception as e:
                idx = futures[future]
                a = matched[idx]
                print(f"  ⚠️ 工作线程异常 [{a['src']}] {a['title'][:40]}: {e}")
                results[idx] = (fallback_summarize(a['title'], a['body']), True)

    for idx, a in enumerate(matched):
        summary, fallback = results.get(idx, ("", True))
        a["summary"] = summary or ""
        a["fallback"] = fallback
        fb = "⚡" if fallback else "✅"
        print(f"  {fb} [{a['src']}] {a['title'][:40]}... ({len(a['summary'])}字)")

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
