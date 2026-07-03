#!/usr/bin/env python3
"""Phase 15E — 统计 step4.py 三个 LLM call site 的调用次数基线。

用法:
    python3 tests/manual/test_15e_llm_call_count.py
    python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
"""

import datetime
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path("/mnt/e/每日新中国")


def parse_args():
    date_str = None
    dry = "--dry-run" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        dt = datetime.date.today()
    return dt, dry


def _extract_n_from_prompt(content):
    """从 batch prompt 中提取标题数。"""
    return max((int(m) for m in re.findall(r'^\[(\d+)\]', content, re.MULTILINE)), default=0) + 1


def main():
    today, dry_run = parse_args()
    today_str = today.strftime("%Y-%m-%d")

    print(f"📊 Phase 15E — LLM 调用计数基线")
    print(f"日期: {today_str}\n")

    sample = BASE_DIR / today_str / "0新闻_粗筛.md"
    if not sample.exists():
        print(f"⚠ 样本不存在: {sample}")
        print(f"请选择一个存在 0新闻_粗筛.md 的日期（例如 --date 2026-06-30）")
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    worktree_root = script_dir.parent.parent
    sys.path.insert(0, str(worktree_root))

    import step4
    import llm_client
    from daily.common import COLUMN_ORDER

    # === 计数器 ===
    counts = {
        "llm_is_china_related": 0,
        "score_signals": 0,
        "llm_classify_single": {"calls": 0, "articles": 0},
        "call_llm": {"total": 0, "by_site": {}},
    }

    # === 替身 1: llm_is_china_related ===
    _real_china = step4.llm_is_china_related

    def _mock_china(title):
        counts["llm_is_china_related"] += 1
        return True

    # === 替身 2: score_signals ===
    _real_score = step4.score_signals

    def _mock_score(title, source):
        counts["score_signals"] += 1
        return {
            "relevance": {col: 5.0 for col in COLUMN_ORDER},
            "importance": 5.0,
            "timeliness": 5.0,
        }

    # === 替身 3: llm_classify_single ===
    _real_classify = step4.llm_classify_single

    def _mock_classify(articles):
        counts["llm_classify_single"]["calls"] += 1
        counts["llm_classify_single"]["articles"] += len(articles)
        return {a["title"]: "🚀 科技" for a in articles}

    # === 安全网 + 计数器：劫持 call_llm（两个引用点） ===
    _real_client_call = llm_client.call_llm
    _real_step4_call = step4.call_llm

    def _mock_call_llm(call_site_id, messages, **kw):
        counts["call_llm"]["total"] += 1
        counts["call_llm"]["by_site"][call_site_id] = \
            counts["call_llm"]["by_site"].get(call_site_id, 0) + 1

        content = messages[-1].get("content", "") if messages else ""

        if call_site_id == "china-relevance":
            n = _extract_n_from_prompt(content)
            return json.dumps(
                [{"index": i, "is_china_related": True} for i in range(n)],
                ensure_ascii=False,
            )
        elif call_site_id == "column-score":
            n = _extract_n_from_prompt(content)
            return json.dumps([
                {
                    "index": i,
                    "relevance": {col: 5.0 for col in COLUMN_ORDER},
                    "importance": 5.0,
                    "timeliness": 5.0,
                }
                for i in range(n)
            ], ensure_ascii=False)
        elif call_site_id == "column-classify":
            return "🚀 科技"
        return ""

    # === 注入（两个引用路径） ===
    step4.llm_is_china_related = _mock_china
    step4.score_signals = _mock_score
    step4.llm_classify_single = _mock_classify
    step4.call_llm = _mock_call_llm
    llm_client.call_llm = _mock_call_llm

    # === 执行 ===
    classified, selected = step4.build_classification_result(today)
    total_articles = sum(len(v) for v in classified.values())
    cat_count = sum(1 for v in classified.values() if v)

    # === 恢复 ===
    step4.llm_is_china_related = _real_china
    step4.score_signals = _real_score
    step4.llm_classify_single = _real_classify
    step4.call_llm = _real_step4_call
    llm_client.call_llm = _real_client_call

    # === 输出 ===
    print()
    print("========== LLM 调用计数 ==========")
    print(f"  llm_is_china_related:   {counts['llm_is_china_related']} 次")
    print(f"  score_signals:          {counts['score_signals']} 次")
    print(f"  llm_classify_single:    {counts['llm_classify_single']['calls']} 次"
          f" ({counts['llm_classify_single']['articles']} 篇文章)")
    print()
    print(f"  [call_llm 替身拦截]")
    print(f"    总 call_llm 调用:     {counts['call_llm']['total']} 次")
    for site_id, n in sorted(counts['call_llm']['by_site'].items()):
        print(f"    - {site_id}: {n} 次")
    print("==================================")
    print()

    print(f"文章总数（分类后）: {total_articles}")
    print(f"有文章的栏目:        {cat_count} / {len(COLUMN_ORDER)}")
    print(f"精选条数:            {len(selected)}\n")

    for col in COLUMN_ORDER:
        items = classified.get(col, [])
        if items:
            print(f"  {col}: {len(items)} 条")

    print(f"\n✅ 计数完成（未触发真实 LLM 调用）")


if __name__ == "__main__":
    main()
