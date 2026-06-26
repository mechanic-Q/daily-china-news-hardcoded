---
schema_version: 1
doc_type: knowledge
category: patterns
author: lmr
created_at: 2026-06-24 18:16:00
---

# Patterns

Daily 项目反复出现、可复用的设计模式。

## 文件接力模式 (File Relay)

模块间通信完全通过 markdown 文件：每个 step 读上一个 step 的输出，无 IPC、无内存共享、无 import 关系。

**优点**：
- 任一 step 独立可运行可重入（同日期可反复跑）
- 失败时可从任一 step 重启，无需重做前置
- `--dry-run` 易于实现（不写文件即可）

**约束**：
- 修改任一 step 的输出格式必须同步更新下游 parser
- 接力文件即"接口契约"，文件名 + 编号前缀（0/1/2/3）不可随意改

参考：`.sillyspec/docs/Daily/flows/daily-pipeline.md`

## 三级回退判定模式 (Three-tier Fallback)

涉华判定（`step4.py`）的典型范式：
1. 最便宜：domain 白名单（O(1) 查 `CHINA_DOMAINS`）
2. 中等成本：keyword 匹配（O(N) 扫 `CHINA_KEYWORDS`）
3. 最贵：LLM 调用兜底（`llm_is_china_related`）

任何新增的"分类/判定/匹配"功能优先考虑这种结构：cheap → medium → LLM。

## 智能重试模式 (Diagnostic Retry)

`step7.py:llm_summarize` 的范式：
1. 调用 LLM
2. 校验输出 → `_why_invalid()` 返回失败原因集合
3. 从 `RETRY_PROMPTS` 字典挑选对应修复提示，注入下次 prompt
4. 重试上限 3 次
5. 仍失败 → `fallback_summarize` 非 LLM 兜底

适用：所有"LLM 输出有可验证质量标准"的场景。

## 多层提取策略链 (Layered Extraction Chain)

`step6.py:extract_body` 的范式：5 个 regex / 规则按优先级依次尝试，前一层失败回退下一层。
1. TRS_Editor / `ozoom`（新华社/人民日报系 CMS）
2. `<article>` / 已知 content class（通用语义化标签）
3. ckxx 特例（`var contentTxt` JS 变量）
4. ckxx 关键词锚定截断
5. `<p>` 段落回退（最后兜底）

加上后处理 + 污染检测 → 失败 → `_aggressive_clean` 重试。

## Chromium 双通道抓取 (Dual-Channel Fetch)

按域名路由：
- `needs_chromium(url)` 判定：cctv/military/cnnc/news.cctv → chromium `--dump-dom`
- 其他：urllib 静态抓取

封装函数 `chromium_dom(url, timeout, budget)` 在 step1_3 和 step6 中**同名定义**（重复代码，未抽公共模块）。

## OpenAI 兼容客户端 (OpenAI-Compatible Client)

通过 `openai` SDK + 自定义 `base_url` 调用国产 LLM：
- Zhipu：`https://open.bigmodel.cn/api/paas/v4/`
- MiniMax：`https://api.minimax.chat/v1`

模式：`OpenAI(base_url=..., api_key=...)` + 标准 `chat.completions.create`。新增 provider（如 9router、SiliconFlow）按同样方式接入即可，无需新 SDK。
