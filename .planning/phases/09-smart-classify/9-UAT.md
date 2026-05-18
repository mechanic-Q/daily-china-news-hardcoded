---
status: complete
phase: 09-smart-classify
source: 9-SUMMARY.md
started: 2026-05-18T00:00:00Z
updated: 2026-05-18T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 歧义词修复——火箭炮不再误归科研
expected: "箭啸喀喇昆仑——火箭炮分队训练影像" 归入 🎖️ 军事，而非 🔬 世界性科研突破
result: pass

### 2. 关键词覆盖——常见新闻有栏目得分
expected: 大部分新闻关键词得分 ≥1（不再是全0），宽泛词改善覆盖率
result: pass

### 3. LLM 分类——关键词无法判断时 GLM 正确分类
expected: GLM-4 Flash 逐条分类，137 条→57 条成功，产出 5 栏目
result: pass

### 4. 优先度排序——高分类得分文章排前面
expected: "箭啸喀喇昆仑"(军事=9) 排军事第一，"国际博物馆日"(0) 排后面
result: pass

### 5. 每日精选 ≥10 条
expected: step4 在两个不同日期（5/17, 5/18）均产出 ≥10 条精选
result: pass

### 6. CAS 正文污染——正文不含机构描述
expected: step6 提取的 CAS 正文不含"贯彻落实党中央"机构描述
result: pass

### 7. LLM 摘要智能重试——API 100% 成功，0 回退
expected: 5/18 step7 API 10/10 成功，0 条规则回退，摘要 36-74 字
result: pass

### 8. 单栏布局——单栏时居中，无空白右栏+分割线
expected: 单栏时用 single-col CSS 居中布局，不显示分割线
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
