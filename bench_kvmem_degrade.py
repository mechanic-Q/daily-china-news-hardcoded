#!/usr/bin/env python3
"""bench_kvmem_degrade.py — KVMem rc1 连续请求劣化观测探针（issue #58 T4）。

背景（KVMem 启动指南红线#1 + issue #58）：
  rc1 实例连续 ~30 轮请求后解码速度从 50-86 t/s 劣化到 4 t/s（长上下文 H3
  场景实测）。Daily 单轮全管道约 23-26 次短调用，接近该阈值，需实测判定
  短调用模式是否复现劣化。

用法:
  python3 bench_kvmem_degrade.py parse  --log /tmp/kvmem-daily.log
      解析服务端日志已发生的请求，输出序号→t/s 曲线
  python3 bench_kvmem_degrade.py probe --turns 30 [--port 27182]
                                        [--prefix-log PATH] [--out PATH]
      主动打 N 轮 Daily 风格负载（模拟 step4 china-relevance / column-score
      短输出 + summarize 中等输出），每轮从服务端日志增量提取 gen_toks，
      输出曲线 + 劣化判定
  python3 bench_kvmem_degrade.py judge  --turns-file PATH
      对已有曲线数据（JSON lines）做劣化判定

判定标准: 有效轮（n_gen >= 8，排除单 token MTP 伪影）连续 3 轮 t/s < 30
判定为劣化。单轮慢调用视为系统抖动，不触发。

速度来源说明: KVMem 响应体无 timings 字段（vanilla 专属），t/s 只能从服务端
日志 KVMEM_CHAT_TURN 的 gen_toks 字段读取（= n_gen / gen_ms * 1000）。
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# ── 判定常量 ──
DETERIORATE_TPS = 30.0          # 低于此值视为慢轮（正常 87-100，红线劣化 4）
DETERIORATE_CONSECUTIVE = 3     # 连续 N 慢轮判定劣化
MIN_VALID_N_GEN = 8             # n_gen < 此值视为 MTP 固定开销伪影
MIN_PROBE_TURNS = 30            # 探针默认轮数 = 红线阈值

CHAT_TURN_PREFIX = "KVMEM_CHAT_TURN "


def parse_chat_turns(log_text: str) -> list[dict]:
    """按出现顺序解析 KVMEM_CHAT_TURN 行 → [{seq, n_prompt, n_gen, tps, wall_ms}]。

    gen_toks 字段实际是解码速度 t/s（n_gen / gen_ms * 1000），沿用服务端命名。
    """
    turns = []
    for line in log_text.splitlines():
        if not line.startswith(CHAT_TURN_PREFIX):
            continue
        fields = {}
        for token in line[len(CHAT_TURN_PREFIX):].split():
            if "=" not in token:
                continue
            k, _, v = token.partition("=")
            try:
                fields[k] = float(v) if "." in v else int(v)
            except ValueError:
                continue
        if "gen_toks" not in fields:
            continue
        turns.append({
            "seq": len(turns) + 1,
            "n_prompt": fields.get("n_prompt", 0),
            "n_gen": fields.get("n_gen", 0),
            "tps": float(fields["gen_toks"]),
            "wall_ms": fields.get("wall_ms", 0),
        })
    return turns


def valid_probe_turns(turns: list[dict]) -> list[dict]:
    """过滤单 token / 超短生成的 MTP 固定开销伪影，只留有效曲线点。"""
    return [t for t in turns if t.get("n_gen", 0) >= MIN_VALID_N_GEN]


def judge_deterioration(turns: list[dict], min_turns: int = MIN_PROBE_TURNS) -> dict:
    """劣化判定：有效轮里连续 DETERIORATE_CONSECUTIVE 轮 t/s < DETERIORATE_TPS。"""
    valid = valid_probe_turns(turns)
    tps_seq = [t["tps"] for t in valid]
    consecutive = 0
    first_bad_seq = None
    for t in valid:
        if t["tps"] < DETERIORATE_TPS:
            consecutive += 1
            if consecutive == 1:
                first_bad_seq = t["seq"]
            if consecutive >= DETERIORATE_CONSECUTIVE:
                return {
                    "deteriorated": True,
                    "first_bad_seq": first_bad_seq,
                    "min_tps": min(tps_seq),
                    "n_valid": len(valid),
                    "consecutive_slow": consecutive,
                    "insufficient": False,
                }
        else:
            consecutive = 0
    return {
        "deteriorated": False,
        "first_bad_seq": None,
        "min_tps": min(tps_seq) if tps_seq else None,
        "median_tps": statistics.median(tps_seq) if tps_seq else None,
        "n_valid": len(valid),
        "n_total": len(turns),
        "consecutive_slow": consecutive,
        "insufficient": len(valid) < min_turns,
    }


# ── Daily 风格负载（贴近 6 个 call_site 的真实 prompt 形态）──

DAILY_PROMPTS = [
    # china-relevance / column-score 类: 中长输入 + JSON 短输出
    (
        "判断以下新闻是否与中国直接相关，回答 JSON: {\"related\": true/false, \"score\": 0-10}。\n"
        "新闻：中科院合肥物质科学研究院在聚变堆中子源靶材研究上取得进展，"
        "研发的低活化钢材料通过辐照测试，抗肿胀性能较上一代提升40%，"
        "为下一代聚变堆材料选型提供依据。项目获国家自然科学基金支持。\n"
        "只输出 JSON，不要解释。",
        128,
    ),
    (
        "对下列 8 条新闻打分（0-10 分，新闻价值），按 JSON 数组输出 "
        "[{\"i\": 序号, \"s\": 分数}]，不要解释。\n"
        "1. 央企助农平台累计销售额突破 6290 亿元，覆盖 140 余个脱贫县。\n"
        "2. 新型固态电解质使钠电池能量密度提升 25%，循环 2000 次后容量保持 90%。\n"
        "3. 某省秋粮收获过八成，单产创 16 年新高。\n"
        "4. AI 辅助诊断系统进入 200 家县医院，肺结节检出率 39.6%。\n"
        "5. 国际空间站释放入轨新卫星，用于地表碳监测。\n"
        "6. 量子计算原型机实现化学分子基态求解新纪录。\n"
        "7. 沿海核电项目 4 号机组并网发电，年发电量 1906.3 万度。\n"
        "8. 农村电商培训覆盖 2422.3 万人次，带动 516 万农户增收。",
        256,
    ),
    # summarize 类: 长输入 + 中等输出
    (
        "为下一条新闻写 60-80 字摘要，只输出摘要文本。\n"
        "正文：国家能源局发布数据，前三季度全国可再生能源发电新增装机 1.2 亿千瓦，"
        "占新增总装机的 71%。其中风电新增 2600 万千瓦，光伏新增 8100 万千瓦。"
        "截至 9 月底，可再生能源累计装机占全部装机的 54.4%，较去年同期提升 4.2 个百分点。"
        "发电量方面，前三季度全国可再生能源发电量 2.1 万亿千瓦时，同比增长 18.9%，"
        "约占全社会用电量的 36%。可再生能源利用率保持在 96% 以上，"
        "弃风弃光问题持续改善。新型储能装机同比增长 120%，为高比例新能源接入提供支撑。"
        "下一步将加快推进大型风电光伏基地建设，完善绿证交易制度。",
        512,
    ),
]


def run_probe(port: int, n_turns: int, api_key: str, log_path: Path,
              out_path: Path | None = None, turn_pause_s: float = 0.3) -> dict:
    """主动打 n_turns 轮 Daily 风格负载，每轮从服务端日志增量提取 t/s。"""
    from openai import OpenAI

    client = OpenAI(
        base_url=f"http://127.0.0.1:{port}/v1",
        api_key=api_key,
    )
    base_offset = _log_turn_count(log_path)
    results = []
    print(f"probe: {n_turns} 轮 @ 127.0.0.1:{port}  (基线 {base_offset} 轮已记录)")
    for i in range(1, n_turns + 1):
        prompt, max_tokens = DAILY_PROMPTS[(i - 1) % len(DAILY_PROMPTS)]
        t0 = time.perf_counter()
        try:
            client.chat.completions.create(
                model=os.environ.get("DAILY_PROBE_MODEL", "qwen3.8"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.0,
                extra_body={"reasoning_effort": "none"},
                timeout=120,
            )
            wall_s = time.perf_counter() - t0
        except Exception as e:  # noqa: BLE001 — 探针要记录失败轮继续跑
            wall_s = time.perf_counter() - t0
            print(f"  turn {i}: ❌ {type(e).__name__} after {wall_s:.1f}s")
            results.append({"seq": i, "error": type(e).__name__, "wall_s": round(wall_s, 2)})
            continue
        # 服务端刚记完最后一轮，稍等日志落盘再读。
        # 注意口径一致: base_offset 是 raw 轮数, 这里也必须用 raw 列表比对索引,
        # 再单独对目标轮做 valid 过滤（valid 过滤会跳过伪影轮, 索引错位）
        deadline = time.time() + 5
        tps = None
        while time.time() < deadline:
            raw_turns = parse_chat_turns(_read_log_tail(log_path))
            if len(raw_turns) >= base_offset + i:
                tps = raw_turns[base_offset + i - 1]["tps"]
                break
            time.sleep(0.2)
        results.append({"seq": i, "tps": tps, "wall_s": round(wall_s, 2)})
        print(f"  turn {i}: tps={tps if tps is not None else '?'}  wall={wall_s:.2f}s")
        time.sleep(turn_pause_s)

    probe_turns = [{"seq": r["seq"], "n_gen": MIN_VALID_N_GEN, "tps": r["tps"]}
                   for r in results if r.get("tps") is not None]
    verdict = judge_deterioration(probe_turns)
    report = {"port": port, "n_turns": n_turns, "results": results, "verdict": verdict}
    if out_path:
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"✅ 报告已写入: {out_path}")
    return report


def _read_log_tail(log_path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        size = log_path.stat().st_size
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            return f.read()
    except FileNotFoundError:
        return ""


def _log_turn_count(log_path: Path) -> int:
    return len(parse_chat_turns(_read_log_tail(log_path)))


def main() -> None:
    ap = argparse.ArgumentParser(description="KVMem 劣化观测探针")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="解析已有服务端日志")
    p_parse.add_argument("--log", default="/tmp/kvmem-daily.log")
    p_parse.add_argument("--out")

    p_probe = sub.add_parser("probe", help="主动打 Daily 风格负载并观测")
    p_probe.add_argument("--turns", type=int, default=MIN_PROBE_TURNS)
    p_probe.add_argument("--port", type=int,
                         default=int(os.environ.get("DAILY_PROBE_PORT", "27182")))
    p_probe.add_argument("--api-key", default=os.environ.get("LLAMA_API_KEY", "none"))
    p_probe.add_argument("--log", default="/tmp/kvmem-daily.log")
    p_probe.add_argument("--out")

    p_judge = sub.add_parser("judge", help="对曲线 JSON 做判定")
    p_judge.add_argument("--turns-file", required=True)

    args = ap.parse_args()

    if args.cmd == "parse":
        turns = parse_chat_turns(Path(args.log).read_text(encoding="utf-8",
                                                           errors="replace"))
        valid = valid_probe_turns(turns)
        verdict = judge_deterioration(valid)
        for t in valid:
            print(f"  seq={t['seq']:3d}  n_prompt={t['n_prompt']:6d}  "
                  f"n_gen={t['n_gen']:5d}  tps={t['tps']:7.2f}")
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        if args.out:
            Path(args.out).write_text(
                json.dumps({"turns": valid, "verdict": verdict},
                           ensure_ascii=False, indent=2), encoding="utf-8")
    elif args.cmd == "probe":
        run_probe(args.port, args.turns, args.api_key, Path(args.log),
                  out_path=Path(args.out) if args.out else None)
    elif args.cmd == "judge":
        data = json.loads(Path(args.turns_file).read_text(encoding="utf-8"))
        turns = data["turns"] if isinstance(data, dict) else data
        print(json.dumps(judge_deterioration(turns), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
