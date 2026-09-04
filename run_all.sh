#!/usr/bin/env bash
# run_all.sh — 全管道串联
# 用法: ./run_all.sh [--date YYYY-MM-DD] [--dry-run]
#       无 --date 则默认今天

set -euo pipefail

DATE=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)
            DATE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        *)
            echo "错误: 未知参数: $1" >&2
            echo "用法: $0 [--date YYYY-MM-DD] [--dry-run]" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$DATE" ]]; then
    DATE=$(date +%Y-%m-%d)
    echo "未指定日期，默认使用今天: $DATE"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [[ ! -x "$PYTHON" ]]; then
    echo "错误: 项目虚拟环境不存在；请运行: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# --- 本地 LLM 服务生命周期 (Qwen3.8-27B @ localhost:8899, 专属端口, 用完必关) ---
LLM_SERVER_SCRIPT="$SCRIPT_DIR/start-llm.sh"
LLM_SERVER_PORT=8899
LLM_PID=""

llm_server_up() {
    curl -sf -m 2 "http://localhost:$LLM_SERVER_PORT/v1/models" >/dev/null 2>&1
}

# 提取本专属端口上实际监听的 llama-server PID (很可能只有自家残留)
port_pids() {
    ss -ltnp 2>/dev/null | awk -v p=":$LLM_SERVER_PORT" \
        '$1=="LISTEN" && $4~p { for(i=1;i<=NF;i++) if($i~/pid=/) { sub(/.*pid=/,"",$i); sub(/,.*/,"",$i); print $i } }'
}

start_llm_server() {
    local existing
    existing=$(port_pids | head -n1)
    if [[ -n "$existing" ]] && llm_server_up; then
        LLM_PID="$existing"   # 复用自家残留, 用完同样关闭
        echo "  [LLM] 服务已在运行 (pid=$LLM_PID)"
        return 0
    fi
    if [[ -n "$existing" ]]; then
        echo "  [LLM] 端口 $LLM_SERVER_PORT 被异常进程占用, 先清理: $existing"
        kill "$existing" 2>/dev/null || true
        sleep 1
    fi
    if [[ ! -f "$LLM_SERVER_SCRIPT" ]]; then
        echo "  [LLM] ⚠ 找不到 $LLM_SERVER_SCRIPT，跳过自动启动（需手动启动 LLM 服务）"
        return 0
    fi
    echo "  [LLM] 启动 Qwen3.8-27B 服务..."
    nohup bash "$LLM_SERVER_SCRIPT" > /tmp/daily-llm-server.log 2>&1 &
    LLM_PID=$!
    for i in $(seq 1 90); do
        if llm_server_up; then
            echo "  [LLM] 就绪 (pid=$LLM_PID)"
            return 0
        fi
        sleep 2
    done
    echo "错误: LLM 服务 180s 内未就绪，日志: /tmp/daily-llm-server.log" >&2
    stop_llm_server
    exit 1
}

stop_llm_server() {
    local pids unique=""
    pids=$(port_pids)
    for p in $LLM_PID $pids; do
        [[ " $unique " == *" $p "* ]] && continue
        unique="$unique $p"
        echo "  [LLM] 停止服务 (pid=$p)..."
        kill "$p" 2>/dev/null || true
    done
    if [[ -n "$unique" ]]; then
        sleep 1
        for p in $unique; do
            kill -9 "$p" 2>/dev/null || true
        done
        LLM_PID=""
    fi
}

trap stop_llm_server EXIT INT TERM

STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")

pipeline_start=$(date +%s)

for step in "${STEPS[@]}"; do
    if [[ "$step" == "step4.py" ]]; then
        echo ""
        echo "  [LLM] step4 需要 LLM，启动服务..."
        start_llm_server
    fi
    echo ""
    echo "═══ 运行: $step --date $DATE $DRY_RUN ═══"
    step_start=$(date +%s)
    set +e
    "$PYTHON" "$SCRIPT_DIR/$step" --date "$DATE" $DRY_RUN
    exit_code=$?
    set -e
    step_end=$(date +%s)
    step_duration=$(( step_end - step_start ))
    if [[ $exit_code -ne 0 ]]; then
        echo "⏱ $step: ${step_duration}s"
        pipeline_end=$(date +%s)
        total_duration=$(( pipeline_end - pipeline_start ))
        echo "⏱ 总耗时: ${total_duration}s"
        echo "❌ $step 失败，停止执行"
        exit 1
    fi
    echo "⏱ $step: ${step_duration}s"
    if [[ "$step" == "step7.py" ]]; then
        stop_llm_server
        # --- 摘要质量闸门：占位/空转摘要必须拦截，不让垃圾进报纸 ---
        overview="/mnt/e/每日新中国/$DATE/3新闻_概述.md"
        if [[ -f "$overview" ]]; then
            if grep -qE "请提供|我才能根据|无法概括|正文仅包含|仅表明|无法生成|请补充|未包含具体新闻事实" "$overview"; then
                echo ""
                echo "❌ 摘要质量闸门：$DATE 的 3新闻_概述.md 含占位摘要，报纸不生成。"
                echo "   命中行："
                grep -nE "请提供|我才能根据|无法概括|正文仅包含|仅表明|无法生成|请补充|未包含具体新闻事实" "$overview" | head -10
                echo "   处理：人工改写概述后重跑 step8（python3 step8.py --date $DATE）"
                exit 1
            fi
            echo "  ✅ 摘要质量闸门通过（无占位摘要）"
        fi
    fi
done

echo ""
echo "✅ 全管道完成: $DATE"
pipeline_end=$(date +%s)
total_duration=$(( pipeline_end - pipeline_start ))
echo "⏱ 总耗时: ${total_duration}s"
