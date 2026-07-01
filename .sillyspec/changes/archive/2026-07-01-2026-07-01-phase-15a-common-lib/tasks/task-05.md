---
id: task-05
title: 迁移 summarizer 与 renderer 到公共包
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-01]
blocks: [task-08, task-09]
requirement_ids: [FR-03, FR-04, FR-07]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - step7.py
  - step8.py
goal: >
  让 step7.py 与 step8.py 复用公共路径、栏目、星期和参数解析，保持日报素材与渲染输出结构不变。
implementation:
  - 在 step7.py 替换 BASE_DIR、COLUMN_ORDER、parse_args。
  - 在 step8.py 替换 BASE_DIR、COLUMN_ORDER、WEEKDAYS、parse_args。
  - 保留摘要、HTML、截图和裁剪业务逻辑。
acceptance:
  - step7.py 与 step8.py 不再定义重复常量或 parse_args。
  - step7 和 step8 可 import。
  - 两个脚本 dry-run 可运行。
verify:
  - python3 -c "import step7, step8"
  - python3 step7.py --date 2026-06-30 --dry-run
constraints:
  - 不改摘要提示和重试策略。
  - 不改 HTML/CSS/PNG 版式。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
