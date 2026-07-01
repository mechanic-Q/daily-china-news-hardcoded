---
author: lmr
created_at: 2026-07-02 01:33:35
schema_version: 1
doc_type: module-impact
change_id: 2026-07-02-phase-15b-trafilatura-body
---

# Module Impact — Phase 15B · trafilatura body extraction

## 三重交叉验证

| 来源 | 文件清单 |
|---|---|
| design.md 变更范围 | requirements.txt, step6.py, tests/fixtures/body_golden.jsonl, tests/manual/test_15b_body_golden.py |
| tasks.md 任务范围 | requirements.txt, step6.py, tests/fixtures/body_golden.jsonl, tests/manual/test_15b_body_golden.py |
| git diff 真实变更 | requirements.txt, step6.py |

一致性：设计声明与真实代码变更一致。tests/fixtures/body_golden.jsonl 和 tests/manual/test_15b_body_golden.py 为新增 fixture/script，未出现在 git diff（属于新文件，diff 只显示已有文件变更），在 untracked 范围内。

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|---|---|---|---|---|
| extractor | 逻辑变更 | step6.py | 正文抽取核心从 5 层 regex 替换为 trafilatura.extract；ckxx fallback 抽出为独立函数；站点后处理收敛为 SITE_POSTPROCESS registry；_postprocess_text 增加 url 参数 | false |
| (无模块映射) | 新增 | requirements.txt | 新增 trafilatura>=1.12 依赖声明 | false |
| (无模块映射) | 新增 | tests/fixtures/body_golden.jsonl | 20 条真实信源正文 golden set，覆盖 6 信源 | false |
| (无模块映射) | 新增 | tests/manual/test_15b_body_golden.py | 手动回归脚本，输出 ratio/diff/summary | false |

## 未匹配文件

| 文件 | 说明 |
|---|---|
| requirements.txt | 顶层依赖声明。不属于 _module-map.yaml 中任何模块路径（模块路径均为 `.py` 文件）。建议在 scan 阶段考虑将其映射至对应模块或创建 `root` 模块条目。 |
| tests/fixtures/body_golden.jsonl | 测试 fixture，不在模块映射路径内。 |
| tests/manual/test_15b_body_golden.py | 手动测试脚本，不在模块映射路径内。建议关联至 extractor 模块。 |

## 影响分析

- step6.py（extractor 模块）是本 change 唯一实质逻辑变更的已有模块。
- requirements.txt 为新增顶层文件（此前项目无正式依赖声明），不归属任何现有模块。
- 测试 fixture 与手动测试脚本为新增辅助文件。
- 下游模块（summarizer/step7、archiver/archive_enrich）接口不受影响 — fetch_and_extract 签名、2新闻_已审核.md 输出格式均保持。
- 影响范围：单模块 + 辅助文件，无跨模块接口变更。
