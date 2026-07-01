---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: brainstorm-skeleton
---

# Requirements · Phase 15F · image quality

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 运行 archive_enrich 自动补图 |
| 维护者 | 调整图片过滤规则 |
| 月报读者 | 看到更可靠的新闻主图 |

## 功能需求

### FR-01: 优先选择主图候选

Given HTML 中存在 metadata image 或正文主图  
When `enrich_image` 执行  
Then 优先使用主图候选，而不是导航/logo 图片

### FR-02: 过滤明显无效图片

Given 候选图片 URL 或尺寸显示它是 logo/icon/nav/qrcode/favicons  
When 下载/校验图片  
Then 跳过该候选

### FR-03: 保持 image_status 兼容

Given 所有候选都被过滤或未找到  
When `enrich_image` 返回  
Then `image_status` 为 `not_found` 而不是新增状态

### FR-04: 本地文件质量校验

Given 图片下载成功但 Pillow 判断尺寸过小  
When 校验执行  
Then 删除本地文件并继续找下一个候选或返回 not_found

## 非功能需求

- top10 图片人工抽样 ≥80% 为新闻主图
- 不改变 archive images 路径结构
- 下载失败不得阻塞正文归档
