#!/bin/bash
# bench_llm.sh — 基准: 对运行中的 8899 服务发 3 个长生成请求, 报 tok/s
# 用法: bash bench_llm.sh [port]
set -euo pipefail
PORT="${1:-8899}"
python3 - "$PORT" <<'EOF'
import sys, urllib.request, json, time
port = sys.argv[1]
PROMPTS = [
    "写一篇200字关于秋天的小短文",
    "详细介绍光合作用的过程",
    "描述一座海滨城市的清晨景象",
]
def bench(prompt, max_tokens=400):
    t0 = time.time()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps({"model": "qwen3.8", "messages": [{"role": "user", "content": prompt}],
                         "max_tokens": max_tokens, "temperature": 0, "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    el = time.time() - t0
    ct = d["usage"].get("completion_tokens", 0)
    return el, ct
rates = []
bench("hi", 10)  # warmup
for i, p in enumerate(PROMPTS):
    el, ct = bench(p)
    tps = ct / el if ct else 0.0
    rates.append(tps)
    print(f"run{i}: {el:.1f}s  out_tok={ct}  {tps:.1f} tok/s")
avg = sum(rates) / len(rates)
print(f"AVG: {avg:.1f} tok/s")
EOF
