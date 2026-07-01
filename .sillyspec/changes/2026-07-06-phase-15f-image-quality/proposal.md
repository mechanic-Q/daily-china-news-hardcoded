---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
depends_on:
  - 2026-07-01-phase-15a-common-lib
  - 2026-07-02-phase-15b-trafilatura-body
status: brainstorm-skeleton
---

# Proposal · Phase 15F · image quality

## 动机

当前 `archive_enrich.extract_first_image_url` 选图顺序是 `og:image` → `twitter:image` → 第一个 `<img>`。许多新闻站第一个图片可能是 logo、导航图、二维码或装饰图，导致归档首图质量不稳定。

Phase 15F 目标是提升 top10 新闻首图质量：优先正文主图，过滤 logo/小图/无效图，并保留 URL + 本地文件双存储策略。

## 关键问题

1. 第一个 `<img>` 常不是新闻主图。
2. 没有尺寸校验，小 icon 也会下载。
3. 没有域名/路径黑名单，容易抓到 logo/nav/favicons。

## 变更范围

- `archive_enrich.py` 改进 `extract_first_image_url`
- 优先使用 trafilatura metadata image（依赖 15B）
- 兜底在正文范围内找图
- 图片下载后用 Pillow 验证尺寸，过小删除并记 not_found/failed
- 增加黑名单路径/域名规则
- 新增 manual 抽样检查脚本

## 不在范围内

- 不改正文提取（15B）
- 不改 archive schema 大版本
- 不改图片存储路径约定 `archive/images/YYYY-MM/`

## 成功标准

- 随机抽 top10 图 10 天，人工目测 ≥8/10 是新闻主图（非 logo/装饰）
- 小于 200x200 的图片不保留
- `image_status` 语义保持兼容
