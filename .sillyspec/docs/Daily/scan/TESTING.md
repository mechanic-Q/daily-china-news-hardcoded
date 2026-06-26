---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# TESTING — 每日新中国 · Daily China News

## 现状结论

**本项目无任何自动化测试。** 经全仓 `rg` 搜索确认：

- 无 `import pytest` / `import unittest`（`rg "import pytest|import unittest" *.py` → 0 matches）
- 无 `test_*` 函数命名（`rg "def test_" *.py` → 0 matches）
- 无 `tests/`、`test/` 目录
- 无 `*.test.py`、`*_test.py` 文件
- 无 `conftest.py`、`pytest.ini`、`tox.ini`、`.github/workflows/` 中的 CI 测试配置
- 5 个 step 脚本（step1_3 / step4 / step6 / step7 / step8）均为生产代码，未含 self-test

## 现有 QA 手段（人工 / 半自动）

1. **`--dry-run` 预览模式**
   - 每个 step 脚本支持 `--dry-run`，仅打印结果不写文件
   - 用法：`python3 step4.py --dry-run --date 2026-06-22`
2. **手工日期回放**
   - 通过 `--date YYYY-MM-DD` 参数复跑历史日期
   - 用法：`python3 stepN.py --date 2026-05-17` 对比 `/mnt/e/每日新中国/2026-05-17/` 旧产物
3. **UAT 流程存档**
   - `.planning/phases/0[1-9]-*/verify.md` 中存档了每个 phase 的人工验收步骤
   - 9 个 phase（01-core-collection ... 09-smart-classify）已 ship 并附 UAT 记录
4. **端到端冒烟**
   - `./run_all.sh` 完整跑一次（包含真实 LLM 调用 + Chromium 截图）
   - 通过观察 `0新闻_粗筛.md` → `3新闻_概述.md` → 最终 PNG 是否生成判断

## 测试缺口（已知）

- **无 LLM mock**：`step4.py`、`step7.py` 每次执行都真实调用 Zhipu GLM-4 Flash 与 MiniMax HTTP API，无法离线回归
- **无信源 HTML/DOM fixtures**：`step1_3.py` 的 7 个抓取器（新华社、人民日报、央视、参考消息、中科院 等）依赖实时网络，信源改版即静默失败
- **无回归基线**：没有"已知好"输出快照（golden file），无法判断 LLM 输出漂移
- **无单元级隔离**：`balance_columns()`（`step8.py:137`）、`needs_chromium()`（`step6.py:205`）等纯函数本可独立测试，目前无覆盖
- **Chromium 依赖未替换**：`/snap/bin/chromium` 硬编码路径在 CI 容器中需另外安装
- **错误路径未验证**：`step4.py:94` 的 `except Exception: return False` 会把所有 LLM 异常静默吞掉，无任何告警/计数

## 推荐补强方向（非本次范围）

- 引入 `pytest` + `requests-mock` / `responses` 抓住 LLM 调用
- 为 `balance_columns`、`needs_chromium`、URL 正则等 17 个纯函数添加单测
- 为每个信源固化一份 HTML fixture，离线验证抓取器
- 建立 3-5 天的产物 snapshot，作为渲染回归基线

---

*本文件由 sillyspec-scan 生成，不编造不存在的测试。*
