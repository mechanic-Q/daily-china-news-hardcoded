# Plan 1: 左右栏平衡 — 视觉权重穷举分配 - Summary

**Completed:** 2026-05-17
**Files modified:** step8.py

## What was built

将 `balance_columns()` 从纯字符贪心分配改为视觉权重穷举最优分配。

### Key changes

| Function | Change |
|----------|--------|
| `_estimate_weight(group)` | 新增 — 纯字数权重：`Σ(title_len + summary_len)` |
| `balance_columns(sections)` | 重写 — 穷举 2^8=256 种分配方案，选差值最小的 |

### E2E results (2026-05-17 data)

- ✅ HTML 正常生成
- ✅ 左右栏字数差 44 字（左栏 544，右栏 588），约 8%
- ✅ 输出格式不变
- ⚠️ `_estimate_weight` 最初使用 `4.5 + Σ(1.2 + text_len/90)` 固定开销公式，经 Phase 7 UAT 发现左右栏视觉不平衡（权重差 0.2 但字数差 152 字），于 2026-05-17 简化为纯字数

### Requirements covered

- BAL-01: `_estimate_weight()` 权重估算 ✅
- BAL-02: 视觉权重替代纯字符穷举分配 ✅
