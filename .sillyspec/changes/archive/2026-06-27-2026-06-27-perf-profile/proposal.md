---
author: lmr
created_at: 2026-06-27 13:45:31
change: 2026-06-27-perf-profile
stage: brainstorm
doc_type: proposal
---

# Proposal — Phase 12 性能量化

## 动机

当前 Daily 全流水线执行时间变长，但缺少量化数据。用户需要先知道慢在哪里，再进入后续性能优化。

## 变更范围

- 新增 `perf_profile.py` 外部 profiler。
- 修改 `run_all.sh` 增加每步耗时和总耗时输出。
- 输出 JSON + Markdown 性能报告。

## 不在范围内

- 不做性能优化。
- 不并发化任何 step。
- 不改栏目评分算法。
- 不深度插桩所有业务脚本。
- 不改变现有报纸产物语义。

## 成功标准

- 能运行 `python3 perf_profile.py --date YYYY-MM-DD --dry-run`。
- 生成 `perf/YYYY-MM-DD-profile.json` 和 `perf/YYYY-MM-DD-profile.md`。
- 报告包含每个 step 耗时、退出码、最慢 step 排名。
- `run_all.sh` 正常运行时输出每步耗时和总耗时。
