---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-02-phase-15b-trafilatura-body
phase: 15b
status: brainstorm-skeleton
---

# Requirements · Phase 15B · trafilatura body extraction

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 运行 `step6.py` 或完整 `run_all.sh` |
| 维护者 | 维护站点 postprocess 规则 |
| 测试者 | 比对 golden set 与历史输出 |

## 功能需求

### FR-01: 使用 trafilatura 提取正文

Given 已安装 `trafilatura`  
When `fetch_and_extract(url, title)` 获取到 HTML  
Then 优先使用 `trafilatura.extract` 得到正文文本

### FR-02: 保留参考消息 fallback

Given URL 属于 `ckxxapp` 或 `cankaoxiaoxi` 且 trafilatura 返回空  
When HTML 中存在 `contentTxt` 变量  
Then 使用现有 JS 变量解析逻辑提取正文

### FR-03: 站点后处理显式化

Given 正文已由 trafilatura 提取  
When URL 属于 CAS / People / CCTV 之一  
Then 通过对应 postprocess function 清理站点噪声

### FR-04: 输出格式不变

Given `step6.py --date YYYY-MM-DD` 运行成功  
Then `2新闻_已审核.md` 的标题、来源、发布时间、正文字段格式保持不变

## 非功能需求

- 正文提取成功率不低于当前基线
- golden set 自动通过率 ≥90% 或人工确认差异为质量提升
- 不改 `run_all.sh`

## 决策覆盖矩阵

正式 brainstorm 时补充 D-xxx。
