---
id: task-03
title: 迁移 classifier 到公共包
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-01]
blocks: [task-08, task-09]
requirement_ids: [FR-03, FR-04, FR-06, FR-07]
decision_ids: [D-002@v1, D-004@v1]
allowed_paths:
  - step4.py
goal: >
  让 step4.py 复用公共路径、栏目、参数解析和信源识别，保持分类、精选与归档调用不变。
implementation:
  - 用 daily.common.BASE_DIR、COLUMN_ORDER、parse_common_args、detect_source 替换本地定义。
  - 保留 CATEGORY_KEYWORDS、过滤规则、LLM 分类和 archive 调用逻辑。
  - 保持 1新闻_链接.md 输出格式。
acceptance:
  - step4.py 不再定义 BASE_DIR、COLUMN_ORDER、parse_args、detect_source。
  - step4 可 import。
  - step4 dry-run 可运行。
verify:
  - python3 -c "import step4; from step4 import COLUMN_ORDER"
  - python3 step4.py --date 2026-06-30 --dry-run
constraints:
  - 不迁移 CATEGORY_KEYWORDS。
  - 不改 MiniMax/Zhipu 调用逻辑。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
