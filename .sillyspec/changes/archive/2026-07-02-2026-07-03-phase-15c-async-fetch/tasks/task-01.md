---
id: task-01
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on: []
blocks: []
requirement_ids:
  - FR-01
  - FR-02
decision_ids:
  - D-001@v1
allowed_paths:
  - requirements.txt
---

# Task-01: 新增 httpx/tenacity 依赖声明到 requirements.txt

## Goal

为 step1_3.py 的 async HTTP 并发与自动重试提供包依赖声明。

## Implementation

1. `requirements.txt` 追加一行 `httpx`
2. `requirements.txt` 追加一行 `tenacity`
3. 保持已有依赖项顺序，新加行放在文件末尾

## Acceptance

- [x] `python3 -c "import httpx; import tenacity"` 退出码 0
- [x] `requirements.txt` 包含 `httpx` 和 `tenacity` 两行
- [x] 已有依赖项不受影响

## Verify

```bash
python3 -c "import httpx; import tenacity"
```

## Constraints

1. 只修改 `requirements.txt`，不碰其他文件
2. 不指定版本号（由 pip 解析器自动选取兼容版本）
3. 不修改已有依赖项的内容或顺序
