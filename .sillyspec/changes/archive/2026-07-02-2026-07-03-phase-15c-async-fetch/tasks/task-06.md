---
id: task-06
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on:
  - task-01
  - task-02
  - task-03
  - task-04
  - task-05
blocks: []
requirement_ids:
  - FR-01
  - FR-02
  - FR-03
  - FR-04
decision_ids:
  - D-001@v1
  - D-002@v1
  - D-003@v1
  - D-004@v1
allowed_paths:
  - .sillyspec/changes/2026-07-03-phase-15c-async-fetch/verification.md
---

# Task-06: 验证 — py_compile + dry-run 格式对比 + timing 对比

## Goal

验证 step1_3.py 语法正确、dry-run 输出格式与旧版一致、async 改造带来可测量的性能提升，确保所有 4 个 FR 按 design.md 验收标准通过。

## Implementation

1. 创建 `.sillyspec/changes/2026-07-03-phase-15c-async-fetch/verification.md`，记录三次验证的结果
2. 运行 `py_compile` 检查语法，运行 dry-run 格式 diff，运行 timing baseline 对比
3. 确认 SOURCES 列表结构、各 fetch_* 签名、run_all.sh 无变更

## Acceptance

- [x] `python3 -m py_compile step1_3.py` 退出码 0
- [x] `python3 step1_3.py --date 2026-06-30 --dry-run` 输出包含 `## {name}（通过N条 / 淘汰N条 / 汇总N条 → 状态）`、`工具:`、`- [{date}] title | url ✅` 等格式元素
- [x] `python3 tests/manual/test_15c_step1_timing.py` 输出 per-source 耗时表且退出码 0，15C 总耗时 <= 15A 总耗时（无明显退化）
- [x] SOURCES 列表、fetch_* 函数签名、run_all.sh 在 git diff 中无变更

## Verify

```bash
python3 -m py_compile step1_3.py
python3 step1_3.py --date 2026-06-30 --dry-run 2>&1 | head -80
python3 tests/manual/test_15c_step1_timing.py
git diff --stat -- step1_3.py requirements.txt tests/manual/test_15c_step1_timing.py
```

## Constraints

1. 只写 verification.md，不修改生产代码或测试脚本
2. 不运行 lint（local.yaml 无 lint 配置）
3. 不运行单元测试（项目无 pytest/单元测试框架）
4. timing 对比不要求严格加速，只检查无倒退
