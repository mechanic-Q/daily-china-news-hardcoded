---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-03-phase-15c-async-fetch
phase: 15c
status: brainstorm-skeleton
---

# Requirements · Phase 15C · async fetch performance

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 执行每日采集 |
| 维护者 | 维护各信源 fetcher |
| 测试者 | 比较采集耗时与输出格式 |

## 功能需求

### FR-01: 采集使用受控并发

Given 单信源需要多个 HTTP 请求  
When fetcher 执行  
Then 并发请求数不得超过 5

### FR-02: 网络失败自动重试

Given HTTP 请求因超时/临时网络失败异常  
When fetcher 执行  
Then 最多 retry 3 次后才判失败

### FR-03: Chromium 作为 fallback

Given 静态 HTML 可获取且满足解析需求  
When fetcher 解析页面  
Then 不启动 Chromium

Given 静态 HTML 为空/过短/缺关键内容  
When fetcher 解析页面  
Then 使用 Chromium fallback

### FR-04: 输出格式不变

Given `step1_3.py --dry-run` 执行完成  
Then `0新闻_粗筛.md` 预览 Markdown 结构与旧版一致

## 非功能需求

- step1_3 总耗时相比 15A 基线下降 ≥40%
- 单信源失败隔离
- 无新增运行步骤
