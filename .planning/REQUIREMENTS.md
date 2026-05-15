# Requirements: 每日新中国硬编码采集

**Defined:** 2026-05-15
**Core Value:** 从多个中国新闻信源自动、确定性地采集当日新闻

## v1 Requirements

### 基础采集
- [ ] **COL-01**: 7信源每日新闻自动采集
- [ ] **COL-02**: 三淘汰验证（HTTP 200 + 标题 + 日期）
- [ ] **COL-03**: 失败信源标注继续

### 性能与质量
- [ ] **PERF-01**: 代码质量修复（Phase 1）
- [ ] **PERF-02**: 性能优化（Phase 1）
- [ ] **FLTR-01**: 分类筛选（Phase 2）
- [ ] **FLTR-02**: 涉华过滤（Phase 2）

### 正文与渲染
- [ ] **BODY-01**: 正文提取（Phase 3）
- [ ] **REND-01**: 报纸渲染（Phase 4）

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COL-01 | Phase 1 | Complete |
| COL-02 | Phase 1 | Complete |
| COL-03 | Phase 1 | Complete |
| PERF-01 | Phase 1 | Complete |
| PERF-02 | Phase 1 | Complete |
| FLTR-01 | Phase 2 | Pending |
| FLTR-02 | Phase 2 | Pending |
| BODY-01 | Phase 3 | Pending |
| REND-01 | Phase 4 | Pending |
