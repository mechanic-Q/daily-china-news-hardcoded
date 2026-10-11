#!/bin/bash
# start-llm.sh — Daily 专用 Strata (Qwen3.8-Flash-Next IQ3_S) 启动器（Windows Git Bash）
# 用法: bash start-llm.sh    # 后台拉起 + 健康自检, 通过即退出 (服务常驻)
#
# 历史: 8899 vanilla llama.cpp / 27182 KVMem 两个 27B 栈随模型文件删除退役（2026-10-12,
#       见 ADR-0004/0005）。Strata 是 Windows 原生引擎, 与 Daily 管道同进程空间, 启停
#       不再跨 WSL 边界。
#
# 红线: 模型加载后显存 15.7/16.3GB —— 任何其它 GPU 负载 (含 WSL 侧 CUDA, nvidia-smi
#       可见) 在线即拒绝启动。空闲基线 ~600MB。
# 思维链: 引擎默认开 CoT, 自检请求带 reasoning_effort=none (llm.yaml strata.reasoning
#       同款), 小 max_tokens 下不关 CoT 会拿到空 content (2026-10-12 冒烟 max_tokens=32
#       实测 content=null)。
# cwd 必须在 Strata 目录: strata-iq3_s.json 里 engine 命令行用相对路径 (packs\iq3_s)。
set -euo pipefail

STRATA_HOME="E:/AI/LLM/Strata"
PORT=8080   # 改这里必须同步改 llm.yaml 的 strata.base_url
PYEXE="$STRATA_HOME/.venv/Scripts/python.exe"
LOG=/tmp/strata-daily.log
VRAM_LIMIT_MB=2000   # 空闲基线 ~600MB; 超过视为 GPU 被占, 拒绝双开

[ -f "$PYEXE" ]   || { echo "缺 Strata python: $PYEXE";   exit 1; }
[ -f "$STRATA_HOME/strata-iq3_s.json" ] || { echo "缺配置: $STRATA_HOME/strata-iq3_s.json"; exit 1; }

USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' \r')
if [ "${USED:-0}" -gt "$VRAM_LIMIT_MB" ]; then
    echo "拒绝启动: GPU 已占用 ${USED}MiB (阈值 $VRAM_LIMIT_MB, 空闲 ~600) —— Strata 需 15.7GB, 先停对方"
    exit 1
fi

cd "$STRATA_HOME"
nohup "$PYEXE" serve/server.py --engine strata --config strata-iq3_s.json --port "$PORT" > "$LOG" 2>&1 &
echo "Strata 启动中: http://127.0.0.1:$PORT/v1  (日志 $LOG; 83GB 冷加载最长 ~5 分钟)"

# 自检: /v1/models 就绪 + 一发小对话。ASCII prompt (Git Bash 命令行中文按 GBK 编码会 400)
CHECK='{"model":"strata","messages":[{"role":"user","content":"reply ok"}],"max_tokens":16,"temperature":0,"reasoning_effort":"none"}'
for i in $(seq 1 150); do
    sleep 2
    if curl -sf -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
        BODY=$(curl -s -m 60 "http://127.0.0.1:$PORT/v1/chat/completions" \
            -H "Content-Type: application/json" -d "$CHECK")
        if echo "$BODY" | grep -qE '"content":[[:space:]]*(null|"")'; then
            echo "自检失败: content 为空 (reasoning 未关或服务异常), 查 $LOG"; echo "$BODY"; exit 1
        fi
        echo "自检通过: content 非空, reasoning_effort=none 生效"
        exit 0
    fi
done
echo "启动超时: 300s 内 /v1/models 未就绪, 查 $LOG"
echo "注意: 加载中的实例可能仍在后台初始化, 稍后重试或到任务管理器结束 python/strata 进程"
exit 1
