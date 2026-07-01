---
author: lmr
created_at: 2026-07-01 18:07:32
schema_version: 1
doc_type: design
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
depends_on: []
parent_series: phase-15 (crawler refactor)
---

# Design · Phase 15A · common lib

## 1. 背景

Daily 项目（5 步新闻管线 + archive_enrich + monthly_report + news_archive + llm_client）已有 9 个模块（见 `.sillyspec/docs/Daily/modules/_module-map.yaml`）。跨 8 个 Python 文件散布着重复常量、重复工具函数、硬编码路径：

- `COLUMN_ORDER` 在 `step4.py`、`step7.py`、`step8.py`、`monthly_report.py` 各写一份，共 4 处
- `WEEKDAYS` 在 `step8.py` 定义，`monthly_report.py` 未用（该文件无 weekday 需求，故只 1 处，但下游 15D 加日报健康 banner 时会用）
- `detect_source` (step4.py) 与 `infer_source` (news_archive.py) 逻辑字面一致
- `parse_args` 在 5 个 step 脚本各自手写 `--date` / `--dry-run` 解析
- `BASE_DIR = Path("/mnt/e/每日新中国")` 在 8 处硬编码（WSL 之外无法运行）
- `fetch_html_static` / `chromium_dom` / `_preprocess_html` / `ssl_ctx` 在 `step1_3.py` 和 `step6.py` 各一份
- `CST = timezone(timedelta(hours=8))` 在 `news_archive.py`、`archive_enrich.py`、`monthly_report.py` 各一份

**痛点**：后续 15B–15G 每个 change 都要触碰上述常量/工具（例如 15B 换 trafilatura 需改 `step6.fetch_html_static`；15D 加健康 JSONL 需改 `BASE_DIR`），若不先集中，每个 change 都要重写 3-5 处；每次改动都要 grep 全项目，遗漏风险高。

Phase 15A 是 Phase 15 系列（15A–15G，共 7 个 change）的**地基 change**。下游 15B/15C/15D/15E 均依赖它。

## 2. 设计目标

- **G-01** 消除 8 文件间的常量/工具函数重复；未来变更只需改一处
- **G-02** 支持 `DAILY_OUTPUT_DIR` 环境变量，摆脱 WSL 硬编码路径
- **G-03** 行为零变化：`./run_all.sh --date 2026-06-30 --dry-run` 输出关键段与重构前一致
- **G-04** 为下游 15B–15G 提供稳定的 `daily.*` import 起点

## 3. 非目标

- **NG-01** 不做正文提取算法升级（15B 负责）
- **NG-02** 不做异步/并发改造（15C 负责）
- **NG-03** 不引入 argparse 或第三方 CLI 库（保持 CONVENTIONS.md §1「不使用 argparse」）
- **NG-04** 不迁移 `CATEGORY_KEYWORDS`（属 classifier 领域常量，留 step4.py）
- **NG-05** 不改 `run_all.sh` 编排逻辑
- **NG-06** 不改任何 step 的对外文件产出（`0新闻_粗筛.md` ... `*.png`）内容或命名
- **NG-07** 不改 tests/ 现有测试（新增测试只放 tests/manual/）

## 4. 拆分判断

- 本 change 是 Phase 15 系列 7 个 change 中的第 1 个
- 单独 change 而非合并入 15B 的理由：15A 是 refactor（零行为变化，可独立回归），15B 是 behavior change（换 trafilatura），混合会让 15B 的行为差异 diff 淹没在 refactor 的 import 变更里，无法定位问题源
- 用户在 plan mode 已确认「多 change 拆分」

## 5. 总体方案

**单 wave 完成**（无内部依赖切分）：

1. 新建 `daily/` 包（`__init__.py` + `common.py` + `http.py`）
2. 迁移常量与工具函数（附带合并 `detect_source` + `infer_source`）
3. 8 个源文件改 import；删除本地重复定义
4. `.env.example` 追加 `DAILY_OUTPUT_DIR`
5. 新增 `tests/manual/test_15a_diff_smoke.py` 冒烟脚本
6. 验证：`grep` 校验唯一定义 + `--dry-run` diff + pytest 全绿

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `daily/__init__.py` | 空文件（或极简 `__version__ = "0.15.0"`） |
| 新增 | `daily/common.py` | 常量：`BASE_DIR` `COLUMN_ORDER` `WEEKDAYS` `CST`；工具：`today_cst` `parse_common_args` `detect_source` `workdir` |
| 新增 | `daily/http.py` | 常量：`CHROMIUM` `ssl_ctx`；工具：`fetch_html_static` `chromium_dom` `_preprocess_html` |
| 修改 | `step1_3.py` | 删本地 `chromium_dom` `fetch_html_static` `ssl_ctx` `BASE_DIR` `parse_args`；换 `from daily.common import ...` `from daily.http import ...` |
| 修改 | `step4.py` | 删本地 `COLUMN_ORDER` `detect_source` `BASE_DIR` `parse_args`；换 import |
| 修改 | `step6.py` | 删本地 `chromium_dom` `fetch_html_static` `ssl_ctx` `_preprocess_html` `BASE_DIR` `parse_args`；换 import；保留 `extract_body/_postprocess_text/_is_contaminated/_aggressive_clean`（15B 才动） |
| 修改 | `step7.py` | 删本地 `COLUMN_ORDER` `BASE_DIR` `parse_args`；换 import |
| 修改 | `step8.py` | 删本地 `COLUMN_ORDER` `WEEKDAYS` `BASE_DIR` `parse_args`；换 import |
| 修改 | `news_archive.py` | 删本地 `BASE_DIR` `ARCHIVE_DIR` `CST` `infer_source`（保 `def infer_source(url, article): return detect_source(url)` 薄 shim 以保 test 兼容）；`ARCHIVE_DIR/ARTICLES_DIR/IMAGES_DIR` 基于新 `BASE_DIR` 派生 |
| 修改 | `monthly_report.py` | 删本地 `COLUMN_ORDER` `CST` `ARCHIVE_DIR` `ARTICLES_DIR` `IMAGES_DIR` `MONTHLY_DIR`（后 4 项基于 common.BASE_DIR 派生并 import） |
| 修改 | `archive_enrich.py` | 删本地 `SSL_CTX` `CST`；换成 `from daily.http import ssl_ctx as SSL_CTX` + `from daily.common import CST` |
| 修改 | `.env.example` | 追加 `DAILY_OUTPUT_DIR=/mnt/e/每日新中国` 说明 |
| 新增 | `tests/manual/__init__.py` | 空文件 |
| 新增 | `tests/manual/test_15a_diff_smoke.py` | 手动脚本：跑 dry-run 与 baseline diff |

## 7. 接口定义

### 7.1 `daily/common.py`

```python
"""daily.common — Daily 项目跨模块共享常量与工具

集中管理 Phase 15A 之前散布在 8 个文件中的常量与 helper：
- 输出根目录（支持 DAILY_OUTPUT_DIR 环境变量）
- 9 栏目定义、weekdays、CST 时区
- --date / --dry-run 命令行解析（不使用 argparse）
- 信源识别（合并 step4.detect_source + news_archive.infer_source）
"""
from __future__ import annotations

import datetime
import os
import sys
from datetime import date, timezone, timedelta
from pathlib import Path
from typing import Tuple


BASE_DIR: Path = Path(os.environ.get("DAILY_OUTPUT_DIR", "/mnt/e/每日新中国"))

CST: timezone = timezone(timedelta(hours=8))

COLUMN_ORDER: list[str] = [
    '🔬 世界性科研突破',
    '🤖 AI智能前沿',
    '🌾 农业',
    '🤝 扶贫',
    '⚡ 能源',
    '🏥 医疗',
    '🚀 科技',
    '🧱 材料',
    '🎖️ 军事',
]

WEEKDAYS: list[str] = [
    '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'
]


def today_cst() -> date:
    """返回 CST 时区下的今天日期。"""
    return datetime.datetime.now(CST).date()


def parse_common_args() -> Tuple[date, bool]:
    """手写解析 sys.argv 中的 --date YYYY-MM-DD 和 --dry-run。

    与旧版 5 个 step 的 parse_args 逐字节等价：
    - 无 --date → today_cst()
    - --date 格式错 → print + sys.exit(1)
    - --dry-run 存在 → dry_run=True

    Returns:
        (date_obj, dry_run_bool)
    """
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}，应为 YYYY-MM-DD")
            sys.exit(1)
    else:
        dt = datetime.date.today()  # 保留旧行为（本地时区），避免行为漂移
    return dt, dry


def detect_source(url: str) -> str:
    """从 URL 判定信源。合并 step4.detect_source + news_archive.infer_source。"""
    if not url:
        return '综合'
    if 'cankaoxiaoxi' in url or 'ckxxapp' in url:
        return '参考消息'
    if 'military.cctv' in url:
        return '央视军事'
    if 'news.cctv' in url:
        return '央视新闻'
    if 'cas.cn' in url:
        return '中科院'
    if 'cnnpn.cn' in url or 'cnnc.com' in url:
        return '中核集团'
    if 'people.com.cn' in url:
        return '人民日报'
    if 'news.cn' in url or 'xinhuanet' in url:
        return '新华社'
    return '综合'


def workdir(d: date) -> Path:
    """返回 BASE_DIR / d.strftime('%Y-%m-%d')。"""
    return BASE_DIR / d.strftime("%Y-%m-%d")
```

### 7.2 `daily/http.py`

```python
"""daily.http — Daily 项目共享 HTTP / Chromium 工具

集中管理 step1_3 与 step6 中重复的 SSL context、静态抓取、
chromium --dump-dom 调用与预处理。
"""
from __future__ import annotations

import re
import ssl
import subprocess
import urllib.request


CHROMIUM: str = "/snap/bin/chromium"

ssl_ctx: ssl.SSLContext = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def fetch_html_static(url: str, timeout: int = 12) -> str:
    """urllib 静态抓取，默认 UA + 全局 ssl_ctx。timeout 默认 12s，
    与旧 step1_3 (15) 和 step6 (12) 有细微差异 —— 统一取 12（覆盖两者最小值）。
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(
        req, timeout=timeout, context=ssl_ctx
    ).read().decode("utf-8", errors="replace")


def chromium_dom(url: str, timeout: int = 45, budget: int = 30000) -> str:
    """chromium --dump-dom 获取 JS 渲染后的 DOM。

    默认 (45, 30000) 对齐 step6；step1_3 用 (12, 5000)。
    调用方按需覆盖以保持旧行为。
    """
    try:
        r = subprocess.run(
            [CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage",
             f"--virtual-time-budget={budget}", "--dump-dom", url],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout
    except Exception:
        return ""


def _preprocess_html(html: str) -> str:
    """剥 <script> <style>。step6 用；15A 迁移，行为不变。"""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.S)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.I | re.S)
    return html
```

### 7.3 迁移前后 API 对照

| 旧引用 | 新引用 |
|---|---|
| `step1_3.chromium_dom(url, timeout=12, budget=5000)` | `daily.http.chromium_dom(url, timeout=12, budget=5000)`（显式传参保留旧默认） |
| `step1_3.fetch_html_static(url)` | `daily.http.fetch_html_static(url, timeout=15)`（step1_3 内部旧默认 15，调用点显式传） |
| `step6.chromium_dom(url)` | `daily.http.chromium_dom(url)`（默认 45/30000 与旧 step6 一致） |
| `step6.fetch_html_static(url)` | `daily.http.fetch_html_static(url)`（默认 12） |
| `step4.detect_source(url)` | `daily.common.detect_source(url)` |
| `news_archive.infer_source(url, article)` | `daily.common.detect_source(url)`；文件内保留 shim `def infer_source(url, article): return detect_source(url)` |
| `step1_3.parse_args()` 等 5 处 | `daily.common.parse_common_args()` |
| `Path("/mnt/e/每日新中国")` | `daily.common.BASE_DIR` |

**关键**：`step1_3` 内部旧 `fetch_html_static` 默认 timeout=15，`step6` 用 12。这是旧代码里两处不一致，本 change 统一 helper 的默认值为 12，但**调用方在有 timeout 差异需求时显式传参**，保证运行时行为不变（`step1_3` 里改成 `fetch_html_static(url, timeout=15)`）。

### 7.4 Re-export 规则（Design Grill X-001/X-002/X-004 消解）

以下三条 re-export 是强制的，否则会破坏跨模块 import 和现有测试的 mock：

- **step6.py 顶部**必须 `from daily.http import fetch_html_static, chromium_dom, ssl_ctx, _preprocess_html`。这使得 `archive_enrich.py` 现有的 `from step6 import fetch_html_static` 仍能工作，`tests/test_archive_enrich.py` 的 `@mock.patch("archive_enrich.fetch_html_static", ...)` 也仍能生效（mock 的是 archive_enrich namespace 里的名字，只需 archive_enrich 能 import 到即可）。
- **monthly_report.py 顶部**必须 `from daily.common import COLUMN_ORDER, CST`。这保 `tests/test_monthly_report.py:19` 的 `from monthly_report import ... COLUMN_ORDER` 不断链。
- **news_archive.py 顶部**必须 `from daily.common import BASE_DIR, CST, detect_source`；同时保留 `def infer_source(url, article): return detect_source(url)` 薄 shim（D-004）。这保 `tests/test_news_archive.py:18` 的 `from news_archive import infer_source` 与 `infer_source(url, {})` 调用继续工作。

Python `import` 语义天然把 `from X import Y` 在导入方 namespace 里绑一个 `Y` 名字，因此 top-level 的 `from daily.http import fetch_html_static` 就是 re-export，无需显式 `__all__` 或 alias。

## 8. 数据模型

不涉及。

## 9. 兼容策略

- **C-01** `DAILY_OUTPUT_DIR` 未设置 → BASE_DIR = `/mnt/e/每日新中国`，与旧行为完全一致
- **C-02** `news_archive.infer_source(url, article)` 保留为薄 shim，避免破坏可能存在的第三方 import
- **C-03** 5 个 step 脚本继续接受 `python3 stepN.py --date X --dry-run`，参数解析行为逐字节等价
- **C-04** `run_all.sh` 完全不改，其调用的 `python3 step*.py --date $DATE $DRY_RUN` 语义不变
- **C-05** 输出文件路径 `BASE_DIR / date_str / <filename>` 结构不变
- **C-06** 所有 `import` 保持 top-level，不引入 lazy import（`llm_client` 已惰性导入 openai，不动）

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | `parse_args` 5 处签名微差异（archive_enrich 有 `--missing-only/--max-seconds`；monthly_report 用 `--month/--no-llm/...`）被误合并 | P0 | 只把「`--date`+`--dry-run` 组合」提取为 `parse_common_args`；archive_enrich 和 monthly_report 的特殊 arg 保留本地 `parse_args`，不迁移 |
| R-02 | `fetch_html_static` 默认 timeout 从 15 (step1_3) 变 12 (统一) 后偶发超时 | P1 | 调用点显式传参保留旧 timeout；validate via dry-run smoke test |
| R-03 | `infer_source(url, article)` 有第三方引用（scan.md 未列，但内部 test 可能引用） | P1 | 保留 shim；grep 全项目验证无字面 `.infer_source(` 硬绑其他签名 |
| R-04 | 循环 import（`daily.common` 与 `daily.http` 若互相 import） | P1 | 严格分层：`daily.common` 不 import `daily.http`；反之亦然 |
| R-05 | `DAILY_OUTPUT_DIR` 设为不存在路径 → step 运行时报错 | P2 | 沿用旧代码行为（step 内 `workdir.mkdir(parents=True, exist_ok=True)` 已存在）；不做 pre-flight 校验 |
| R-06 | 现有 `tests/test_news_archive.py` 硬编码 `BASE_DIR = Path("/mnt/e/每日新中国")` 或直接 import `infer_source` 断言签名 | P0 | execute 阶段先 grep tests/ 确认无冲突；有冲突再 patch 测试 |
| R-07 | Python 版本兼容：`from __future__ import annotations` 需 3.7+，`list[str]` 需 3.9+ | P2 | 项目 Python 3.12，OK；仍加 `from __future__ import annotations` 保险 |
| R-08 | `step1_3.SOURCES` 常量引用了本地 `fetch_xinhuanet` 等，若 fetcher 内部换 `daily.http` 后有闭包问题 | P1 | fetcher 函数不迁移，只换其内部对 helper 的引用 |

## 11. 决策追踪

本 change Grill 阶段判定为 skip（P0/P1 歧义 = 0，见 Step 7 摘要）。以下为在 Step 6（对话式探索）中确认的 3 项决策，转录到本 change 的 `decisions.md`：

- **D-001@v1**：daily/ 包结构（含 `__init__.py` + `common.py` + `http.py`）
- **D-002@v1**：`parse_common_args` 保持手写 sys.argv，不引入 argparse
- **D-003@v1**：`BASE_DIR = Path(os.environ.get("DAILY_OUTPUT_DIR", "/mnt/e/每日新中国"))`

覆盖对应：
- D-001 → §6 文件清单 + §7.1/7.2 API
- D-002 → §7.1 `parse_common_args` 实现 + NG-03
- D-003 → §7.1 BASE_DIR 定义 + C-01

无剩余未解决 D-xxx。

## 12. 生命周期契约表

**判定**：本 change 无涉及 session/lease/agent_run/daemon/lifecycle/state transition/complete/end/claim/heartbeat 任一关键词。跳过。

## 13. 自审

### 需求覆盖
- ✅ 消除跨文件重复（G-01）→ §6 全部 8 个 step/archive/monthly 文件都在清单中
- ✅ env 化 BASE_DIR（G-02）→ §7.1 `BASE_DIR = Path(os.environ.get(...))`
- ✅ 行为零变化（G-03）→ §7.3 显式 API 对照 + §9 兼容策略
- ✅ 为下游提供 daily.* 起点（G-04）→ §6 新增 `daily/` 包

### Grill 覆盖
- ✅ D-001/D-002/D-003 全部在 §7/§9/§11 有引用

### 约束一致性
- ✅ CONVENTIONS §1「不使用 argparse」→ NG-03 + §7.1 手写 sys.argv
- ✅ CONVENTIONS §2 命名（snake_case、大写常量、下划线私有）→ `_preprocess_html` 保下划线；`BASE_DIR`/`COLUMN_ORDER` 大写
- ✅ CONVENTIONS §5「无 threading/asyncio」→ 本 change 不引入
- ✅ STRUCTURE §5「无包结构」将被打破 → 已在 Step 6 用户明确同意（D-001）

### 真实性
- ✅ 所有类/方法/常量名来自 `_module-map.yaml` main_symbols 或源码 grep 确认（`COLUMN_ORDER` in step4/7/8/monthly_report、`detect_source` in step4、`infer_source` in news_archive、`chromium_dom` in step1_3/6 等）
- ⚠️ 自审存疑：`tests/test_news_archive.py` 可能引用 `infer_source` — execute 前需 grep 校验（已列为 R-06）

### YAGNI
- ✅ 未加日志、未加类型检查工具、未加 CI（属 15G）
- ✅ 未迁移 `CATEGORY_KEYWORDS`（属 classifier 领域，留 step4）

### 验收标准可测
- ✅ §14 全部为 command / grep 可执行断言

### 非目标清晰
- ✅ §3 明确 6 项 NG

### 兼容策略（brownfield）
- ✅ §9 C-01～C-06 覆盖 env 未设、shim、CLI 语义、路径结构、import 层级

### 风险识别
- ✅ §10 登记 8 条风险，覆盖签名合并、timeout 差异、循环 import、tests 冲突

### 生命周期契约表
- N/A（§12 已判定）

**自审结论**：通过。1 处「⚠️ 自审存疑」已转 R-06 待 execute 阶段消解。

## 14. 验收标准

- **V-01** `python3 -c "from daily.common import BASE_DIR, COLUMN_ORDER, WEEKDAYS, CST, today_cst, parse_common_args, detect_source, workdir; from daily.http import CHROMIUM, ssl_ctx, fetch_html_static, chromium_dom, _preprocess_html"` 无异常
- **V-02** `DAILY_OUTPUT_DIR=/tmp/x python3 -c "from daily.common import BASE_DIR; assert str(BASE_DIR)=='/tmp/x'"` 通过
- **V-03** `rg 'COLUMN_ORDER = \[' *.py` 无命中（daily/ 下有一处，但根目录已清空）
- **V-04** `rg '"/mnt/e/每日新中国"' *.py daily/` 命中数 ≤ 1（只 `daily/common.py` 默认值）
- **V-05** `rg 'ssl_ctx.verify_mode = ssl.CERT_NONE' *.py` 无命中；只在 `daily/http.py`
- **V-06** `rg 'def chromium_dom\(' *.py` 无命中；只在 `daily/http.py`
- **V-07** `python3 -m pytest tests/` 全绿（`tests/manual/` 不入默认 collect）
- **V-08** 备份 baseline：`python3 run_all.sh --date 2026-06-30 --dry-run` 输出关键段（`═══ 预览`、`═══ Step` 计数、精选新闻列表）与 refactor 前一致（人工核对 `tests/manual/test_15a_diff_smoke.py` 出结果）
- **V-09** `python3 step1_3.py --date 2026-06-30 --dry-run` 单步等价
- **V-10** `python3 archive_enrich.py --date 2026-06-30 --dry-run` 单步等价（验证 SSL_CTX/CST 迁移未破坏）
- **V-11** `python3 -m pytest tests/test_archive_enrich.py tests/test_news_archive.py tests/test_monthly_report.py` 全绿（验证 step6/monthly_report/news_archive re-export 兼容）
- **V-12** `python3 - <<'PY'\nimport step6, monthly_report, news_archive\nassert hasattr(step6, 'fetch_html_static')\nassert hasattr(monthly_report, 'COLUMN_ORDER')\nassert news_archive.infer_source('https://news.cn/x', {}) == '新华社'\nPY` 通过（Design Grill re-export 检查）.
