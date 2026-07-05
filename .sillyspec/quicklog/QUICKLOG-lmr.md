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

## ql-20260704-003-ef92 | 2026-07-04 22:59:00 | Step7 新闻概述正文删除习近平三字
状态：已完成
关联变更：default
文件：step7.py, tests/test_step7.py
结果：summarize_article_worker 在 LLM 和规则回退摘要收敛后新增 summary.replace("习近平", "")；仅处理正文，不影响标题/link/来源。新增 tests/test_step7.py: 3 个测试覆盖 LLM、回退、无敏感词场景。全量 164 passed。

## ql-20260705-001-b3e8 | 2026-07-05 18:00:00 | Step6/7 正文提取必须成功，失败则 pipeline fail closed
状态：已完成
关联变更：default
文件：step6.py, step7.py, tests/test_step6.py, tests/test_step7.py
结果：step6 fetch_and_extract 重写为 _fetch_any 多路重试链：静态抓取失败→静默重试→fallback Chromium；CCTV 优先 Chromium→回退静态。run() 改为 fail closed：正文提取失败 raise SystemExit(1)，不再写占位正文。step7 在 run() 开头拒绝 [正文提取失败:] 正文。新增测试覆盖 fallback、fail-closed 两种行为。全量 169 passed。

## ql-20260705-002-1c3a | 2026-07-05 18:29:33 | Step7/8 概述新闻标注标准新闻来源
状态：已完成
关联变更：default
文件：step7.py, tests/test_step7.py
结果：step7 run() 输出 `### {title}` → `### [{src}] {title}`，来源取自 step4 上游 src 字段，LLM 不参与来源判断。step8 parse_md 天然兼容 `[来源] 标题` 格式，无需改动。全量 170 passed。

## ql-20260705-003-f77d | 2026-07-05 19:37:43 | Step1 HTTP验证至少试3次，失败原因明确
状态：已完成
关联变更：default
文件：step1_3.py, tests/test_step1_3.py
结果：http_200_async() 改为最多试 3 次，每次间隔 0.5s/1s；返回 (ok, reason) 元组；verify_http() 写入真实原因（HTTP 500/timeout/SSL EOF），不再统一写 HTTP非200。aiohttp session 加 User-Agent: Mozilla/5.0。新增测试覆盖成功/失败reasons。全量 172 passed。
