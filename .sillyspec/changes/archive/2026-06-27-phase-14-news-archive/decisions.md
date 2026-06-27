---
author: lmr
created_at: 2026-06-27 16:20:00
schema_version: 1
doc_type: decisions
change_id: 2026-06-27-news-archive-core
phase: 14A
---

# Decisions · Phase 14A News Archive Core

## D-001@v1: Phase 14 拆分为 14A/14B/14C
- type: architecture
- priority: P0
- status: accepted
- source: user
- question: Phase 14 是否一次性实现归档、正文图片和月报？
- answer: 拆分：14A 核心 JSONL 归档；14B 正文/图片补全；14C 自动月报。本次只做 14A。
- normalized_requirement: 当前变更不得实现正文、图片下载或月报生成，只实现 metadata + score/signals 归档。
- impacts: [design §4, FR-01, task-01]
- evidence: 用户回答“同意拆分”

## D-002@v1: 14A 只存 metadata + score/signals
- type: boundary
- priority: P0
- status: accepted
- source: user
- question: 14A 第一包是否必须包含正文？
- answer: 14A 只存 metadata + score/signals；正文/图片留 14B，月报留 14C。
- normalized_requirement: JSONL v1 record 中 `archive_status=metadata-only`，不得要求 `body` 或 `images` 字段必填。
- impacts: [design §3, design §8, FR-02]
- evidence: 用户确认“可以”，接受“14A 只存元数据+评分”的解释

## D-003@v1: 默认接入 run_all 但失败不阻断日报
- type: compatibility
- priority: P1
- status: accepted
- source: user
- question: 14A 归档写入如何触发？
- answer: 默认接入 run_all，但归档失败不阻断日报；另提供独立命令补跑历史日期。
- normalized_requirement: step4 或 run_all 触发归档时必须 best-effort catch all exceptions；归档失败不能导致 `run_all.sh` exit 1。
- impacts: [design §5, design §9, R-08, FR-04]
- evidence: 用户回答“可以”

## D-004@v1: 提供独立补跑命令 archive_news.py --date
- type: architecture
- priority: P1
- status: accepted
- source: user
- question: 历史日期如何补归档？
- answer: 新增 `archive_news.py --date YYYY-MM-DD [--dry-run]` 独立补跑。
- normalized_requirement: CLI 手写 parse_args；支持 --date 和 --dry-run；重复运行同一日期必须幂等。
- impacts: [design §5.3, design §7.2, FR-05]
- evidence: 用户确认默认接入 run_all 同时提供独立补跑

## D-005@v1: Phase 13 成果必须保留，先做 Phase 13 再做 Phase 14
- type: dependency
- priority: P0
- status: accepted
- source: user
- question: Phase 14 是否覆盖/替代 Phase 13？
- answer: 不替代。Phase 13 成果必须完整保留，未来执行顺序是先 Phase 13，再 Phase 14。
- normalized_requirement: Phase 14A 设计必须把 Phase 13 commit `b56d2c7` 作为前置；execute 前检查 Phase 13 代码已落地。
- impacts: [design §1, R-01, FR-06]
- evidence: 用户原话“13 的成果一定不能完全丢掉…肯定是先做 13 再做 14”

## D-006@v1: 实现方案选 B helper module
- type: architecture
- priority: P1
- status: accepted
- source: user
- question: 14A 用内联 step4、helper module 还是事件日志+compactor？
- answer: 选择方案 B：新增 `news_archive.py` helper，step4 best-effort 调用，另提供 `archive_news.py --date` 补跑。
- normalized_requirement: 不把所有 JSONL 逻辑内联进 step4；归档逻辑集中在 `news_archive.py`，step4 只负责调用。
- impacts: [design §5, design §6, design §7, FR-03]
- evidence: 用户回答“方案b”

## D-007@v1: 不修改 run_all.sh
- type: consistency
- priority: P1
- status: accepted
- source: design-grill
- question: D-003 说“默认接入 run_all”，是否需要修改 run_all.sh 添加归档 step？
- answer: 不需要修改 run_all.sh。run_all 已默认执行 step4；归档通过 step4 内部 `archive_articles_best_effort` 默认触发即可满足需求，并避免 `set -euo pipefail` 下 shell best-effort 分支。
- normalized_requirement: 本期文件变更清单将 `run_all.sh` 标为不变；step4 内部调用 helper 并 catch all exceptions。
- impacts: [design §5.1, design §6, R-08, FR-04]
- evidence: run_all.sh:36 `STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")`; design grill X-001

## D-008@v1: Upsert 保留 archived_at 并刷新 updated_at
- type: definition
- priority: P1
- status: accepted
- source: design-grill
- question: 同 URL 重复补跑时 `archived_at` 应表示首次入档还是最近更新？
- answer: `archived_at` 表示首次入档时间，upsert 时保留；新增 `updated_at` 表示最近更新。
- normalized_requirement: `write_month_records` upsert 时若 id 已存在，保留旧 `archived_at`，刷新 `updated_at` 和其他可变字段。
- impacts: [design §8, design §9, tests]
- evidence: design grill X-002

## D-009@v1: news_archive 不 import step4
- type: compatibility
- priority: P1
- status: accepted
- source: design-grill
- question: `news_archive.py` 能否复用 `step4.detect_source`？
- answer: 不 import step4，避免 step4 import news_archive 后形成循环依赖。`news_archive.py` 自带 `infer_source(url, article)`。
- normalized_requirement: `news_archive.py` 不得 `import step4`；source 推断逻辑自包含。
- impacts: [design §7.1, R-10, tests]
- evidence: design grill X-003

## D-010@v1: step4 暴露 build_classification_result(today)
- type: architecture
- priority: P1
- status: accepted
- source: design-grill
- question: `archive_news.py --date` 如何补跑而不重写 `1新闻_链接.md`？
- answer: `step4.py` 新增纯数据函数 `build_classification_result(today)`，返回 `(classified, selected)`；`run()` 和 `archive_news.py` 共用该函数。
- normalized_requirement: `archive_news.py` 不调用 `step4.run()`；补跑只写 archive，不写 `1新闻_链接.md`。
- impacts: [design §5.3, design §6, R-09, tests]
- evidence: step4.py:277 `run(today, dry_run)` 当前同时分类+写文件；design grill X-004
