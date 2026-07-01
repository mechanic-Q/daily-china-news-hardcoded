---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-02-phase-15b-trafilatura-body
phase: 15b
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-revised
---

# Design · Phase 15B · trafilatura body extraction

## 1. 背景

`step6.py` 负责从 `1新闻_链接.md` 抓取正文并写入 `2新闻_已审核.md`。当前正文抽取以 HTML regex 策略链为核心：先匹配 `TRS_Editor` / `article` / `content` / `ozoom` 等容器，再用参考消息 `contentTxt` 特例和 `<p>` 拼接兜底，最后靠 `_postprocess_text` / `_is_contaminated` / `_aggressive_clean` 清理污染。

该模式存在三个问题：

- regex 对嵌套 HTML 脆弱，容易截断正文或混入导航、CSS、JS、播放器 UI。
- 站点特例散落在抽取、后处理、污染检测中，维护成本随信源增多而上升。
- `archive_enrich.py` 复用 `step6.fetch_and_extract(url, title)`，正文质量问题会同步污染归档正文和月报素材。

Phase 15B 在 15A common lib 之后执行，用 `trafilatura` 替代大部分通用正文抽取逻辑，并把必要站点特例收敛到显式后处理注册表。

## 2. 设计目标

- **G-01** 优先使用 `trafilatura.extract` 作为通用正文抽取核心，降低 regex 依赖。
- **G-02** 保持 `fetch_and_extract(url, title) -> (body, err)` 外部接口不变。
- **G-03** 保持 `step6.py` 输出 `2新闻_已审核.md` 的标题、来源、发布时间、正文字段格式不变。
- **G-04** 保留参考消息 `ckxxapp` / `cankaoxiaoxi` 的 `contentTxt` fallback，避免 JS 字面量正文页退化。
- **G-05** 将 CAS / People / CCTV 等站点噪声清理组织为可读 postprocess registry。
- **G-06** 建立 golden set 回归，确保成功率不低于旧实现，差异可人工审查。

## 3. 非目标

- **NG-01** 不改 `run_all.sh` 编排。
- **NG-02** 不改 `needs_chromium(url)` 路由规则；15C 再处理异步抓取与 Chromium 策略。
- **NG-03** 不改 `step7.py` 摘要逻辑和 `step8.py` 渲染逻辑。
- **NG-04** 不做正文改写、摘要、润色或 LLM 修复；正文必须来自页面内容。
- **NG-05** 不改 archive schema、图片策略或首图选择；15F 负责图片质量。
- **NG-06** 不引入 Playwright / Selenium 等浏览器新依赖。

## 4. 拆分判断

Phase 15B 是 Phase 15 crawler refactor 系列中的行为变更层：15A 先完成 common lib 抽取，15B 再替换正文抽取核心。它不与 15C/15D/15E 合并，原因如下：

- 15B 改变正文抽取结果，需要 golden diff 独立判断质量变化。
- 15C 属性能/并发改造，若与 15B 混合会让失败来源难定位。
- 15D 属来源健康观测，依赖稳定的正文错误分类，不应与抽取算法替换同批上线。
- 15E 属 LLM batching，与 step6 无直接接口耦合。

## 5. 决策/方案选择

### D-001@v1：通用正文抽取采用 `trafilatura.extract`，而不是继续扩展 regex 容器列表

- **选择**：在 `extract_body(html, url)` 中优先调用 `trafilatura.extract(..., output_format="txt", include_comments=False, include_tables=False, favor_precision=True)`。
- **理由**：正文抽取是成熟通用问题，`trafilatura` 对新闻正文、样板噪声、链接密度有专门策略；继续增加 regex 只会把结构识别和噪声过滤混在一起。
- **取舍**：引入第三方依赖，执行结果可能与旧 regex 不完全一致；用 golden set 与手动 diff 控制风险。
- **覆盖需求**：FR-01。

### D-002@v1：站点特例保留为 fallback / postprocess，不参与通用正文定位

- **选择**：参考消息 `contentTxt` 只在 trafilatura 返回空时作为 fallback；CAS / People / CCTV 噪声清理只在正文已抽出后执行。
- **理由**：将“找正文”和“清噪声”分离，避免站点规则重新变成主抽取链。
- **取舍**：少数站点仍保留定制代码；但定制点集中、可命名、可测试。
- **覆盖需求**：FR-02、FR-03。

### D-003@v1：保持 `fetch_and_extract` 与 `2新闻_已审核.md` 格式稳定

- **选择**：不改函数签名、不改 `(body, err)` 返回约定、不改下游 markdown 字段。
- **理由**：`archive_enrich.py`、`step7.py` 和历史人工流程都依赖该接口/格式。
- **取舍**：新抽取质量元数据暂不暴露；15D 可另行增加健康观测。
- **覆盖需求**：FR-04。

### D-004@v1：回归验证采用历史 archive golden set + 人工 diff

- **选择**：从 `archive/articles/2026-06.jsonl` 抽样 20 条历史 `body_status=extracted` 记录，保存 URL、title、old_body；manual test 用 `SequenceMatcher` 比对。
- **理由**：正文抽取质量不能只看测试通过，必须对真实信源历史样本回归。
- **取舍**：manual test 不进入常规自动化；符合 local.yaml 当前 `test_strategy: skip`，但 verify 阶段必须可手动运行。
- **覆盖需求**：NFR golden set 自动通过率 ≥90% 或人工确认质量提升。

## 6. 总体方案

### Wave 1：依赖与验证基线

1. 新增 `requirements.txt`（或更新已有文件）声明 `trafilatura>=1.12`。
2. 新增 `tests/fixtures/body_golden.jsonl`，字段至少包含 `url`、`title`、`source`、`old_body`。
3. 新增 `tests/manual/test_15b_body_golden.py`，逐条调用 `step6.fetch_and_extract` 并输出 ratio / diff。

### Wave 2：正文抽取核心替换

1. `step6.py` 导入 `trafilatura.extract`。
2. 将 `extract_body(html, url)` 改为：
   - 先调用 trafilatura 通用抽取。
   - 若为空且 URL 属于参考消息，调用现有 `contentTxt` fallback。
   - 若仍为空，返回 `None`。
3. 建立 `SITE_POSTPROCESS`：
   - `cas.cn` → CAS 页眉/页脚清理。
   - `people.com.cn` → `enpproperty` / 时间戳尾部清理。
   - `cctv.com` / `military.cctv` → 播放器 UI 清理。
   - default → HTML unescape、空白归一、重复句去重。
4. `fetch_and_extract` 保持原流程：抓 HTML → `extract_body` → `_postprocess_text(text, url)` → 污染检查 → 返回 `(processed, None)` 或错误原因。

### Wave 3：兼容验证与文档同步

1. 运行 manual golden test，确认 ≥18/20 自动通过，或记录人工确认差异。
2. 运行 `python3 step6.py --date <可用样本日期> --dry-run` 验证输出格式。
3. 若模块文档需要更新，在 archive/scan 阶段同步 `extractor` module card。

## 7. 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增/修改 | `requirements.txt` | 声明 `trafilatura>=1.12` 依赖 |
| 修改 | `step6.py` | 用 trafilatura 替换大部分 regex 正文抽取；保留 `fetch_and_extract` 签名与输出约定 |
| 新增 | `tests/fixtures/body_golden.jsonl` | 真实历史正文 golden set，供 15B 回归 |
| 新增 | `tests/manual/test_15b_body_golden.py` | 手动回归脚本，输出相似度与 diff |
| 修改 | `.sillyspec/changes/2026-07-02-phase-15b-trafilatura-body/design.md` | 本设计文档补齐决策与自审 |

## 8. 接口定义

### 8.1 `fetch_and_extract`

```python
def fetch_and_extract(url, title):
    """抓取 URL 并返回正文。外部接口保持不变。

    Returns:
        (body, None) 成功；(None, reason) 失败。
    """
```

### 8.2 `extract_body`

```python
def extract_body(html, url):
    """返回未经站点后处理的正文纯文本；失败返回 None。"""
```

### 8.3 postprocess registry

```python
SITE_POSTPROCESS = [
    (lambda url: "cas.cn" in url, cas_postprocess),
    (lambda url: "people.com.cn" in url, people_postprocess),
    (lambda url: "cctv.com" in url or "military.cctv" in url, cctv_postprocess),
]


def _postprocess_text(text, url=None):
    """按 URL 命中站点清理函数后，再执行通用清理。"""
```

### 8.4 ckxx fallback

```python
def _extract_ckxx_content_txt(html):
    """从参考消息 contentTxt JS 变量中提取正文；失败返回 None。"""
```

### 8.5 manual golden test

```python
def compare_body(old_body, new_body):
    """返回 difflib.SequenceMatcher ratio。"""
```

## 9. 数据模型

不改生产数据模型、不新增数据库、不改 archive JSONL schema。

新增测试 fixture 为 JSONL，每行结构：

```json
{"source":"人民日报","title":"...","url":"https://...","old_body":"..."}
```

该 fixture 仅用于 manual regression，不被生产管线读取。

## 10. 兼容策略

- `fetch_and_extract(url, title)` 签名和 `(body, err)` 语义不变。
- `needs_chromium(url)` 暂不改变，仍沿用 15A 后的 `daily.http.chromium_dom` / `fetch_html_static`。
- `2新闻_已审核.md` 格式不变，下游 `step7.py` 无需修改。
- 参考消息 `contentTxt` fallback 保留，避免 trafilatura 对 JS 字面量正文返回空。
- 提取失败仍返回 `(None, "未找到正文区域")` 或具体异常字符串。
- 若 trafilatura 结果污染，仍通过 `_is_contaminated` 拦截，避免污染正文进入下游。

## 11. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | trafilatura 对部分中文新闻页抽取为空 | P1 | 保留 ckxx fallback；golden set 覆盖 7 信源；失败输出 URL 与原因 |
| R-02 | trafilatura 输出与旧正文差异大，ratio 低 | P1 | manual test 输出 diff；人工确认新版更干净才接受 |
| R-03 | 第三方依赖安装失败或环境缺包 | P1 | `requirements.txt` 明确声明；verify 阶段执行 import 检查 |
| R-04 | 站点后处理误删正文 | P2 | 后处理函数按站点拆分，golden diff 检测短文本/低 ratio |
| R-05 | `_is_contaminated` 对 trafilatura 输出过严导致误判失败 | P2 | 保留污染检查但根据 golden diff 调整信号，仅拦截 CSS/JS/模板污染 |

## 12. 决策追踪

- D-001@v1 覆盖 FR-01，对应章节：5、6、8.2。
- D-002@v1 覆盖 FR-02、FR-03，对应章节：5、6、8.3、8.4。
- D-003@v1 覆盖 FR-04，对应章节：5、8.1、10。
- D-004@v1 覆盖 golden set 非功能需求，对应章节：5、6、9。
- 当前无未解决 D-xxx；剩余风险见风险登记 R-01 到 R-05。

## 13. 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖 FR-01 到 FR-04 与 golden set 非功能需求 |
| 决策覆盖 | 通过 | 明确 D-001@v1 到 D-004@v1，含取舍与覆盖需求 |
| 约束一致性 | 通过 | 保持文件接力架构、手写 CLI、step6 对外接口不变 |
| 真实性 | 通过 | `step6.py`、`fetch_and_extract`、`archive_enrich.py`、`daily.http` 均来自现有代码/15A 文档 |
| YAGNI | 通过 | 不做并发、首图、摘要、schema、LLM 修正文 |
| 验收标准 | 通过 | golden set ratio、step6 dry-run、import 检查可验证 |
| 非目标清晰 | 通过 | 明确排除 15C/15D/15E/15F 范围 |
| 兼容策略 | 通过 | 签名、返回、输出 markdown 格式均保持稳定 |
| 风险识别 | 通过 | 识别中文页抽取、依赖、误删、污染误判风险 |
| 生命周期契约表 | 不适用 | 本变更不涉及 session / lease / daemon / heartbeat 等生命周期关键词 |
