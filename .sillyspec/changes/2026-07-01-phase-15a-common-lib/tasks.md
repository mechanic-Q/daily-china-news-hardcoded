---
author: lmr
created_at: 2026-07-01 18:38:54
schema_version: 1
doc_type: tasks
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
---

# Tasks · Phase 15A common lib

> 任务细节在 plan 阶段展开；本文件只列任务名、文件路径、覆盖 FR / D。

## Task List

- [ ] T-01 · 新建 `daily/` 公共包
  - 文件：`daily/__init__.py`, `daily/common.py`, `daily/http.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-05, D-001@v1, D-002@v1, D-003@v1

- [ ] T-02 · 迁移 collector 到公共包
  - 文件：`step1_3.py`
  - 覆盖：FR-02, FR-04, FR-05, FR-07, D-002@v1, D-003@v1

- [ ] T-03 · 迁移 classifier 到公共包
  - 文件：`step4.py`
  - 覆盖：FR-03, FR-04, FR-06, FR-07, D-002@v1, D-004@v1

- [ ] T-04 · 迁移 extractor 到公共包并保 re-export
  - 文件：`step6.py`
  - 覆盖：FR-02, FR-04, FR-05, FR-07, D-001@v1, D-002@v1

- [ ] T-05 · 迁移 summarizer 与 renderer 到公共包
  - 文件：`step7.py`, `step8.py`
  - 覆盖：FR-03, FR-04, FR-07, D-001@v1, D-002@v1

- [ ] T-06 · 迁移 archive/news/monthly 兼容层
  - 文件：`news_archive.py`, `archive_enrich.py`, `monthly_report.py`
  - 覆盖：FR-02, FR-03, FR-06, D-003@v1, D-004@v1, D-005@v1

- [ ] T-07 · 文档与环境示例
  - 文件：`.env.example`, `README.md`（如 plan 阶段确认需要）
  - 覆盖：FR-02, D-003@v1

- [ ] T-08 · 手动 diff smoke 脚本
  - 文件：`tests/manual/__init__.py`, `tests/manual/test_15a_diff_smoke.py`
  - 覆盖：FR-07

- [ ] T-09 · 验证
  - 命令：`python3 -m pytest tests/`; import smoke; rg duplicate checks; `run_all.sh --date 2026-06-30 --dry-run`
  - 覆盖：全部 FR 与 D
