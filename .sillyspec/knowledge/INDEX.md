---
schema_version: 1
doc_type: knowledge-index
author: lmr
created_at: 2026-06-24 18:16:00
---

# Knowledge Index

Daily 项目长期复用知识索引。关键词用 `|` 分隔，用于 execute/brainstorm 阶段命中匹配。

## Conventions
- step|脚本|命令行|入口|argparse → [Step 脚本统一接口](conventions.md#step-脚本统一接口)
- 输出|目录|BASE_DIR|路径|0新闻|1新闻|2新闻|3新闻 → [输出目录规范](conventions.md#输出目录规范)
- 中文|emoji|✅|❌|状态 → [中文 + 状态 emoji 输出风格](conventions.md#中文--状态-emoji-输出风格)
- LLM|openai|SDK|base_url|api_key|zhipu|minimax → [LLM 调用约定](conventions.md#llm-调用约定)
- error|except|try|异常|错误处理 → [错误处理风格](conventions.md#错误处理风格)
- branch|分支|phase|PR → [分支策略](conventions.md#分支策略)

## Patterns
- 文件接力|file relay|markdown|管道|接口契约 → [文件接力模式](patterns.md#文件接力模式-file-relay)
- 涉华|three-tier|回退|fallback|domain|keyword|LLM → [三级回退判定模式](patterns.md#三级回退判定模式-three-tier-fallback)
- 重试|retry|诊断|diagnose|RETRY_PROMPTS|_why_invalid → [智能重试模式](patterns.md#智能重试模式-diagnostic-retry)
- extract_body|5层|多层|提取|extraction|chain → [多层提取策略链](patterns.md#多层提取策略链-layered-extraction-chain)
- chromium|dump-dom|抓取|双通道|fetch → [Chromium 双通道抓取](patterns.md#chromium-双通道抓取-dual-channel-fetch)
- OpenAI 兼容|openai SDK|base_url|provider|zhipu|minimax|9router → [OpenAI 兼容客户端](patterns.md#openai-兼容客户端-openai-compatible-client)

## Known Issues
- minimax|m2.7|model id|涉华|静默 → [MiniMax 模型字符串可能无效](known-issues.md#-minimax-模型字符串可能无效)
- BASE_DIR|硬编码|路径|不可移植 → [BASE_DIR 硬编码](known-issues.md#-base_dir-硬编码)
- except|静默|宽泛|异常吞掉 → [LLM 异常被宽泛 except 静默](known-issues.md#-llm-异常被宽泛-except-静默)
- chromium_dom|重复|step1_3|step6 → [step1_3 / step6 重复定义 chromium_dom](known-issues.md#-step1_3--step6-重复定义-chromium_dom)
- dotenv|env|不一致|load_dotenv → [python-dotenv 在 README 提及但代码未统一使用](known-issues.md#-python-dotenv-在-readme-提及但代码未统一使用)
- balance_columns|O(2^n)|性能|枚举 → [balance_columns O(2^n) 性能上限](known-issues.md#-balance_columns-on-性能上限)
- requirements|版本|依赖|未锁定 → [无 requirements.txt / pyproject.toml](known-issues.md#-无-requirementstxt--pyprojecttoml)
- 信源|URL|硬编码|配置 → [信源 URL/正则硬编码](known-issues.md#-信源-url正则硬编码)
- step5|编号|跳过 → [step5 编号空缺](known-issues.md#-step5-编号空缺)
- snap|chromium|路径 → [chromium snap 路径](known-issues.md#-chromium-snap-路径)
- milestone|v1.0|v1.1|历程|phase → [历史里程碑](known-issues.md#历史里程碑)
