---
status: complete
phase: 07-column-balance
source: 7-SUMMARY.md
started: 2026-05-17T12:00:00Z
updated: 2026-05-18T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Visual column balance
expected: 左右两栏渲染高度大致接近
result: ✅ 用户反馈"满意" — 纯字数权重，左544字/右588字，差值44字

### 2. No empty columns
expected: 控制台打印的左右栏分配中，每栏至少包含 1 个栏目
result: ✅ 左5栏目, 右2栏目

### 3. HTML renders correctly
expected: HTML 文件能在浏览器中正常打开，显示双栏报纸布局
result: ✅ HTML(9217B) + PNG(1805KB) 正常生成

### 4. Output format unchanged
expected: balance_columns 返回的数据结构不变，下游 build_html() 无需修改
result: ✅ heading/items/weight 字段完整，类型正确

### 5. Optimal split
expected: 左右栏权重差小于最大单个栏目的权重（证明穷举找到了好于随机/贪心的解）
result: ✅ 差值44字(8.4%) 小于最大单栏目502字

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

- WGT-01: 原权重公式 `4.5 + Σ(1.2 + text_len/90)` 使用固定开销，导致左右栏权重差0.2但实际字数差152字（有量无质的"平衡"）。已于2026-05-17修复为纯字数 `Σ(text_len)`。
