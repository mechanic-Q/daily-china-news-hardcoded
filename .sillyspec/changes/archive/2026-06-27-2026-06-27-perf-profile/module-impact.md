---
author: lmr
created_at: 2026-06-27 13:59:00
change: 2026-06-27-perf-profile
stage: archive
doc_type: module-impact
---

# Module Impact — Phase 12 性能量化

## 声明范围 (design.md)
- `perf_profile.py` — 新增
- `run_all.sh` — 修改

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| orchestrator | 调用关系变更 | run_all.sh | 增加每步耗时和总耗时输出，set+e/set-e 实现计时 | false |

## 未匹配文件

| 文件 | 说明 |
|------|------|
| perf_profile.py | 新增外部性能量化脚本，不属于现有模块；建议补充到 _module-map.yaml |
