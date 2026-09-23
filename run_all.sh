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

# --- 本地 LLM 服务生命周期 (provider 由 llm.yaml 决定, 端口从 base_url 解析) ---
# issue #58: provider: kvmem → start-llm.sh kvmem @ 27182; qwen-local → 8899;
# 云 provider (zhipu/minimax) 无本地实例, 跳过启停。16G 卡互斥见 ADR-0004。
# 所有权语义 (2026-09-24 沙箱测试误杀生产实例的教训):
#   - 自启动的实例 → trap 退出时关闭 (用完必关)
#   - 端口上已在线的实例 → 复用但退出时**不杀** (可能是用户/上游手动启动)
#   - 互斥端口被外部占用 → 拒绝启动报错退出 (与 start-llm.sh 一致), 绝不替用户杀
LLM_SERVER_SCRIPT="$SCRIPT_DIR/start-llm.sh"
LLM_PID=""

_llm_provider_base_url() {
    python3 - "$SCRIPT_DIR/llm.yaml" <<'PYEOF'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
prov = cfg["providers"][cfg["provider"]]
print(prov["base_url"])
PYEOF
}

_llm_provider_name() {
    python3 - "$SCRIPT_DIR/llm.yaml" <<'PYEOF'
import sys, yaml
print(yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["provider"])
PYEOF
}

LLM_PROVIDER=""
LLM_SERVER_PORT=""

resolve_llm_provider() {
    LLM_PROVIDER=$(_llm_provider_name) || { echo "错误: 无法解析 llm.yaml provider" >&2; exit 1; }
    local base_url
    base_url=$(_llm_provider_base_url) || { echo "错误: 无法解析 llm.yaml base_url" >&2; exit 1; }
    case "$base_url" in
        http://127.0.0.1:*|http://localhost:*)
            local port="${base_url##*:}"
            LLM_SERVER_PORT="${port%%/*}"
            ;;
        *)
            # 云 provider: 无本地实例可管
            LLM_SERVER_PORT=""
            ;;
    esac
    echo "  [LLM] provider=$LLM_PROVIDER base_url=$base_url"
}

llm_server_up() {
    curl -sf -m 2 "http://127.0.0.1:$LLM_SERVER_PORT/v1/models" >/dev/null 2>&1
}

# 提取本专属端口上实际监听的 llama-server PID (很可能只有自家残留)
port_pids() {
    ss -ltnp 2>/dev/null | awk -v p=":$LLM_SERVER_PORT" \
        '$1=="LISTEN" && $4~p { for(i=1;i<=NF;i++) if($i~/pid=/) { sub(/.*pid=/,"",$i); sub(/,.*/,"",$i); print $i } }'
}

# 16G 卡互斥: 其它本地 LLM 端口被占 (非自家端口) 则拒绝双开
# 注意: set -e 下 grep 无结果返回 1, 必须 || true 兜底
foreign_llm_port_pids() {
    ss -tlnp 2>/dev/null | grep -E "127\.0\.0\.1:(8888|8899|18200|18201) " | \
        grep -oE 'pid=[0-9]+' | cut -d= -f2 || true
}

start_llm_server() {
    if [[ -z "$LLM_SERVER_PORT" ]]; then
        echo "  [LLM] provider=$LLM_PROVIDER 为云端 API，跳过本地服务启停"
        return 0
    fi
    local existing foreign
    existing=$(port_pids | head -n1)
    if [[ -n "$existing" ]] && llm_server_up; then
        echo "  [LLM] 端口 $LLM_SERVER_PORT 已有实例在线 (pid=$existing)，复用，退出时不关闭"
        LLM_PID=""   # 非自家启动, 退出时不杀
        return 0
    fi
    foreign=$(foreign_llm_port_pids)
    if [[ -n "$foreign" ]]; then
        echo "错误: 16G 显存互斥: 本地 LLM 端口 8888/8899/18200/18201 被占用 (pid=$foreign)。" >&2
        echo "      双实例必 OOM；请先停对方或改 llm.yaml provider。" >&2
        exit 1
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
    local mode=""
    case "$LLM_PROVIDER" in
        kvmem) mode="kvmem" ;;
        *) mode="" ;;
    esac
    echo "  [LLM] 启动 $LLM_PROVIDER 服务 (${mode:-vanilla})..."
    nohup bash "$LLM_SERVER_SCRIPT" $mode > /tmp/daily-llm-server.log 2>&1 &
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
    # 只关自家启动的实例 (LLM_PID 非空); 复用的外部实例不动
    if [[ -z "$LLM_PID" ]]; then
        return 0
    fi
    echo "  [LLM] 停止自家实例 (pid=$LLM_PID)..."
    kill "$LLM_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$LLM_PID" 2>/dev/null || true
    LLM_PID=""
}

trap stop_llm_server EXIT INT TERM

# 解析 provider/端口（在 trap 之后: resolve 失败 exit 时无需清理本地服务）
resolve_llm_provider

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
