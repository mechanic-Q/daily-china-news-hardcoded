#!/bin/bash
# start-llm.sh — Daily 专用 Qwen3.8-27B 启动
# 用法:
#   bash start-llm.sh          # 默认: vanilla llama-server @ 8899 (IQ3_XS, 旧栈, 保留作回滚)
#   bash start-llm.sh kvmem    # KVMem rc1 + IQ2_S @ 27182 (Daily 本地后端, 2026-09 起, 见 ADR-0004)
# 纯文本 / 思维链关 / 无 DFlash2 / 无视觉 / ctx 32768 / 串行 (parallel=1)
#
# 为什么不用 ~/projects/llama-dflash2/03-start-qwen38-dflash2.sh:
#   DFlash2 投机解码在本机会挂死 (所有 task 被 cancel, 无响应)
#   start-vision.sh ctx 仅 4096 (日报 prompt 过长)
#   故取 start-text 的纯文本, 去 DFlash2
#
# parallel=1: n_slots=1, GPU 无并发, 避免 4-slot 同时激活把 VRAM 顶过 16G 触发
#   cuMemSetAccess CUDA error (2026-08-23 step7 7 路 summarize+dedup 崩溃根因)。
# 思维链关: summarize max_tokens=512 全给正文摘要, CoT 不再吃额度 → 空 content 趋零。
# chat-template-file: Qwen3 官方模板规定 system 必须第一条, 否则 raise。
#   opencode/Magic-Context 会中途注入 <system-reminder> system 角色消息 → 必炸。
#   qwen3-tolerant.tmpl = 官方模板去 raise, 中途 system 改渲染为 user。
set -euo pipefail

# ── kvmem 模式: KVMem rc1 (WSL Linux sm120a 专用包) + IQ2_S 去限款 ──
# 实测参照: 短上下文 75-86 t/s, 单次数百 token 调用 ≈3s (KVMem-IQ2S-WSL-启动指南.md §3/§4)
# 红线: 16G 显存单实例互斥 —— 8888(视频 np4)/8899(旧栈)/18200/18201(视频 KVMem)
#   任一在线时拒绝启动 (issue #56)
if [ "${1:-}" = "kvmem" ]; then
    KBIN="$HOME/kvmem-rc1/kvmem-v0.16.0-rc1-linux-x86_64-cuda13-sm120a/bin/llama-kvmem-server"
    KMODEL="$HOME/models/llm/qwen38-27b/iq2s/Qwen3.8-27B-Abliterated-GSQ-Orca-IQ2_S-MTP.gguf"
    KPORT=27182   # 冷门端口(18201/18202 让给视频侧); 改这里必须同步改 llm.yaml 的 kvmem.base_url
    MIN_TPS=75    # 自检达标线 (issue #56); 实测参照 87-90 (指南 75-86)
    [ -f "$KBIN" ]   || { echo "缺 llama-kvmem-server: $KBIN";  exit 1; }
    [ -f "$KMODEL" ] || { echo "缺模型: $KMODEL"; exit 1; }
    command -v ss >/dev/null || { echo "缺 ss 命令, 无法做显存互斥检查, 拒绝启动"; exit 1; }
    for p in 8888 8899 18200 18201 "$KPORT"; do
        if ss -tln | grep -q ":$p "; then
            echo "拒绝启动: 端口 $p 已被占用 —— 16G 卡两实例必 OOM, 先停对方"; exit 1
        fi
    done
    nohup "$KBIN" -m "$KMODEL" \
        --host 127.0.0.1 --port "$KPORT" \
        -c 262144 -n 16384 \
        --kvmem-budget 36864 --kvmem-gen-reserve 16384 \
        --kvmem-block-tokens 128 --kvmem-query-policy user \
        -ctk q8_0 -ctv q8_0 \
        --spec-type draft-mtp --spec-draft-n-max 3 \
        --no-think \
        > /tmp/kvmem-daily.log 2>&1 &
    KPID=$!
    echo "KVMem 启动中: http://127.0.0.1:$KPORT/v1  (日志 /tmp/kvmem-daily.log)"
    # 自检: KVMem 响应体无 timings 字段(vanilla 专属), 速度看服务端日志 KVMEM_CHAT_TURN 的 gen_toks。
    # 负载用 256-token 生成: 短生成(数十 token) MTP 固定开销占比大, 数值波动 68-75 会误杀
    # 健康实例; 256 token 实测稳定 87-90 t/s (2026-09-24 本机, 指南参照 75-86)。
    SELF_CHECK='{"messages":[{"role":"user","content":"数从1到100，每行一个"}],"max_tokens":256,"temperature":0}'
    for i in $(seq 1 24); do
        sleep 2
        if curl -sf -m 2 "http://127.0.0.1:$KPORT/health" >/dev/null 2>&1; then
            curl -s -m 120 "http://127.0.0.1:$KPORT/v1/chat/completions" \
                -H "Content-Type: application/json" -d "$SELF_CHECK" >/dev/null
            TPS=$(grep 'KVMEM_CHAT_TURN' /tmp/kvmem-daily.log | grep -oE 'gen_toks=[0-9.]+' | tail -1 | cut -d= -f2)
            echo "自检 gen_tps: ${TPS:-0}  (达标线 $MIN_TPS; 实测参照 87-90; <30 显卡被占/服务异常)"
            python3 -c "import sys; sys.exit(0 if float(sys.argv[1] or 0) >= float(sys.argv[2]) else 1)" "${TPS:-0}" "$MIN_TPS" \
                || { echo "自检不达标: gen_tps < $MIN_TPS, 服务异常, 查 /tmp/kvmem-daily.log"; kill "$KPID" 2>/dev/null; exit 1; }
            exit 0
        fi
    done
    echo "启动超时: 48s 内 health 未就绪, 查 /tmp/kvmem-daily.log"; kill "$KPID" 2>/dev/null; exit 1
fi

BIN="$HOME/projects/llama-dflash2/llama.cpp/build/bin/llama-server"
MAIN="$HOME/models/llm/qwen38-27b/main-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-IQ3_XS.gguf"

[ -f "$BIN" ]  || { echo "缺 llama-server: $BIN";  exit 1; }
[ -f "$MAIN" ] || { echo "缺模型: $MAIN"; exit 1; }

echo "=== Qwen3.8-27B 破限版 (Daily: 纯文本/思维链关/串行/ctx 32768) ==="
echo "API: http://localhost:8899/v1  (Ctrl+C 停止)"
echo ""

exec "$BIN" \
    --model "$MAIN" \
    --n-gpu-layers 999 \
    --ctx-size 32768 \
    --flash-attn on \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    --ctx-checkpoints 4 \
    --spec-type draft-mtp --spec-draft-n-max 2 \
    --parallel 1 \
    --jinja \
    --chat-template-file "$HOME/projects/Daily/qwen3-tolerant.tmpl" \
    --alias qwen3.8 \
    --host 0.0.0.0 --port 8899
