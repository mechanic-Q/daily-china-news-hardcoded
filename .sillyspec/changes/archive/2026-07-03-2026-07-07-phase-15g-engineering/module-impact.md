---
author: lmr
created_at: 2026-07-03 21:30:00
schema_version: 1
doc_type: module-impact
change_id: 2026-07-07-phase-15g-engineering
---

# Module Impact · Phase 15G · Engineering Hardening

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| llm-client | 逻辑变更 | llm_client.py, tests/test_llm_client.py | call_llm 异常脱敏：traceback.print_exc → logger 安全摘要；新增 LLMCallError 文案降敏 | false |
| archiver | 数据结构变更 | news_archive.py, tests/test_news_archive.py | 新增 migrate_record，load_month_records 集成 schema migration；默认字段补齐 | false |
| classifier | 新增 | tests/test_step4.py | 纯函数回归测试（24 cases）：keyword/filter/JSON/chunking/score 路径 | false |
| extractor | 新增 | tests/test_step6.py | 纯函数回归测试（15 cases）：postprocess/contamination/CAS/CCTV/ckxx | false |
| orchestrator | 配置变更 | .github/workflows/test.yml, .sillyspec/local.yaml | 新增 CI workflow (push/PR/pytest)；更新 local.yaml 测试命令 | false |

## 未匹配文件

| 文件 | 说明 |
|------|------|
| daily_logging.py | 新增模块，尚未录入 module-map。建议下次 scan 时纳入 |
| .github/workflows/test.yml | CI 配置，不归属于现有模块路径 |

## 跨模块调用关系变更

- llm-client → daily_logging: call_llm 通过 `from daily_logging import setup_logging` 接入日志
- archiver → 自身: migrate_record 仅内部调用 load_month_records，无跨模块接口变更
- 所有 call_llm 调用者（step4/step7/monthly_report）：签名不变，无需修改

## 注意
- daily_logging.py 为新模块入口，后续 scan 应录入 _module-map.yaml
