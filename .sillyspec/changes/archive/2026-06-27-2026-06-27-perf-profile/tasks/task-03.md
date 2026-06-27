---
author: lmr
created_at: 2026-06-27 13:49:58
id: task-03
title: 验证 profiler dry-run 报告
priority: P0
estimated_hours: 1
depends_on: [task-01]
blocks: []
requirement_ids: [FR-01, FR-02, FR-04]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - perf_profile.py
  - /mnt/e/每日新中国/**
---

# task-03: 验证 profiler dry-run 报告

## 修改文件

- 不修改源码；会生成或覆盖指定日期 `perf/` 报告文件。

## 覆盖来源

- Requirements: FR-01, FR-02, FR-04
- Decisions: D-001@v1, D-002@v1

## 实现要求

1. 运行 `python3 -m py_compile perf_profile.py`。
2. 选择已有日期，优先使用已有完整 0/1/2/3 产物的日期。
3. 运行 `python3 perf_profile.py --date YYYY-MM-DD --dry-run`。
4. 检查 JSON 报告字段。
5. 检查 Markdown 报告表格和最慢 step 排名。
6. 确认未修改 5 个业务 step。

## 接口定义

验证命令：

```bash
python3 perf_profile.py --date YYYY-MM-DD --dry-run
```

报告路径：

```text
/mnt/e/每日新中国/YYYY-MM-DD/perf/YYYY-MM-DD-profile.json
/mnt/e/每日新中国/YYYY-MM-DD/perf/YYYY-MM-DD-profile.md
```

## 边界处理

- 若 dry-run 某 step 因缺少上游文件失败，报告仍应存在。
- 若没有历史日期目录，记录无法实测原因。
- 不运行完整非 dry-run，避免网络和 LLM 成本。
- 不删除已有 perf 报告。
- 不把失败的 step 判为 profiler 失败，只要报告生成且退出码符合设计即可。
- 不检查业务产物内容正确性。

## 非目标

- 不做性能结论分析。
- 不验证真实非 dry-run 全链路。
- 不优化任何慢 step。

## 参考

- `requirements.md` FR-01/FR-02。
- `design.md` JSON 报告结构。

## TDD 步骤

1. 编译 profiler。
2. dry-run 生成报告。
3. 用 Python 读取 JSON 并检查字段。
4. grep Markdown 关键标题。
5. 汇总结果。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python3 -m py_compile perf_profile.py` | 退出码 0 |
| AC-02 | `python3 perf_profile.py --date YYYY-MM-DD --dry-run` | 生成报告文件 |
| AC-03 | Python 读取 JSON | 必需字段存在，steps 为列表 |
| AC-04 | 检查 Markdown | 含耗时表和 slowest/最慢信息 |
| AC-05 | `git diff --name-only` | 不包含 step1_3/step4/step6/step7/step8 |
