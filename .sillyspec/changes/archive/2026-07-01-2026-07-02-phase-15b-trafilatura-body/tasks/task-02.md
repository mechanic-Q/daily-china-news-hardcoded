---
id: task-02
title: 建立 20 条真实信源正文 golden set fixture（覆盖：FR-04, D-004@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on: []
blocks: []
requirement_ids: [FR-04]
decision_ids: [D-004@v1]
allowed_paths:
  - tests/fixtures/body_golden.jsonl
goal: 从 archive/articles/2026-06.jsonl 抽样 20 条 body_status=extracted 记录，保存 source/title/url/old_body，覆盖 6 信源。
implementation:
  - python3 读取 archive/articles/2026-06.jsonl，过滤 body_status=extracted
  - 按来源分层抽样，每源 ≤4 条，覆盖 6 信源
  - 保留 source/title/url/old_body 输出 JSONL，random.seed(42)
acceptance:
  - tests/fixtures/body_golden.jsonl 存在且 20 行，每行含 source/title/url/old_body
  - 至少覆盖 5 个不同信源，每行 non-empty old_body
verify:
  - python3 -c "import json; p='tests/fixtures/body_golden.jsonl'; rows=[json.loads(l) for l in open(p) if l.strip()]; assert len(rows)==20; req={'source','title','url','old_body'}; assert all(req <= set(r) and r['old_body'] for r in rows); assert len({r['source'] for r in rows})>=5; print('OK')"
constraints:
  - 仅允许 tests/fixtures/body_golden.jsonl
  - 随机种子 42，保证复现
  - 不含 HTML 未转义、无敏感信息
  - 数据源 /mnt/e/每日新中国/archive/articles/2026-06.jsonl，运行者确保
---
