---
schema_version: 1
doc_type: module-card
module_id: renderer
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# renderer

## 定位
- 负责：摘要 md → HTML + PNG 双栏中文报纸版面（管道终点，step8.py）
- 不负责：内容生成（summarizer）、内容选取（classifier）、抓取（fetcher）

## 契约摘要
- 输入：`<日期>/3新闻_概述.md`（上游 summarizer 产物）
- 解析 md，按 `COLUMN_ORDER`（8 栏目固定顺序）分组
- `balance_columns` 通过 `1 << n` 子集枚举，最小化左右两栏权重差（`_estimate_weight`）
- 生成 1080px 宽 CSS Grid 单页 HTML（`force-device-scale-factor=2` 实际 2160px）
- Chromium headless `--screenshot` 直接出 PNG（不走 puppeteer/selenium）
- Pillow `ImageChops.difference` 检测纯色底部并裁剪，pad=24
- 输出：`<日期>/YYYY-MM-DD_每日新中国_<中文期号>.html` + `.png`
- `--dry-run` 仅出 HTML，跳过截图

## 关键逻辑
```
parse_md(input_path) → (title_line, sections)
groups = group_by_heading(sections)
ordered = [{heading, items, weight=_estimate_weight(...)} for each group]
n = len(ordered)
best_mask, best_diff = 0, inf
for mask in range(1 << n):                  # O(2^n) 子集枚举
    左右权重 = 按 mask 位拆分累加
    if abs(左-右) < best_diff: 更新 best_mask
left_col, right_col = 按 best_mask 拆 ordered
html = build_html(today, sections, left_col, right_col)
html_path.write_text(html)
若非 dry_run:
    chromium --headless=new --disable-gpu --hide-scrollbars
             --force-device-scale-factor=2
             --window-size=2160,10000
             --screenshot=<png_path>  file://<html_path>
    crop_bottom_whitespace(png_path):
        bg = Image.new(size, pixel(0, h-1))      # 取左下角为底色
        bbox = ImageChops.difference(img, bg).getbbox()
        img.crop(bbox ± pad=24).save(png_path)
```

## 注意事项
- 🟡 `balance_columns` 为 O(2^n) 暴力枚举，n=8 时 256 次循环可忽略；n>20 性能崩盘（当前 8 栏目硬上限）
- 渲染过程无任何 LLM 调用，纯模板 + 浏览器引擎
- chromium 硬编码路径 `/snap/bin/chromium`，缺失直接跳过截图（HTML 仍可用）
- 截图超时 120s（`subprocess.run timeout=120`）
- 期号 `_compute_issue` 以某起始日累计（中文序数 `_chinese_ordinal`）
- 裁白边以左下角像素为参考底色，若版面底部非纯色（如背景插画）会失效
- `--window-size=2160,10000` 高度故意给大值，靠裁剪定底；版面真实高度由内容决定
- 管道终点，修改时无下游模块需要联动；上游契约仅依赖 `3新闻_概述.md` 的 heading/标题结构

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
