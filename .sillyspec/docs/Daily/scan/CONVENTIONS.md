---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# Daily（每日新中国） 代码约定 CONVENTIONS

## 1. 框架隐形规则

### 统一命令行接口
每个 step 脚本均通过 `parse_args()` 手动解析 `sys.argv`（**不使用 `argparse` 库**），暴露两个通用参数：
- `--date YYYY-MM-DD` — 指定处理日期；缺省时在 `parse_args()` 中 fallback 为 `datetime.date.today()`
- `--dry-run` — 预览模式，不输出最终文件；step8 在 dry-run 下仍写入 HTML 但跳过截图

调用模式全部为：
```python
today, dry_run = parse_args()
...
if __name__ == "__main__":
    main()
```

### 文件接力管线
按 `run_all.sh` 顺序串联，每个 step 读上一个 step 的产物：
| Step | 输入 | 输出 |
|------|------|------|
| step1_3 | （外部API） | `0新闻_粗筛.md` |
| step4 | `0新闻_粗筛.md` | `1新闻_链接.md` |
| step6 | `1新闻_链接.md` | `2新闻_已审核.md` |
| step7 | `2新闻_已审核.md` 和 `1新闻_链接.md` | `3新闻_概述.md` |
| step8 | `3新闻_概述.md` | `.html` + `.png` |

`run_all.sh` 使用 `set -euo pipefail`，任一 step 非零退出则终止整条管线。

### 输出目录硬编码
所有路径基于 `BASE_DIR / date_str`：
```python
BASE_DIR = Path("/mnt/e/每日新中国")
workdir = BASE_DIR / today_str
```
输入/输出文件名使用 `0新闻_粗筛.md`、`1新闻_链接.md` 等固定命名。

### 错误退出
所有 step 在致命错误（文件缺失、参数无效）时统一执行 `sys.exit(1)`，无异常链或自定义退出码。

## 2. 代码风格

### 命名规范
- **函数/变量**：`snake_case`，如 `parse_args()`、`fetch_xinhuanet()`、`today_str`
- **全局常量**：全大写，如 `BASE_DIR`、`CHROMIUM`、`CATEGORY_KEYWORDS`、`SOURCES`、`COLUMN_ORDER`、`EXCLUDE_TITLES`、`WEEKDAYS`
- **私有辅助函数**：下划线前缀，如 `_is_contaminated()`、`_aggressive_clean()`、`_chinese_ordinal()`

### 注释语言
- 行内注释和块注释以**简体中文**为主
- docstring 使用中文，集中在文件头部用法说明中
- step8.py 全文件无注释（唯一例外）

### 类型注解
极少使用 type hints；仅偶见 `def main()` 返回值省略、参数无类型标注。

### 错误处理模式
- 每个 step 使用 `try/except Exception`（step1_3 出现 7 次 `try:`，其余 2-4 次）
- 不区分异常类型，全部 catch 后打印中文错误信息或执行 `sys.exit(1)`
- step1_3 额外处理网络异常（`ssl.SSLError`, `urllib.error.URLError`），step8 处理 `PIL` 可选导入的 `ImportError`

## 3. LLM 调用约定

- 统一通过 `openai` SDK，通过 `base_url` 切换不同提供商：
  - step4 使用 MiniMax (`api.minimax.chat/v1`) 和 GLM (`open.bigmodel.cn/api/paas/v4/`)
  - step7 使用 GLM (`open.bigmodel.cn/api/paas/v4/`)
- `from openai import OpenAI` 在函数内部**惰性导入**
- API key 通过 `os.environ["..."]` 读取，无显式配置或 .env 文件管理

## 4. 输出风格

- 状态信息使用中文 emoji 前缀：`print(f"✅ ...")`、`print(f"❌ ...")`、`print(f"⚠ ...")`
- 关键进度输出 `═══ 运行: ... ═══` 来自 `run_all.sh`
- step8 截图使用 Chromium (`/snap/bin/chromium`) 无头模式 + `PIL` 裁剪白边

## 5. 异步与并发

- 仅 step1_3 使用 `asyncio` + `aiohttp`：通过 `asyncio.run(verify_http(...))` 异步验证链接可用性
- 其余 step 均为纯同步脚本，无 threading 或 asyncio

## 6. 文件 I/O

- 字符串写入一律 `encoding="utf-8"`，使用 `Path.write_text()`
- 行列表拼接后统一 `"\n".join(lines)` 写入
- 无上下文管理器以外的显式文件关闭操作

## 7. 演进趋势

- step1_3 → step8 在复杂性上无明显下降：step1_3（17 函数）、step4（14）、step6（14）、step7（8）、step8（15）
- 专用常量列表（`EXCLUDE_TITLES`、`CATEGORY_KEYWORDS`、`CHINA_KEYWORDS` 等）在 step4 集中定义
- step8 无任何注释，且是唯一使用 `PIL` 外部依赖的脚本