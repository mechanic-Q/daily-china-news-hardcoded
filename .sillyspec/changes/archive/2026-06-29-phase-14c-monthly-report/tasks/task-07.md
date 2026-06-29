---
id: task-07
title: render_markdown + render_html
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-03, task-04, task-06]
blocks: [task-08, task-09]
requirement_ids: [FR-06]
decision_ids: [D-001@v1]
allowed_paths: [monthly_report.py]
goal: >
  生成可发布月报的 Markdown 与 HTML 字符串，含统计、总述/趋势、每栏目代表新闻，缺图占位。
implementation:
  - render_markdown(month, stats, picks, overview) 返回完整 markdown 字符串
    - 标题 `# 每日新中国 · 月报 · {month}`
    - 总述段（来自 overview）
    - 统计表（栏目分布 / 信源分布 / body coverage）
    - 每栏目按 COLUMN_ORDER 顺序列出 Top N：`### {column}` + 每篇 `- [{title}]({url}) — {source} · {date}` + body[:200]
    - 有 image_path 时追加 `![](file:///{abs_path})`，缺图用占位符 `（无图）`
  - render_html(month, stats, picks, overview) 内联 CSS（参考 prototype-monthly-report.html），单文件可浏览器直接打开
    - 双栏报纸样式；overview/统计在头部；代表新闻按栏目分块；首图缩略
    - 字符转义用 html.escape
acceptance:
  - md/html 内含所有 picks 的 url 与 source
  - 缺 image_path 时输出占位符不报错
  - html 浏览器直接打开样式正常
verify:
  - 单测：构造样本 stats/picks → 快照断言含 url、source、date 字段
constraints:
  - 不 import step8
  - 不调用 chromium
  - 不下载图片（仅引用本地 image_path）
  - 不写文件（task-08 负责落盘）
