#!/bin/bash
# start-llm.sh — Daily 专用 Qwen3.8-27B 启动
# 纯文本 / 思维链关 / 无 DFlash2 / 无视觉 / ctx 32768 / 串行 (parallel=1)
# 用法: bash start-llm.sh  (Ctrl+C 停止)
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
