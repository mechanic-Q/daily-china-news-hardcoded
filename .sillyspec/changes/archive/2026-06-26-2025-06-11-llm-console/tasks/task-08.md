---
id: task-08
author: lmr
created_at: 2026-06-24 19:40:00
title: 更新 CLAUDE.md 的 LLM 调用点章节
priority: P1
depends_on: [task-01, task-02]
blocks: [task-09]
requirement_ids: []
decision_ids: []
allowed_paths:
  - /mnt/e/Daily/CLAUDE.md
---

# task-08: 更新 CLAUDE.md 的 LLM 调用点章节

## 修改文件
- 修改 `/mnt/e/Daily/CLAUDE.md`

## 覆盖来源
无 FR/D 覆盖（项目知识维护任务）。

## 实现要求
1. 读取当前 `/mnt/e/Daily/CLAUDE.md` 中的「LLM 调用点（共 3 处）」章节
2. 重写为两个子章节：
   - **LLM 配置管理**：说明 `llm.yaml` 是唯一真相，`llm_client.py` 是抽象层
   - **当前 3 个调用点**：表格式列出 call_site_id → 用途 → 文件位置
3. 不删其他章节，只替换 LLM 调用点章节

## 接口定义

替换章节内容（直接替换现有「LLM 调用点（共 3 处）」章节）：

```
## LLM 调用点（共 3 处）

全部通过 `openai` SDK + 自定义 `base_url` 调用 OpenAI 兼容 API，统一由 `llm_client.py` 管理。

### 配置管理

- **唯一配置**：`llm.yaml` — 改一行即可切换 provider/model/provider
- **抽象层**：`llm_client.py` — `get_client(call_site_id)` 返回 (OpenAI实例, model, kwargs)
- **切换 provider**：改 `llm.yaml` 顶层 `provider: <name>` + `model: <string>` 即可
- **环境变量**：`.env` 中 `NINEROUTER_API_KEY`（主 provider）+ `ZHIPU_API_KEY` / `MINIMAX_API_KEY`（应急保留）

### 调用点总览

| call_site_id | 位置 | 用途 | 关键参数 |
|---|---|---|---|
| `china-relevance` | `step4.py:llm_is_china_related()` | 涉华判定兜底 | temp=0.7, max_tokens=10, timeout=15s |
| `column-classify` | `step4.py:llm_classify_single()` | 8 栏目分类仲裁 | temp=0.7, max_tokens=10, timeout=15s |
| `summarize` | `step7.py:llm_summarize()` | 新闻摘要生成 | temp=0.7, max_tokens=300, timeout=30s, 智能重试×3 |

### 旧 provider 切回

```bash
# 切回 Zhipu GLM-4 Flash
# 编辑 llm.yaml: provider: zhipu, model: glm-4-flash
# 重跑流水线，不需改代码
```
```

## 边界处理
1. **不要全文件替换**：只改 LLM 调用点章节，其他章节不动
2. **保留 CLAUDE.md 顶部模板**：保留 "# CLAUDE.md" 抬头
3. **LLM 调用点原表格的 3 行可删**：旧调用点信息已过时

## 非目标
- ❌ 不改项目概述/管道架构/7 信源/配置文件/分支策略/已知问题等其他章节
- ❌ 不修改 CLAUDE.md 格式（保留原 markdown 风格）

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep "llm.yaml" /mnt/e/Daily/CLAUDE.md` | 找到 |
| AC-02 | `grep "llm_client.py" /mnt/e/Daily/CLAUDE.md` | 找到 |
| AC-03 | `grep "call_site_id" /mnt/e/Daily/CLAUDE.md` | 找到 |
| AC-04 | `grep "china-relevance\|column-classify\|summarize" /mnt/e/Daily/CLAUDE.md \| wc -l` | 输出 ≥ 3 |
| AC-05 | `grep "minimax-m2.7\|glm-4-flash" /mnt/e/Daily/CLAUDE.md` | 不应再出现旧 model 字符串（可选，但推荐清理）|
