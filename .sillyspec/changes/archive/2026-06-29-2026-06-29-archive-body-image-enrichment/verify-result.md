---
author: lmr
created_at: 2026-06-29 15:23:00
updated_at: 2026-06-29 16:14:00
schema_version: 2
doc_type: verify-result
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
revision: 2
---

# 验证报告

## 结论

**PASS**

change_risk_profile: unit-sufficient（纯 Python 后端函数，无 daemon/session/跨进程/部署路径）

## 任务完成度

| Task | 结果 | 证据 |
|------|------|------|
| task-01 news_archive schema v2 与 IMAGES_DIR | ✅ | `news_archive.py:SCHEMA_VERSION=2`, `IMAGES_DIR`, `__all__` 导出 |
| task-02 14A upsert 保留 14B enrichment 字段 | ✅ | `archive_articles` 合并 `BODY_IMAGE_FIELDS`；`body-failed` 不再降级为 metadata-only |
| task-03 新增 archive_enrich.py CLI 与路径工具 | ✅ | `archive_enrich.py` 含 CLI `--date/--missing-only/--dry-run/--max-seconds` |
| task-04 实现正文补全状态机 | ✅ | `should_enrich_body` + `enrich_body` 仅调用 `step6.fetch_and_extract`，禁 LLM |
| task-05 实现首图提取与下载 | ✅ | `should_enrich_image` + `enrich_image` + `fetch_html_for_image` + `extract_first_image_url`（拒非 http/https） |
| task-06 实现 JSONL enrich 读写与统计 | ✅ | `enrich_records` + `enrich_archive` + `enrich_archive_best_effort` |
| task-07 step4 接入 archive_enrich best-effort | ✅ | `step4.py:run()` 中 try/except 调用 `enrich_archive_best_effort` |
| task-08 新增 tests/test_archive_enrich.py | ✅ | 33 tests pass |
| task-09 扩展 tests/test_news_archive.py | ✅ | 23 tests pass（含 schema v2 + upsert 保留测试） |
| task-10 运行验证命令 | ✅ | 测试通过, dry-run exit 0 |

完成率: 10/10

## 已修复 Blocker（来自 revision 1 FAIL）

| 编号 | 描述 | 修复 |
|------|------|------|
| B-01 | `archive_enrich.py` 未维护 `archive_status` | 在 `enrich_records` 主循环末尾按 body/image 状态计算 `body-image-enriched`/`body-enriched`/`body-failed`/`metadata-only`；budget 路径 `setdefault("archive_status", "metadata-only")` |
| B-02 | `news_archive.archive_articles` upsert 把 `body-failed` 降级 | 排除列表从 `('metadata-only', 'body-failed')` 改为 `('metadata-only',)`，`body-failed` 保留 |
| B-03 | 非 top10 未写 `image_status="not_selected"` | 主路径 `else` 分支 `setdefault("image_status", IMAGE_STATUS_NOT_SELECTED)`；budget 路径 `elif not selected_in_top10` |
| B-04 | `extract_first_image_url` 未拒非 http/https | og:image / twitter:image / `<img>` 三条路径都强制校验 `http://`/`https://`，否则返回 None |
| B-05 | `download_image` 改扩展名时 `image_path` 与 `final_path` 不一致 | `download_image` 改为返回 `(status, error, final_path)`；`enrich_image` 用 `dl_final_path` 写入 record |
| B-06 | 预算测试用 `max_seconds=99999/0`，实际不触发预算 | `test_budget_exceeded_skips_remainder` 改用 `mock.patch("archive_enrich.time.time", side_effect=[0.0, 2.0, ...])` + `max_seconds=1`，在首条记录就触发 budget |

## 决策追踪矩阵

| 决策 ID | FR | Task | Evidence | 状态 |
|---------|----|------|----------|------|
| D-001@v1 | FR-01/FR-03 | task-04/task-05 | `should_enrich_body`（全量）+ `should_enrich_image`（仅 top10） | PASS |
| D-002@v1 | FR-02 | task-04 | `enrich_body` 仅 `fetch_and_extract`；测试 `test_body_no_llm_call` | PASS |
| D-003@v1 | FR-04 | task-05 | `enrich_image` 返回 `image_url` + `image_path`；B-05 已修 | PASS |
| D-004@v1 | FR-05 | task-03/task-06 | `archive_enrich.py` CLI + helper + best-effort | PASS |
| D-005@v1 | FR-06/FR-07 | task-06/task-07 | `enrich_archive_best_effort` catch all + `step4.run` try/except | PASS |
| D-006@v1 | FR-08 | task-02/task-09 | `BODY_IMAGE_FIELDS` 合并；B-02 已修 | PASS |
| D-007@v1 | FR-04 | task-05/task-08 | `fetch_html_for_image` 单独抓 HTML，`fetch_and_extract` 契约不变 | PASS |

## 探针结果

- 未实现标记扫描：变更文件中无 TODO/FIXME/HACK/XXX 匹配
- 设计关键词覆盖：body / image / fetch_and_extract / enrich / dry_run / best_effort / max_seconds / archive_status 全部实现并覆盖
- 测试覆盖：`tests/test_archive_enrich.py`(33) + `tests/test_news_archive.py`(23) = 56 tests, 全部通过
- 决策追踪覆盖：D-001@v1 ~ D-007@v1 全部 FR/task/evidence 闭环

## 测试结果

```
$ python3 tests/test_archive_enrich.py
................................. (33)
Ran 33 tests in 0.006s
OK

$ python3 tests/test_news_archive.py
.......................  (23)
Ran 23 tests in 0.006s
OK

$ python3 archive_enrich.py --date 2026-06-29 --dry-run
═══ 归档增强 ═══
日期: 2026-06-29  补缺失: False  dry-run: True  max秒: 0
  当日无记录: 2026-06-29
(exit 0)
```

## 技术债务

无。

## 代码审查

实现质量良好；测试覆盖充分（56 tests），mock-only 无网络依赖。  
所有 6 个 design.md 一致性 blocker 已修复，决策追踪闭环，无 P0/P1 unresolved。  
变更影响范围小（5 个 brownfield 文件 + 2 个新文件），run_all.sh / 1-3新闻md / HTML / PNG 格式均未改变。

可进入 archive 阶段。
