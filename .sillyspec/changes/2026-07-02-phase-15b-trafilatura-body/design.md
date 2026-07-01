---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-02-phase-15b-trafilatura-body
phase: 15b
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-skeleton
---

# Design · Phase 15B · trafilatura body extraction

## 设计目标

- 用 `trafilatura` 替代 `step6.py` 中大部分 HTML regex 正文抽取
- 将站点特例从散落 regex 改为可读的 postprocess registry
- 保持 `fetch_and_extract(url, title) -> (body, err)` 外部接口不变
- 保持 `archive_enrich.py` 对 `step6.fetch_and_extract` 的调用不变

## 总体方案

### 1. 获取 HTML

继续使用 15A 后的 `daily.http.fetch_html_static` / `daily.http.chromium_dom`。`needs_chromium(url)` 暂不重写，避免与 15C 交叉。

### 2. 通用正文提取

调用：

```python
from trafilatura import extract

body = extract(
    html,
    output_format="txt",
    include_comments=False,
    include_tables=False,
    favor_precision=True,
)
```

若返回空，进入站点 fallback。

### 3. 参考消息特殊 fallback

`ckxxapp` / `cankaoxiaoxi` 可能正文在 JS 变量 `contentTxt` 中，保留现有专用提取逻辑作为 fallback。

### 4. 站点后处理注册表

```python
SITE_POSTPROCESS = [
    (lambda url: "cas.cn" in url, cas_postprocess),
    (lambda url: "people.com.cn" in url, people_postprocess),
    (lambda url: "cctv.com" in url, cctv_postprocess),
]
```

每个 postprocess 只做站点噪声清理，不再负责寻找正文区域。

### 5. Golden set 回归

从 `archive/articles/2026-06.jsonl` 抽样 20 条 `body_status=extracted` 且覆盖 7 信源的记录，保存 URL、title、old_body。

Manual test 逻辑：
- 对每条重新 `fetch_and_extract`
- 用 `difflib.SequenceMatcher` 计算相似度
- ratio ≥0.85 视为自动通过
- ratio <0.85 输出 diff 供人工判断

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `requirements.txt` |
| 修改 | `step6.py` |
| 新增 | `tests/fixtures/body_golden.jsonl` |
| 新增 | `tests/manual/test_15b_body_golden.py` |

## 兼容策略

- `fetch_and_extract(url, title)` 签名不变
- `needs_chromium(url)` 暂不改变
- 提取失败仍返回 `(None, reason)`
- `2新闻_已审核.md` 格式不变

## 风险

| 风险 | 应对 |
|---|---|
| trafilatura 对 JS 注入正文页无效 | 保留 ckxx/cankaoxiaoxi fallback |
| 新版正文与旧版差异大 | golden set + 人工 diff；新版更干净可更新 golden |
| 依赖安装失败 | requirements 明确新增，verify 阶段 import 检查 |

## 待正式 brainstorm 完善

- golden set 抽样策略细化
- 每个站点 postprocess 规则细化
- trafilatura 参数是否 `favor_precision=True` 还是 `favor_recall=True`
