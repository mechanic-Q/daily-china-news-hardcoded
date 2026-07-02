---
id: task-03
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on:
  - task-01
blocks:
  - task-04
  - task-06
requirement_ids:
  - FR-01
  - FR-02
decision_ids:
  - D-001@v1
  - D-002@v1
  - D-003@v1
allowed_paths:
  - step1_3.py
---

# Task-03: 在 step1_3.py 中实现 _async_fetch_many helper

## Goal

实现 `_async_fetch_many`：httpx.AsyncClient + Semaphore(5) + tenacity retry 3 次的受控并发 fetch helper，保持输入顺序。

## Implementation

1. `step1_3.py` 添加 `import httpx`、`import asyncio`、`from tenacity import retry, stop_after_attempt, wait_exponential`
2. 定义 `async def _async_fetch_many(urls: list[str], semaphore: asyncio.Semaphore = asyncio.Semaphore(5)) -> list[str | None]`，内嵌 `_fetch_one` 闭包
3. `_fetch_one` 用 `@tenacity.retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))` 装饰，`async with semaphore:` 控制并发
4. 外层 `async with httpx.AsyncClient(verify=False) as client`，`asyncio.gather` 收集结果；异常捕获返回 `None`

## Acceptance

- [x] `_async_fetch_many` 签名与 design.md §8.2 一致：入参 `urls: list[str]` + `semaphore`，返回 `list[str | None]`
- [x] 输出列表顺序与 `urls` 输入顺序一致（`asyncio.gather` 保序）
- [x] 网络失败/超时的条目在结果列表对应位置为 `None`

## Verify

```bash
python3 -m py_compile step1_3.py
```

## Constraints

1. 不修改任何 `fetch_*` 函数签名（仍为同步 `def fetch_*(today) -> list[dict{url, title}]`）
2. 不修改 `SOURCES` 列表结构和 `main()` 流程
3. 输出顺序保持 `asyncio.gather` 的输入顺序，不额外排序
