# Phase 6: 正文提取修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 06-fix-body-extract
**Areas discussed:** 清洗层级, 人民日报专用策略, 验证回退, 内容去重

---

## 清洗层级

| Option | Description | Selected |
|--------|-------------|----------|
| 两层都做 | 提取前剥script/style + 提取后解码实体/清理视频标记 | ✓ |
| 只做文本层 | 只在提取后正则清理，不做预处理 | |

**User's choice:** 两层都做（推荐）
**Notes:** HTML实体在提取后统一用html.unescape()解码；视频标记/播放器UI清理具体实现由agent决定

---

## 人民日报专用策略

| Option | Description | Selected |
|--------|-------------|----------|
| 新增层1（最优先） | 在5层前加#ozoom专用层 | |
| 并入现有层2 | 在通用div搜索列表加id="ozoom" pattern | ✓ |
| URL分流专用提取 | 为paper.people.com.cn写独立提取逻辑 | |

**User's choice:** 并入现有层2（听agent建议）
**Notes:** 最小改动，不新增代码路径

---

## 验证回退

| Option | Description | Selected |
|--------|-------------|----------|
| 清理+重试再失败 | 提取→验证→不通过→清理HTML重提取→再验证→不通过→失败 | ✓ |
| 尽力清理后用残留 | 检测到污染后用正则清理，不重试 | |
| 直接标记失败 | 检测到污染直接标记提取失败 | |

**User's choice:** 清理+重试再失败（推荐）
**Notes:** 污染检测用模式匹配（CSS/JS/导航垃圾pattern），具体阈值由agent决定

---

## 内容去重

| Option | Description | Selected |
|--------|-------------|----------|
| 做去重 | 在extract_body()返回前检测连续段落重复并去重 | ✓ |
| 不去重 | 不处理，LLM摘要时自然会被修复 | |

**User's choice:** 做去重（推荐）
**Notes:** 在extract_body()返回前检测连续段落重复并去除

---

## the agent's Discretion

- 视频标记和播放器UI文字的具体清理正则
- 污染检测的具体pattern列表和阈值
- `<p>`标签聚合时的噪声过滤词表更新

## Deferred Ideas

- 左右栏平衡改进 — Phase 7
- LLM报纸概述替换auto-concatenation — 后续milestone
- 代码质量（logging/config/utils提取）— 后续milestone
