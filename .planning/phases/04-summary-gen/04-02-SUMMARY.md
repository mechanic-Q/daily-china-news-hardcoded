---
phase: 04-summary-gen
plan: 02
status: complete
improvements_applied: 5
---

# Plan 04-02 — 健壮性改进摘要

## What Was Done

对 `step7.py` 应用了 5 项非阻塞健壮性改进（基于 RESEARCH.md 识别）：

| # | 改进项 | 实现方式 | 验证状态 |
|---|--------|----------|----------|
| 1 | load_dotenv 显式路径 | `load_dotenv(Path(__file__).parent / '.env')` — 从任意目录运行都能找到 .env | ✅ |
| 2 | API 重试机制 | `for attempt in range(2)` — 首次失败后 sleep(2) 重试 1 次 | ✅ |
| 3 | fallback 噪音过滤 | 分句前移除【纠错】/【责任编辑】/记者/编辑/来源/免责声明 | ✅ |
| 4 | API 调用间隔 | 成功 API 调用间 `time.sleep(0.5)` 避免 429 | ✅ |
| 5 | Body 截断提示 | body[:2000] 截断时打印 "⚠ 正文超长截断" | ✅ |

## Key Changes

- **load_dotenv 显式路径** (line 20): 不依赖 CWD
- **重试循环** (line 130-160): 2 次尝试 + sleep
- **噪音过滤** (line 105-106): `body.replace(noise, '')` 在分句前
- **间隔控制** (line 203-204): `time.sleep(0.5)` 仅在 API 成功后

## Regression

`python3 step7.py --date 2026-05-16 --dry-run` — 6/6 API success, clean output
`MINIMAX_API_KEY= python3 step7.py --date 2026-05-16 --dry-run` — 6/6 fallback, no crash
`py_compile` — syntax OK
Total lines: 239

## Connection to Phase 5

Improvements make step7.py more robust for daily use by:
- Not relying on CWD for .env loading
- Surviving transient API failures with retry
- Producing cleaner fallback summaries
- Not overwhelming MiniMax API with rapid-fire calls
