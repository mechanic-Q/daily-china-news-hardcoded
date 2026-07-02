---
author: lmr
created_at: 2026-07-02 14:34:06
schema_version: 1
doc_type: design
change_id: 2026-07-03-phase-15c-async-fetch
phase: 15c
depends_on:
  - 2026-07-01-phase-15a-common-lib
  - 2026-07-02-phase-15b-trafilatura-body
status: brainstorm-revised
---

# Design · Phase 15C · async fetch performance

## 1. 背景

`step1_3.py` 负责 7 信源采集，串行逐个执行 `SOURCES` 中的 fetcher。其中 `fetch_cas`、`fetch_rmrb`、`fetch_url_title`（回调 fallback）内部存在多个独立串行 HTTP 请求：

- `fetch_cas`：首页静态 HTML → list of URLs → 逐条 `fetch_html_static` 取标题，串行 5-10 次
- `fetch_rmrb`：循环 node_01-09 → 逐版 `fetch_html_static` → 逐条 `fetch_html_static` 取正文标题，串行 10+ 次
- `fetch_url_title`：单个 URL 调用，但采集失败时作为兜底批量触发

此外，多个信源（新华社/央视/央视军事）直接走 Chromium `--dump-dom`，即使静态 HTML 已足够。每启一次 Chromium 子进程浪费 2-5s。

**痛点**：串行批量 HTTP 和过早的 Chromium 调用是 step1_3 的主要耗时来源。

## 2. 设计目标

- **G-01** 将 CAS 和人民日报中的批量串行 HTTP 改为受控并发 `asyncio.Semaphore(5)`
- **G-02** 网络失败自动重试 3 次（指数退避 + jitter），减少临时抖动导致的信源 0 条
- **G-03** 采用 static-first 策略：静态 HTML 可解析则不启 Chromium
- **G-04** 保持 `0新闻_粗筛.md` 输出格式与旧版一致
- **G-05** 保持 `run_all.sh`、`step6.py`、`step7.py` 无变动

## 3. 非目标

- **NG-01** 不改正文提取算法（15B）
- **NG-02** 不改 LLM 分类/摘要（15E）
- **NG-03** 不抽取公共 async helper 到 `daily/http.py`（除非 execute 阶段发现极小 helper 必需）
- **NG-04** 不添加信源健康持久化（15D）
- **NG-05** 不改 `run_all.sh` 编排
- **NG-06** 不改造 SOURCES 信源入口的同步签名

## 4. 拆分判断

Phase 15C 是 15A-15G 系列中的性能改造层，聚焦 collector 单模块。独立拆分理由：
- 15C 改变采集并发模型，可能影响 0新闻_粗筛.md 输出顺序，需独立回归确认
- 15D 不依赖 15C，可并行
- 与 15B（正文抽取）无代码耦合

## 5. 决策/方案选择

### D-001@v1：范围限定 collector 模块
- **选择**：只改 `step1_3.py`，不改 `daily/http.py`、`step6`、`step7`、`run_all.sh`
- **理由**：缩小影响面，保持 15A 的 common lib 不乱
- **覆盖**：FR-01, FR-02, FR-03, FR-04

### D-002@v1：并发 HTTP helper 留在 step1_3.py 内部
- **选择**：在 `step1_3.py` 内部新增 `async def _async_fetch_many(urls, ...)`，不抽出到 `daily/http.py`
- **理由**：避免 15C 触及 common lib 的 HTTP 层，等 15G 工程化阶段统一梳理
- **覆盖**：FR-01

### D-003@v1：并发结果按源 URL 顺序稳定输出
- **选择**：`asyncio.gather` 保持输入顺序，写出前不再重新排序
- **理由**：大部分输出格式依赖 `write_0` 的条目顺序，保持稳定
- **覆盖**：FR-04, G-04

### D-004@v1：timing baseline 采集用手动脚本
- **选择**：创建 `tests/manual/test_15c_step1_timing.py`，运行 15A dry-run 与 15C dry-run 对比
- **理由**：无自动化测试，手动脚本更灵活
- **覆盖**：FR-04 验收

## 6. 总体方案

### Wave 1：依赖与 timing baseline
1. `requirements.txt` 新增 `httpx`、`tenacity`
2. `tests/manual/test_15c_step1_timing.py` 采集 15A baseline 耗时（dry-run 选 2026-06-30）

### Wave 2：async helper + CAS/RMRB 并发化
1. `step1_3.py` 新增 `import httpx`、`import tenacity`
2. 新增内部 async helper：

```python
async def _async_fetch_many(urls, semaphore=asyncio.Semaphore(5)):
    """受控并发 + retry 3 次"""
    @tenacity.retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _fetch_one(client, url):
        async with semaphore:
            resp = await client.get(url, timeout=httpx.Timeout(12.0))
            return resp.text
    async with httpx.AsyncClient(verify=False) as client:
        return await asyncio.gather(*[_fetch_one(client, u) for u in urls])
```

3. `fetch_cas`：改用 `_async_fetch_many` 批量取标题
4. `fetch_rmrb`：改用 `_async_fetch_many` 批量 fetch 版面 + 正文标题

### Wave 3：static-first Chromium fallback
1. `fetch_xinhuanet`、`fetch_cctv_news`、`fetch_cctv_military`：先 `fetch_html_static` 尝试，静态 HTML 可解析则跳过 Chromium
2. 静态为空/过短（<500 字）/缺关键 selector 时回退现有 `chromium_dom`
3. `fetch_home_html` 改为 static-first 模式

### Wave 4：验证
1. 运行 `python3 -m py_compile step1_3.py`
2. 运行 `python3 step1_3.py --date 2026-06-30 --dry-run` 对比输出格式
3. 运行 timing baseline 脚本对比耗时

## 7. 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `requirements.txt` | 新增 `httpx`、`tenacity` |
| 修改 | `step1_3.py` | 新增 async helper、CAS/RMRB 并发化、static-first fallback |
| 新增 | `tests/manual/test_15c_step1_timing.py` | timing baseline + 耗时对比 |

## 8. 接口定义

### 8.1 `main()`、`SOURCES`、各 `fetch_*` 签名不变

所有 fetcher 保持 `def fetch_*(today) -> list[dict{url, title}]` 签名。

### 8.2 新增内部函数

```python
async def _async_fetch_many(urls: list[str], semaphore: asyncio.Semaphore = Semaphore(5)) -> list[str | None]:
    """受控并发抓取多个 URL，保持输入顺序。失败条目返回 None。"""
```

### 8.3 修改函数

- `fetch_home_html(url)` — 改为 static-first（先 urllib，空/短再 chromium）
- `fetch_cas(today)` — 批量标题取 async
- `fetch_rmrb(today)` — 版面扫描+标题取 async

## 9. 数据模型

不改生产数据模型。新增测试脚本仅用于手动 timing，不参与管线。

## 10. 兼容策略

- `python3 step1_3.py --date YYYY-MM-DD [--dry-run]` 保持不变
- `0新闻_粗筛.md` 的 Markdown 结构（标题行/通过淘汰/状态/工具名）保持不变
- SOURCES 列表结构不变，各 fetcher 函数签名不变
- 三淘汰验证的 `verify_http` 的 `asyncio.run` 调用方式不变
- Chromium 不通的机器静态抓取仍可运行（降级路径保持）

## 11. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 并发请求被目标限流 | P1 | Semaphore(5) + User-Agent + exponential backoff |
| R-02 | 输出顺序因并发改变 | P1 | `_async_fetch_many` 保持输入顺序（`asyncio.gather` 保序） |
| R-03 | static-first 判据不准导致正确内容缺失 | P1 | 静态度量判据（空/过短 500 字）；golden 回归 diff 旧版输出 |
| R-04 | httpx 与现有 urllib 行为差异 | P2 | 先只改 CAS/RMRB 标题抓取，不改 src 首页/API 等稳定路径 |
| R-05 | tenacity retry 和现有 try/except 嵌套 | P2 | retry 只包装 HTTP 请求，不包信源级逻辑；外面 try/except 仍兜底 |

## 12. 决策追踪

- D-001@v1 覆盖 FR-01 到 FR-04，对应章节 3, 6, 7
- D-002@v1 覆盖 FR-01，对应章节 5, 6, 8.2
- D-003@v1 覆盖 FR-04，对应章节 5, 8.2
- D-004@v1 覆盖 FR-04 验收，对应章节 6, 7
- 当前无未解决 D-xxx

## 13. 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | FR-01 到 FR-04 均有对应 Wave/Task 覆盖 |
| 决策覆盖 | 通过 | D-001@v1 到 D-004@v1 均明确 |
| 约束一致性 | 通过 | 文件接力、step 独立运行、--date/--dry-run 协议保持 |
| 真实性 | 通过 | SOURCES、fetch_cas/rmrb、verify_http、write_0 均来自 code |
| YAGNI | 通过 | 不做全信源 async、不抽公共层、不改下游 |
| 验收标准 | 通过 | timing script、dry-run 格式对比、py_compile 可验证 |
| 非目标清晰 | 通过 | 明确排除全文/抽象 helper/健康持久化/编排 |
| 兼容策略 | 通过 | CLI、输出格式、SOURCES、fetcher 签名保持 |
| 风险识别 | 通过 | 限流/输出顺序/静态度量/httpx 差异/retry 嵌套 |
| 生命周期契约表 | 不适用 | 无 session/lease/daemon 关键词 |
