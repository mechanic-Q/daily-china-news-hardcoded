---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-02-phase-15b-trafilatura-body
phase: 15b
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-skeleton
---

# Proposal · Phase 15B · trafilatura body extraction

## 动机

当前 `step6.py` 正文提取依赖 5 层 regex 策略链和大量站点后处理 hack：`TRS_Editor`、`article-content`、`content`、`detail`、`main-content`、`ozoom`、参考消息 JS 变量、CAS 页脚剥离、人民日报 `enpproperty` 剥离、央视播放器 UI 清理等。该方式脆弱、难维护，且每个新站点异常都倾向于再加一条 regex。

Phase 15B 目标是用 `trafilatura` 作为通用正文抽取核心，并把少数站点特例收敛到显式 postprocess registry，从根上降低正文污染和维护成本。

## 关键问题

1. regex 对嵌套 HTML 结构脆弱，容易截断正文或混入 CSS/JS/UI 文本。
2. `_postprocess_text` / `_is_contaminated` / `_aggressive_clean` 是补丁式治理，说明核心抽取层不可靠。
3. 归档增强 `archive_enrich.py` 也依赖 `step6.fetch_and_extract`，正文提取质量会直接影响日归档和月报。

## 变更范围

- `requirements.txt` 新增 `trafilatura>=1.12`
- `step6.py` 使用 `trafilatura.extract(...)` 替代大部分 regex extraction
- 保留 `ckxxapp` / `cankaoxiaoxi` 的 `contentTxt` JS 变量降级路径
- 建立站点后处理注册表：CAS / People / CCTV / default
- 新增 golden set：`tests/fixtures/body_golden.jsonl`（从历史 archive 抽样）
- 新增手动回归：`tests/manual/test_15b_body_golden.py`

## 不在范围内

- 不改 `run_all.sh` 运行步骤
- 不改 `step7.py` 摘要逻辑
- 不改首图选择（15F）
- 不改并发/Chromium 常驻（15C）

## 成功标准

- golden set 20 条中 ≥18 条新旧正文相似度 ≥0.85，或人工标注新版更干净
- `step6.py` 正文提取成功率不低于当前基线
- `step6.py` 行数明显下降（目标 ≤220 行）
- 参考消息 JS 页仍可提取正文
