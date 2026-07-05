---
schema_version: 1
doc_type: module-card
module_id: collector
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# collector

## 定位
- 负责：作为流水线第 1 步，从 7 个中国官方/央媒新闻信源采集"当日"新闻链接，做一轮 HTTP-200 可达性校验（不编造 URL），把"信源 → 通过/淘汰条目 + 工具"汇总写入 `0新闻_粗筛.md`，交给下游 classifier。
- 不负责：
  - 不做正文抓取与正文提取（只取链接 + 标题）
  - 不做新闻分类、标签、聚类（那是 step4 的事）
  - 不做内容质量判断、去重，只做"URL 是否 HTTP 200"
  - 不做翻译、不做摘要、不做渲染（那是 step6 / renderer 的事）

## 7 信源一览
| 序号 | 信源 | fetcher 函数 | 工具 |
|------|------|-------------|------|
| 1 | 新华社 news.cn | `fetch_xinhuanet` | chromium --dump-dom |
| 2 | 参考消息 china.cankaoxiaoxi.com | `fetch_ckxx` | urllib JSON API |
| 3 | 央视新闻 news.cctv.com | `fetch_cctv_news` | chromium --dump-dom |
| 4 | 央视军事 military.cctv.com | `fetch_cctv_military` | chromium --dump-dom |
| 5 | 中科院 www.cas.cn | `fetch_cas` | urllib |
| 6 | 中核集团 cnnc.com.cn → cnnpn.cn | `fetch_cnnc`（三级回退） | 降级链 |
| 7 | 人民日报 paper.people.com.cn | `fetch_rmrb` | urllib + node_NN.html 扫描 |

每个信源由 `SOURCES` 列表中一个 `(name, fetcher, tool)` 元组描述；中核集团因降级链返回 `(items, tool)` 元组，其余返回 `items`。

## 契约摘要
- 命令行入口 `python step1_3.py [--date YYYY-MM-DD] [--dry-run]`，由 `parse_args` 解析参数、由 `init` 创建/复用当日工作目录。
- 7 信源以**串行**方式调用各自的 `fetch_*` 函数（详见"关键逻辑"），每个 fetcher 返回 `[{"url": ..., "title": ...}, ...]`，不抛异常时由 `main` 的 try/except 兜底。
- 采集结果先执行见报/发布日期硬闸门：每条 item 必须有可信 `published_at == --date`，否则淘汰；通过日期闸门后再由 `verify_http` + `http_200_async` 用 aiohttp **并发**做 HTTP-200 校验（`TCPConnector(limit=30)`，单 URL `aiohttp.ClientTimeout(total=12)`），分流为 `passed` / `failed`。
- 抓取手段三选一：①外部 chromium 子进程 `chromium_dom`（新华社、央视、央视军事、中核首选）；②`urllib.request` 静态抓 HTML（中科院、人民日报）；③JSON API（参考消息）。
- 最终产物：当日工作目录下的 `0新闻_粗筛.md`（utf-8），每个信源一节，列出"通过/淘汰/工具/状态"，被 classifier (step4) 作为输入。
- `--dry-run` 模式只 print 前 3000 字预览，不落盘。
- 具体导出符号、路径、tags 参考 `_module-map.yaml` 中 `collector` 一节，本卡片不再罗列。

## 关键逻辑
```
main():
    today, dry_run = parse_args()                    # --date / --dry-run
    today, workdir = init(today)                     # 建 YYYY-MM-DD 工作目录
    all_entries = []
    for i, (name, fetcher, tool) in enumerate(SOURCES, 1):
        try:
            if name == "中核集团":
                items, tool = fetcher(today)         # 三级回退，tool 由 fetcher 决定
            else:
                items = fetcher(today)
            # 各 fetcher 实现差异：
            #   fetch_xinhuanet       → chromium_dom(news.cn) + 正则抽 a/href + 标题
            #   fetch_ckxx            → urllib JSON API
            #   fetch_cctv_news       → chromium_dom(news.cctv.com)
            #   fetch_cctv_military   → chromium_dom(military.cctv.com)
            #   fetch_cas             → urllib(cas.cn) 静态 HTML
            #   fetch_cnnc            → cnnc_chromium → cnnc_cnnpn 降级链
            #   fetch_rmrb            → urllib paper.people.com.cn + node_NN.html 扫描
            passed, failed, _ = asyncio.run(verify_http(items, today))
              # aiohttp.ClientSession + asyncio.gather(http_200_async(...))，并发 HTTP 校验
        except Exception as e:
            print(f"❌ 异常: {e}")
            # 信源失败被吞，记 0 条，不阻断后续
        all_entries.append({source, passed, failed, tool})
    write_0(today, all_entries, dry_run)             # 落盘 0新闻_粗筛.md 或 dry-run 预览
```
辅助：`fetch_title(html)` 从 HTML 片段中抽 `<title>` 兜底标题；`CHROMIUM = "/snap/bin/chromium"` 是 chromium 二进制路径常量；`chromium_dom(url, timeout=35, budget=20000)` 用 `--headless=new --disable-gpu --dump-dom` 模式拉到的 HTML（带 budget 截断防爆内存）。

## 注意事项
- chromium 渲染走外部子进程（`chromium_dom`，默认 `timeout=35s`、`budget=20000` 字节），依赖宿主机 snap chromium v147（路径写死在 `CHROMIUM` 常量），CI / 容器 / 别的发行版部署时需自行确认可用，否则 4 个 chromium 信源会全军覆没。
- HTTP-200 校验**只判可达性，不判内容时效**；时效由 `published_at` 硬闸门负责。每个 fetcher 必须提供可信见报/发布日期（URL 日期、API createtime、版面日期或页面明确发布时间），且 `published_at == --date` 才能进入通过列表；缺日期或非当天必须淘汰，不得用运行日期补写。
- 中核集团有 3 级回退（`fetch_cnnc_chromium` → `fetch_cnnc_cnnpn` → ...），改造时注意 `main` 里对"中核集团"做了**特判** —— 这个 fetcher 返回 `(items, tool)` 元组而非 `items`，因为 tool 名取决于实际命中的回退层级。
- 任一信源 fetcher 抛异常会被 `main` 的 `except` 吞掉、记为 0 条，**不会阻断后续信源**；想加新信源时按 `(name, fetcher, tool)` 元组追加到 `SOURCES` 列表即可，无需改 `main`。
- aiohttp 并发上限 `limit=30`、单 URL `timeout=12s`，对慢站点（如人民日报某些版面）可能直接 fail；如需放宽，改 `verify_http` 中的 `TCPConnector` 和 `aiohttp.ClientTimeout`。
- 修改时需同步检查的下游：**classifier（step4）读 `0新闻_粗筛.md` 格式** —— 段落标题 `## {name}（通过.../淘汰.../汇总... → 状态）`、条目行 `- [日期] 标题 | URL ✅`、淘汰行 `（淘汰）标题 | URL | 原因`，这些字面格式是 step4 的解析锚点，**改 `write_0` 前先同步 classifier**。
- `dry_run` 模式不会落盘，只 print 前 3000 字预览，适合调试单信源或重构 `write_0` 时用，不会污染历史目录。
- `_module-map.yaml` 中 `collector.depends_on` 为空（流水线源头），向下被 classifier 单向依赖；新增"依赖"时记得回填 map。

## 人工备注

<!-- MANUAL_NOTES_START -->

## 变更索引

- ql-20260704-002-a4d1 | 强制采集见报/发布日期为当天的新闻
- ql-20260705-003-f77d | Step1 HTTP验证至少试3次，失败原因明确

<!-- MANUAL_NOTES_END -->
