---
author: lmr
created_at: 2026-07-01 18:38:54
schema_version: 1
doc_type: proposal
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
---

# Proposal · Phase 15A common lib

## 动机

Daily 爬虫系统已经从 5 个 step 脚本扩展到包含 `archive_enrich.py`、`news_archive.py`、`monthly_report.py`、`llm_client.py` 的多模块流水线。当前跨 8 个文件重复定义路径、栏目、时区、HTTP helper 与信源识别逻辑，导致后续 Phase 15B–15G 每次优化都要手工同步多处，遗漏风险高。

本 change 先抽出 `daily/` 公共包，把跨模块共享但不属于某个业务 step 的基础能力集中管理，为后续正文提取、异步抓取、信源健康、LLM 批处理、首图质量等 change 打地基。

## 关键问题

1. **重复常量导致变更风险**
   `COLUMN_ORDER` 在 `step4.py`、`step7.py`、`step8.py`、`monthly_report.py` 各写一份；新增/重命名栏目时必须同步多处。

2. **硬编码输出路径限制部署**
   `BASE_DIR = Path("/mnt/e/每日新中国")` 散布在多个文件，WSL 之外无法无痛运行，也不利于测试环境隔离。

3. **HTTP/Chromium helper 重复且默认值不一致**
   `step1_3.py` 和 `step6.py` 都定义 `chromium_dom`、`fetch_html_static`、`ssl_ctx`，但 timeout 默认值不同，后续 15C 性能优化会更难验证。

4. **信源识别逻辑重复**
   `step4.detect_source` 与 `news_archive.infer_source` 逻辑字面一致，修改一个容易漏另一个。

## 变更范围

- 新增 `daily/__init__.py`
- 新增 `daily/common.py`
  - `BASE_DIR` 支持 `DAILY_OUTPUT_DIR` 环境变量并保留 `/mnt/e/每日新中国` 默认值
  - 集中 `COLUMN_ORDER`、`WEEKDAYS`、`CST`
  - 提供 `parse_common_args()`、`today_cst()`、`detect_source()`、`workdir()`
- 新增 `daily/http.py`
  - 集中 `CHROMIUM`、`ssl_ctx`、`fetch_html_static()`、`chromium_dom()`、`_preprocess_html()`
- 修改 8 个调用方 import：`step1_3.py`、`step4.py`、`step6.py`、`step7.py`、`step8.py`、`news_archive.py`、`archive_enrich.py`、`monthly_report.py`
- `.env.example` 追加 `DAILY_OUTPUT_DIR` 示例
- 新增 `tests/manual/test_15a_diff_smoke.py` 手动输出对比脚本

## 不在范围内（显式清单）

- 不换正文提取算法（15B trafilatura 负责）
- 不改抓取并发模型（15C 负责）
- 不加信源健康数据（15D 负责）
- 不做 LLM 批处理（15E 负责）
- 不改首图选择策略（15F 负责）
- 不引入 logging/CI/schema migration（15G 负责）
- 不迁移 `CATEGORY_KEYWORDS`，该常量属于 classifier 领域，继续留在 `step4.py`
- 不修改 `run_all.sh` 运行步骤

## 成功标准（可验证）

- `daily.common` / `daily.http` 可被直接 import
- 未设置 `DAILY_OUTPUT_DIR` 时仍写入 `/mnt/e/每日新中国`
- 设置 `DAILY_OUTPUT_DIR=/tmp/x` 时 `BASE_DIR == /tmp/x`
- 根目录 Python 文件不再定义重复 `COLUMN_ORDER`、`chromium_dom`、`ssl_ctx.verify_mode = ssl.CERT_NONE`
- `news_archive.infer_source(url,{})` 保持可用
- `monthly_report.COLUMN_ORDER` 保持可 import
- `step6.fetch_html_static` 保持可 import（供 archive_enrich 间接兼容）
- `python3 -m pytest tests/` 全绿
- `run_all.sh --date 2026-06-30 --dry-run` 关键输出与 refactor 前一致
