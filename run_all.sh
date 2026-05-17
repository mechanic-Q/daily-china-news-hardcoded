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

STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")

for step in "${STEPS[@]}"; do
    echo ""
    echo "═══ 运行: $step --date $DATE $DRY_RUN ═══"
    python3 "$SCRIPT_DIR/$step" --date "$DATE" $DRY_RUN
    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo "❌ $step 失败，停止执行"
        exit 1
    fi
done

echo ""
echo "✅ 全管道完成: $DATE"
