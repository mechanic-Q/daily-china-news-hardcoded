---
phase: 05-newspaper-render
plan: 01
status: complete
uat: 10/10
rendering_tested: 2026-05-14 (HTML + PNG)
---

# Plan 05-01 — step8.py 报纸渲染引擎

## What Was Built

**`step8.py`** — 独立全流程报纸渲染脚本，不依赖 `render_newspaper.py`。

核心函数：
- `parse_md()` — 解析 `3新闻_概述.md` 为栏目+标题+摘要结构
- `balance_columns()` — 贪心动态平衡算法，按内容长度分配左右栏
- `build_html()` — 1080px 双栏报纸 HTML，含"紫音简报"报头、期号、日期、页脚
- `screenshot_and_crop()` — `/snap/bin/chromium` headless 截图 + Pillow 裁白边

## UAT Results

| # | Test | Result |
|---|------|--------|
| 1 | Syntax check | ✅ pass |
| 2 | Full run exits 0 + HTML + PNG | ✅ pass |
| 3 | dry-run skips PNG | ✅ pass |
| 4 | HTML contains 紫音简报 | ✅ pass |
| 5 | HTML contains 第二十六期 | ✅ pass |
| 6 | HTML contains formatted date | ✅ pass |
| 7 | HTML has left/right columns + grid | ✅ pass |
| 8 | Empty sections skipped | ✅ pass |
| 9 | PNG 2208x2929 @2x scale | ✅ pass |
| 10 | All 8 section headings correct | ✅ pass |

## Key Metrics

- **输出:** 4新闻_报纸.html (6.5KB) + 4新闻_报纸.png (~1MB, 2208x2929)
- **数据:** 10 条新闻解析 / 8 栏目 / 左5栏5条 → 右3栏5条
