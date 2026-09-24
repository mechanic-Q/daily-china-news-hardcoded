#!/bin/bash
# bench_llm.sh — LLM 后端基准: tok/s（长生成）+ 单调用延迟（短调用）
#
# 用法:
#   bash bench_llm.sh [port]                    # 单端口基准（兼容旧用法，默认 8899）
#   bash bench_llm.sh --compare 27182,8899     # 多端口顺序对比，输出对比表
#   bash bench_llm.sh --compare 27182,8899 --out /tmp/bench.json
#
# 计时口径: 客户端 time.time() 包住整个 HTTP 往返（含连接+prefill+decode）。
# tok/s = usage.completion_tokens / 耗时。两个后端（vanilla llama.cpp / KVMem rc1）
# 均已实测返回标准 usage 字段，无需读服务端日志。
# 单调用延迟 = 短 prompt（输出 ~10 token，模拟 step4 china-relevance 是/否判断）的端到端耗时。
set -euo pipefail
OUT_JSON=""
PORTS_ARG=""
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --compare) PORTS_ARG="${2:?--compare 需要端口列表}"; shift 2 ;;
        --out)     OUT_JSON="${2:?--out 需要路径}"; shift 2 ;;
        *)         ARGS+=("$1"); shift ;;
    esac
done
if [ -z "$PORTS_ARG" ]; then
    PORTS_ARG="${ARGS[0]:-8899}"
fi

python3 - "$PORTS_ARG" "$OUT_JSON" <<'EOF'
import sys, urllib.request, json, time

ports_arg, out_json = sys.argv[1], sys.argv[2]
ports = [p.strip() for p in ports_arg.split(",") if p.strip()]

PROMPTS = [
    "写一篇200字关于秋天的小短文",
    "详细介绍光合作用的过程",
    "描述一座海滨城市的清晨景象",
]
SHORT_PROMPT = "判断以下新闻标题内容主体上是否直接与中国相关。只回答\"是\"或\"否\"。\n\n标题：我国电动汽车充电基础设施总数达2422.3万个"


def call(port, prompt, max_tokens, timeout):
    t0 = time.time()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps({"model": "qwen3.8",
                         "messages": [{"role": "user", "content": prompt}],
                         "max_tokens": max_tokens, "temperature": 0,
                         "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    el = time.time() - t0
    ct = d.get("usage", {}).get("completion_tokens", 0)
    return el, ct


def bench_port(port):
    # warmup: 权重加载/缓存预热不计入统计
    call(port, "hi", 10, 120)
    rates, latencies = [], []
    for i, p in enumerate(PROMPTS):
        el, ct = call(port, p, 400, 600)
        tps = ct / el if ct else 0.0
        rates.append(tps)
        print(f"  run{i}: {el:.1f}s  out_tok={ct}  {tps:.1f} tok/s")
    for i in range(3):
        el, ct = call(port, SHORT_PROMPT, 16, 120)
        latencies.append(el)
        print(f"  short{i}: {el:.2f}s  out_tok={ct}")
    return {"tps_runs": rates, "tps_avg": sum(rates) / len(rates),
            "short_latency_s": latencies,
            "short_latency_avg": sum(latencies) / len(latencies)}


results = {}
for port in ports:
    print(f"== port {port} ==")
    try:
        results[port] = bench_port(port)
        print(f"  AVG: {results[port]['tps_avg']:.1f} tok/s | "
              f"short_latency_avg: {results[port]['short_latency_avg']:.2f}s")
    except Exception as e:
        print(f"  ❌ port {port} 基准失败: {e}")
        results[port] = {"error": str(e)}

if len(ports) > 1:
    print("\n== 对比 ==")
    print("| port | avg tok/s | avg short latency |")
    print("|------|-----------|-------------------|")
    for port in ports:
        r = results[port]
        if "error" in r:
            print(f"| {port} | ❌ {r['error'][:40]} | - |")
        else:
            print(f"| {port} | {r['tps_avg']:.1f} | {r['short_latency_avg']:.2f}s |")

if out_json:
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "ports": results}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {out_json}")
EOF
