#!/bin/bash
# start-llm.sh — Daily 专用 Qwen3.8-27B 启动
# 纯文本 / 思维链关 / 无 DFlash2 / 无视觉 / ctx 32768
# 用法: bash start-llm.sh  (Ctrl+C 停止)
#
# 为什么不用 ~/projects/llama-dflash2/03-start-qwen38-dflash2.sh:
#   DFlash2 投机解码在本机会挂死 (所有 task 被 cancel, 无响应)
#   start-text.sh 开思维链 (破限版会重新推导拒绝)
#   start-vision.sh ctx 仅 4096 (日报 prompt 过长)
#   故取 03-start 的思维链关 + start-text 的纯文本, 去 DFlash2
set -euo pipefail

BIN="$HOME/projects/llama-dflash2/llama.cpp/build/bin/llama-server"
MAIN="$HOME/models/qwen38-27b/main-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q3_K_P.gguf"

[ -f "$BIN" ]  || { echo "缺 llama-server: $BIN";  exit 1; }
[ -f "$MAIN" ] || { echo "缺模型: $MAIN"; exit 1; }

echo "=== Qwen3.8-27B 破限版 (Daily: 纯文本/思维链关/ctx 32768) ==="
echo "API: http://localhost:8888/v1  (Ctrl+C 停止)"
echo ""

exec "$BIN" \
    --model "$MAIN" \
    --n-gpu-layers 999 \
    --ctx-size 32768 \
    --flash-attn on \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    --ctx-checkpoints 4 \
    --reasoning off \
    --chat-template-kwargs '{"enable_thinking": false}' \
    --jinja \
    --host 0.0.0.0 --port 8888
