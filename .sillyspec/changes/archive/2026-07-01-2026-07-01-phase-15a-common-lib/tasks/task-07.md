---
id: task-07
title: 更新环境示例与补漏文件
author: lmr
created_at: 2026-07-01 19:08:31
priority: P1
depends_on: [task-01]
blocks: [task-09]
requirement_ids: [FR-02]
decision_ids: [D-003@v1]
allowed_paths:
  - .env.example
  - perf_profile.py
goal: >
  记录 DAILY_OUTPUT_DIR 配置，并消除 perf_profile.py 输出根目录硬编码补漏。
implementation:
  - 创建或更新 .env.example，只写占位 key 与 DAILY_OUTPUT_DIR 示例。
  - 在 perf_profile.py 从 daily.common 导入 BASE_DIR，删除本地硬编码 BASE_DIR。
  - 保持 --output-dir 参数优先级高于默认 BASE_DIR。
acceptance:
  - .env.example 含 DAILY_OUTPUT_DIR 示例且无真实密钥。
  - perf_profile.py 不再硬编码输出根目录。
  - 根目录 Python 中 /mnt/e/每日新中国 字面量只剩 daily/common.py 默认值。
verify:
  - /usr/bin/rg -n 'DAILY_OUTPUT_DIR' .env.example
  - python3 -c "import perf_profile"
constraints:
  - 不读取或复制 .env 真实密钥。
  - 不改 perf_profile.py 报告格式。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
