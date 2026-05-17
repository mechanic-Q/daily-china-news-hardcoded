# Plan 1: 左右栏平衡 — 视觉权重穷举分配 - Summary

**Completed:** 2026-05-17
**Files modified:** step8.py

## What was built

将 `balance_columns()` 从纯字符贪心分配改为视觉权重穷举最优分配。

### Key changes

| Function | Change |
|----------|--------|
| `_estimate_weight(group)` | 新增 — 视觉权重估算：`4.5 + Σ(1.2 + text_len/90 per item)` |
| `balance_columns(sections)` | 重写 — 穷举 2^8=256 种分配方案，选差值最小的 |

### E2E results (2026-05-17 data)

- ✅ HTML 正常生成
- ✅ PNG 正常生成并裁白边
- ✅ 左右栏权重差 4.7（总权重 47.9，约 10%）
- ✅ 输出格式不变

### Requirements covered

- BAL-01: `_estimate_weight()` 权重估算 ✅
- BAL-02: 视觉权重替代纯字符穷举分配 ✅
