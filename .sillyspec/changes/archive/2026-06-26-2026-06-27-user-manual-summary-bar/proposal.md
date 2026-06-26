---
author: lmr
created_at: 2026-06-27 03:10:26
change: 2026-06-27-user-manual-summary-bar
stage: brainstorm
doc_type: proposal
---

# Proposal — 用户手册与顶部总摘要栏移除

## 动机

用户需要一个可自查的项目手册，集中说明 Daily 项目功能、运行方式、sillyspec 流程、计时方法、故障排查和后续路线。

同时当前报纸渲染会在大标题下方自动生成“所有新闻总和”摘要栏。用户明确表示不想要该栏目，希望标题下方直接进入各栏目新闻正文。

## 变更范围

- 修改 `step8.py`：删除顶部全局摘要栏。
- 新增 `USER_MANUAL.md`：单文件用户手册。
- 保留现有 `run_all.sh`、各 step CLI、文件接力输入输出格式。

## 不在范围内

- 不调整栏目评分算法。
- 不做性能量化或性能优化。
- 不新增摘要栏开关。
- 不拆多份文档。

## 成功标准

- `step8.py` 生成的 HTML 不再包含 `<div class="summary">`。
- `python3 -m py_compile step8.py` 通过。
- `python3 step8.py --date <已有日期> --dry-run` 可生成 HTML。
- `USER_MANUAL.md` 覆盖用户确认的全部手册范围。
