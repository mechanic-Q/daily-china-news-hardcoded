---
id: task-08
title: render_png + write_outputs（含 统计.json）
author: lmr
created_at: 2026-06-29 21:09:11
priority: P1
depends_on: [task-07]
blocks: [task-09]
requirement_ids: [FR-06]
decision_ids: [D-001@v1]
allowed_paths: [monthly_report.py]
goal: >
  调 chromium 截 HTML 为 PNG（Pillow 裁边）并把 md/html/png/统计.json 四件套写入 archive/monthly/YYYY-MM/。
implementation:
  - write_outputs(month, md, html, stats, picks) 创建 MONTHLY_DIR / month 目录
  - 写 {month}_月报.md / {month}_月报.html / {month}_统计.json（json.dumps ensure_ascii=False indent=2）
  - 调 render_png(html_path, png_path)
  - render_png 用 subprocess.run(['/snap/bin/chromium','--headless','--no-sandbox','--screenshot=...','--window-size=1280,2000', f'file://{html_path}'], timeout=60)
  - 用 PIL.Image + ImageChops.difference 裁掉白边（参考 step8 现有实现）
  - chromium 不存在 / 子进程失败 / PIL 不可用 → print ⚠ 后返回 False；main 据此 exit code 2 提示但其他三件套已生成
  - dry_run 时 write_outputs 仅 print 目标路径不写文件
acceptance:
  - 四件套写入正确目录
  - 统计.json 是合法 JSON 且包含 compute_stats 输出全部字段
  - 缺 chromium → md/html/json 仍生成；main 返回 exit code 2
  - dry_run 不创建任何文件
verify:
  - 单测 mock subprocess 与 PIL；验证 dry_run 不写文件
constraints:
  - 不 import step8
  - 不引入 PIL 以外的新依赖
  - 不并发；单进程顺序
  - 写文件前 mkdir parents=True exist_ok=True
