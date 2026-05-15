# Phase 3 Summary: 正文提取

**Phase:** 3 — 03-body-extract
**Completed:** 2026-05-15

## What Was Built

`step6.py`（165行）——从 `1新闻_链接.md` 读取精选新闻 URL，经 5 层策略链提取正文，输出 `2新闻_已审核.md`。

## Accomplishments

- 5 层策略链：TRS_Editor → 通用容器 → 参考消息关键词 → `<p>` 兜底 → CCTV chromium
- 信源分流：静态源 urllib（快），央视系/中核集团 chromium（完整 DOM）
- 无正文长度限制
- `--date` / `--dry-run` 参数
- 央视干扰词过滤（copyright/icp/登录/央视网/二维码）

## Verification

- 语法检查通过
- 静态源正文提取成功（3篇文章总共 2260 字）
- 验证用例：10 条待处理（含静态 + CCTV）

## Key Metrics

| Metric | Value |
|--------|-------|
| 代码行数 | 165 |
| 策略层数 | 5 |
| 验证用例 | 3/3 静态源通过 |
| 正文上限 | 无 |
