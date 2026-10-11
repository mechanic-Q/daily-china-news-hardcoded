#!/usr/bin/env bash
# run_all.sh — 全管道串联（Windows Git Bash 原生）
# 用法: ./run_all.sh [--date YYYY-MM-DD] [--dry-run]
#       无 --date 则默认今天
# 历史: 2026-10-12 前跑在 WSL2（WSL venv + /snap/bin/chromium + ss 端口互斥）；
#       LLM 后端迁 Windows 原生 Strata 后随迁（ADR-0005），WSL 路径与端口互斥机制退役。

set -euo pipefail

export PYTHONUTF8=1   # 中文输出/文件 IO 统一 UTF-8（Windows 默认 cp936 会炸中文管道）

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
PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
if [[ ! -x "$PYTHON" ]]; then
    echo "错误: 项目虚拟环境不存在；请运行: py -3 -m venv .venv && .venv/Scripts/pip install -r requirements.txt" >&2
    exit 1
fi

# --- 本地 LLM 服务生命周期 (provider 由 llm.yaml 决定, 端口从 base_url 解析) ---
# issue #62: provider: strata → start-llm.sh @ 8080 (Windows 原生 Strata 引擎);
# 云 provider (zhipu/minimax) 无本地实例, 跳过启停。
# 互斥口径 (ADR-0005): nvidia-smi 显存阈值取代 WSL 时代的 ss 端口清单 —— WSL 侧 CUDA
#   负载在 Windows nvidia-smi 同样可见, 覆盖一切 GPU 占用方。
# 所有权语义 (2026-09-24 沙箱测试误杀生产实例的教训, 沿用):
#   - 自启动的实例 → trap 退出时 taskkill 树杀 (用完必关)
#   - 端口上已在线的实例 → 复用但退出时**不杀** (可能是用户/上游手动启动)
#   - GPU 被占 / 端口被占但健康检查未过 → 拒绝启动报错退出, 绝不替用户杀
LLM_SERVER_SCRIPT="$SCRIPT_DIR/start-llm.sh"
LLM_OWNED=""

_llm_provider_base_url() {
    "$PYTHON" - "$SCRIPT_DIR/llm.yaml" <<'PYEOF'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
prov = cfg["providers"][cfg["provider"]]
print(prov["base_url"])
PYEOF
}

_llm_provider_name() {
    "$PYTHON" - "$SCRIPT_DIR/llm.yaml" <<'PYEOF'
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

# 本专属端口上实际监听的 Windows PID (netstat -ano 末列; tr 去 CR 防正则失配)
port_pid() {
    netstat -ano 2>/dev/null | tr -d '\r' | awk -v p=":${LLM_SERVER_PORT}" \
        '$1=="TCP" && $2 ~ p"$" && $4=="LISTENING" && $5 ~ /^[0-9]+$/ {print $5; exit}'
}

# GPU 显存占用 MiB (含 WSL 侧 CUDA 负载; 空闲基线 ~600MB)
vram_used_mb() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' \r'
}

start_llm_server() {
    if [[ -z "$LLM_SERVER_PORT" ]]; then
        echo "  [LLM] provider=$LLM_PROVIDER 为云端 API，跳过本地服务启停"
        return 0
    fi
    local existing used
    existing=$(port_pid)
    if [[ -n "$existing" ]] && llm_server_up; then
        echo "  [LLM] 端口 $LLM_SERVER_PORT 已有实例在线 (pid=$existing)，复用，退出时不关闭"
        LLM_OWNED=""   # 非自家启动, 退出时不杀
        return 0
    fi
    used=$(vram_used_mb)
    if [[ "${used:-0}" -gt 2000 ]]; then
        echo "错误: 16G 显存互斥: GPU 已占用 ${used}MiB (空闲基线 ~600MB)。" >&2
        echo "      Strata 需 ~15.7GB, 双负载必 OOM；请先停对方 (若 Strata 正在加载请等待)。" >&2
        exit 1
    fi
    if [[ -n "$existing" ]]; then
        # 目标端口被占但健康检查未过: 可能是用户正在手动启动 (模型加载 1-5 分钟)。
        # 分不清自家残留与用户进程 → 报错退出, 不替用户杀 (与所有权语义一致)
        echo "错误: 端口 $LLM_SERVER_PORT 被占用 (pid=$existing) 但服务未就绪。" >&2
        echo "      若是自家残留请手动清理 (taskkill //PID $existing //T //F) 后重跑; 若是用户正在启动请等待。" >&2
        exit 1
    fi
    if [[ ! -f "$LLM_SERVER_SCRIPT" ]]; then
        echo "  [LLM] ⚠ 找不到 $LLM_SERVER_SCRIPT，跳过自动启动（需手动启动 LLM 服务）"
        return 0
    fi
    echo "  [LLM] 启动 $LLM_PROVIDER 服务..."
    nohup bash "$LLM_SERVER_SCRIPT" > /tmp/daily-llm-server.log 2>&1 &
    LLM_OWNED=1   # 所有权标记; 停止时按端口回读 Windows pid 再杀 ($! 是 MSYS 伪 pid, taskkill 不认)
    local i
    for i in $(seq 1 150); do
        if llm_server_up; then
            # 83GB 权重冷加载可到 5 分钟
            echo "  [LLM] 就绪 (pid=$(port_pid))"
            return 0
        fi
        sleep 2
    done
    echo "错误: LLM 服务 300s 内未就绪，日志: /tmp/daily-llm-server.log (+ /tmp/strata-daily.log)" >&2
    echo "      注意: 加载中的实例可能仍在后台初始化, 稍后重试或手动结束 python/strata 进程" >&2
    stop_llm_server
    exit 1
}

stop_llm_server() {
    # 只关自家启动的实例 (LLM_OWNED 非空); 复用的外部实例不动。
    # 杀法: 按端口回读 Windows pid 再 taskkill //T 树杀 —— $! 是 MSYS 伪 pid, taskkill 不认。
    # server.py 被硬杀没有优雅卸载路径, 必须连 engine 子进程一起, 否则显存残留;
    # 若 engine 仍脱离进程树幸存, 按 GPU 计算进程表定点补杀。
    if [[ -z "$LLM_OWNED" ]]; then
        return 0
    fi
    local srv orphan used
    srv=$(port_pid)
    if [[ -n "$srv" ]]; then
        echo "  [LLM] 停止自家实例 (pid=$srv, 树杀)..."
        taskkill //PID "$srv" //T //F >/dev/null 2>&1 || true
    else
        echo "  [LLM] 停止自家实例 (端口上无监听, 实例可能仍在加载)..."
    fi
    sleep 2
    used=$(vram_used_mb)
    if [[ "${used:-0}" -gt 2000 ]]; then
        for orphan in $(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>/dev/null | tr -d '\r' | awk -F', ' '$2 ~ /strata.exe/ {print $1}'); do
            echo "  [LLM] 清杀脱离进程树的 engine: pid=$orphan"
            taskkill //PID "$orphan" //F >/dev/null 2>&1 || true
        done
        sleep 3
        used=$(vram_used_mb)
    fi
    if [[ "${used:-0}" -gt 2000 ]]; then
        echo "  [LLM] ⚠ 退出后 GPU 仍占用 ${used}MiB —— engine 残留清杀失败, 请查任务管理器"
    fi
    LLM_OWNED=""
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
        overview="E:/每日新中国/$DATE/3新闻_概述.md"
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
