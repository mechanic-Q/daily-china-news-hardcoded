---
author: lmr
created_at: 2026-07-01 14:51:33
---

## ql-20260701-001-a7c9 | 2026-07-01 14:51:33 | 修复 step1_3 新闻抓取超时
状态：已完成
文件：step1_3.py, .sillyspec/docs/Daily/modules/collector.md, .sillyspec/changes/default/tasks.md
结果：根因是 Chromium 首页 dump 超时；已改 urllib 首页优先、Chromium 快速降级；2026-07-01 dry-run 7/7 信源通过；unittest discover 75 tests OK。

## ql-20260704-001-8f2a | 2026-07-04 07:50:26 | 修复 Step4 LLM batch 降级不牺牲筛选准确度
状态：已完成
关联变更：2026-07-04-step4-accuracy-guardrails
文件：step4.py, tests/test_step4.py, .sillyspec/changes/default/design.md, .sillyspec/docs/Daily/modules/classifier.md, .sillyspec/changes/2026-07-04-step4-accuracy-guardrails/tasks.md
结果：Step4 恢复严格 index JSON batch 协议；batch 失败先重试再逐条 LLM，score_signals 失败不再生成关键词 fake signals；score_source 明确区分 llm-batch / llm / keyword-fallback；151 tests passed，2026-07-04 dry-run 成功。

## ql-20260704-002-a4d1 | 2026-07-04 20:42:16 | 强制采集见报/发布日期为当天的新闻
状态：已完成
关联变更：default
文件：step1_3.py, step4.py, step6.py, tests/test_step1_3.py, tests/test_step4.py, tests/test_step6.py, .sillyspec/changes/default/design.md, .sillyspec/docs/Daily/modules/collector.md, .sillyspec/docs/Daily/modules/classifier.md, .sillyspec/docs/Daily/modules/extractor.md
结果：collector 增加可信 published_at 硬闸门，见报/发布日期必须等于 --date；中科院只收 tYYYYMMDD_ 当天 URL；中核/cnnpn 无可信日期不进入通过列表；0/1/2 文件传递真实发布时间，不再用运行日期伪造。新增/更新测试覆盖日期解析、同日闸门、Step4/Step6 日期传递；/usr/bin/python3 -m pytest tests/ -q 161 passed；2026-07-04 dry-run 完成且旧中科院 t20260702 不再进入候选。
