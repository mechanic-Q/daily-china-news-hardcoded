---
status: complete
phase: 08-summary-robustness
source: 8-SUMMARY.md
started: 2026-05-18T00:00:00Z
updated: 2026-05-18T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 负面新闻过滤（D-02）
expected: step4 输出中无含"审查调查/违纪违法/落马/双开/接受审查/涉嫌严重"等关键词的新闻
result: pass

### 2. 涉华过滤——关键词层（D-01）
expected: 含"习近平/中美/神舟/南海/商务部/外交部"等中国关键词的新闻通过初筛，不含任何中国关键词且非中国来源的纯外国新闻被过滤
result: pass

### 3. 涉华过滤——来源白名单（D-01）
expected: 来自 xinhuanet.com/people.com.cn/cctv.com/cas.cn 等中国域名的新闻，即使标题关键词未命中，也进入 LLM 二次确认流程
result: pass

### 4. 涉华过滤——LLM 二次确认（D-01）
expected: 来源为中国域名但标题无明确中国关键词的新闻，LLM 被调用判断是否涉华。输出中显示"LLM裁决"数量。精选总数 ≥ 10 条
result: pass

### 5. 扶贫缩宥（D-03）
expected: 含"乡村振兴"但不含"扶贫/脱贫/精准扶贫"的新闻不归入扶贫栏目。扶贫栏目只在标题明确含扶贫相关词时才填充
result: pass

### 6. 摘要精简（D-04）
expected: step7 输出的摘要为 1-2 句话，每条 30-200 字，不出现 LLM 推理过程（如"用户要求我用..."），不出现正文原文片段
result: pass

### 7. 无效摘要回退（D-05）
expected: API 返回无效摘要（长度<20/含原文片段/CoT推理泄漏）时自动触发规则回退，输出中显示"规则回退"计数
result: pass

### 8. 正文污染——人民日报元数据尾部
expected: step6 提取的正文不含"2026-05-17 00:00:00:0本报记者.../enpproperty-->"等元数据尾部
result: pass

### 9. 正文污染——中科院机构页头+页脚
expected: step6 提取的中科院文章正文不含"中国科学院贯彻落实党中央..."机构介绍，也不含"地址：...邮编：...电话：..."页脚
result: pass

### 10. E2E 管道完整性
expected: step4 → step6 → step7 → step8 全流程无报错，最终输出 HTML+PNG 文件正常生成，精选 ≥ 10 条新闻
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
