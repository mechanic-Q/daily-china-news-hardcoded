---
author: lmr
created_at: 2026-07-04 00:23:08
---

# Tasks

## Task List

| 任务 | 文件路径 | 覆盖 |
|---|---|---|
| task-01: 新增涉华位串 parser | `step4.py`, `tests/test_step4.py` | FR-01, D-001@v1 |
| task-02: 新增栏目评分矩阵 parser | `step4.py`, `tests/test_step4.py` | FR-02, FR-03, D-003@v1 |
| task-03: 切换涉华 batch prompt 到位串协议 | `step4.py` | FR-01, D-001@v1 |
| task-04: 切换栏目评分 prompt 到矩阵协议 | `step4.py` | FR-02, FR-03, D-001@v1 |
| task-05: 为 low 调用注入 reasoning 和输出预算 | `step4.py`, `llm.yaml` | FR-04, D-004@v1 |
| task-06: 增强空 content 诊断 | `llm_client.py`, `tests/test_llm_client.py` | FR-05, D-004@v1 |
| task-07: 增加 mock batch 端到端测试 | `tests/test_step4.py` | FR-01, FR-02, FR-03, FR-06 |
| task-08: 验证 dry-run 与测试套件 | `step4.py`, `tests/` | 所有 FR |

细节在 plan 阶段展开。
