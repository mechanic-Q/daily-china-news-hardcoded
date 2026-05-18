# Roadmap: 每日新中国硬编码采集

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-05-17)
- ✅ **v1.1 Quality Fix** — Phases 6-9 (Phases 6-9 shipped 2026-05-18)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-05-17</summary>

- [x] Phase 1: 基础采集与优化 (1/1 plan) — 7信源全通 + aiohttp并发
- [x] Phase 2: 分类筛选 (1/1 plan) — 8栏目 + 涉华过滤
- [x] Phase 3: 正文提取 (1/1 plan) — 5层策略链
- [x] Phase 4: 摘要生成 (2/2 plans) — MiniMax M2.7 LLM摘要
- [x] Phase 5: 报纸渲染 (2/2 plans) — step8.py + run_all.sh

</details>

<details>
<summary>✅ v1.1 Quality Fix (Phases 6-9) — ALL SHIPPED 2026-05-18</summary>

- [x] Phase 6: 正文提取修复 — 清理JS/CSS/HTML实体混入，改进提取策略
- [x] Phase 7: 左右栏平衡改进 — 纯字数权重穷举分配, WGT-01修复
- [x] Phase 8: 摘要与过滤健壮性 — step4涉华/负面过滤 + step7摘要精简/回退
- [x] Phase 9: 智能分类 — C+D混合（关键词加权+GLM裁决+智能重试）

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|---------------|--------|-----------|
| 1. 基础采集与优化 | v1.0 | 1/1 | Complete | 2026-05-15 |
| 2. 分类筛选 | v1.0 | 1/1 | Complete | 2026-05-15 |
| 3. 正文提取 | v1.0 | 1/1 | Complete | 2026-05-15 |
| 4. 摘要生成 | v1.0 | 2/2 | Complete | 2026-05-16 |
| 5. 报纸渲染 | v1.0 | 2/2 | Complete | 2026-05-17 |
| 6. 正文提取修复 | v1.1 | 1/1 | Complete | 2026-05-17 |
| 7. 左右栏平衡改进 | v1.1 | 1/1 | Complete | 2026-05-17 |
| 8. 摘要与过滤健壮性 | v1.1 | 1/1 | Complete | 2026-05-17 |
| 9. 智能分类 | v1.1 | 1/1 | Complete | 2026-05-18 |
