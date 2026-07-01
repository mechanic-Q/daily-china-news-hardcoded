---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: brainstorm-skeleton
---

# Design · Phase 15F · image quality

## 总体方案

### 1. 候选来源顺序

1. `trafilatura.extract_metadata(html).image`
2. OpenGraph `og:image`
3. Twitter card `twitter:image`
4. 正文 DOM 范围内第一张满足条件的 `<img>`
5. 全页面 `<img>` fallback（严格过滤）

### 2. 过滤规则

- URL 路径包含 `logo`、`icon`、`nav`、`qrcode`、`二维码`、`favicon` → 跳过
- HEAD/GET Content-Type 非 image → 跳过
- Content-Length < 20KB → 跳过（正式 brainstorm 确认阈值）
- 下载后 Pillow 打开失败 → failed
- 宽高任一 <200 或面积 <200*200 → 删除并跳过

### 3. 状态兼容

继续使用：
- `downloaded`
- `not_found`
- `failed`
- `not_selected`
- `skipped`

若候选图片被过滤到无图，返回 `not_found`。

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `archive_enrich.py` |
| 新增 | `tests/manual/test_15f_image_sample.py` |

## 风险

| 风险 | 应对 |
|---|---|
| 部分站点 og:image 本来就是主图，被正文范围过滤误杀 | 候选顺序保 og/twitter 在前，但仍做尺寸/路径过滤 |
| HEAD 被站点拒绝 | HEAD 失败时直接 GET 并在下载后校验 |
| 过滤过严导致无图 | 记录 not_found，不阻塞归档 |

## 待正式 brainstorm 完善

- 最小尺寸/大小阈值
- 黑名单列表
- 正文 DOM 范围如何复用 15B 结果
