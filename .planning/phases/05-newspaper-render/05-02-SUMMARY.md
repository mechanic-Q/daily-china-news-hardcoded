---
phase: 05-newspaper-render
plan: 02
status: complete
---

# Plan 05-02 — run_all.sh 全管道串联

## What Was Built

**`run_all.sh`** — Bash 脚本串联 step1_3.py → step4.py → step6.py → step7.py → step8.py。

- `--date YYYY-MM-DD` 必填参数，传递到每一步
- `--dry-run` 可选，透传给每一步
- `set -euo pipefail` 严格错误处理
- `SCRIPT_DIR` 相对路径解析，可从任意目录运行
- 某步失败立刻停止并输出错误信息
