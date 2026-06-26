---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# CONCERNS — 每日新中国 · Daily China News

按严重程度分组：🔴 阻断 / 🟡 警告 / 🟢 提示

## 代码质量

### 🔴 高优先级

- 🔴 **MiniMax 模型字符串疑似无效** — `step4.py:88` 写死 `model="minimax-m2.7"`，MiniMax 官方实际模型名为 `abab6.5*` 系列或 `MiniMax-M2`。该调用包在 `try/except Exception: return False`（step4.py:93-94）中，任何 API 错误都被静默吞掉，"中国相关性判断"会全部回退为 False 而无任何告警，污染下游分类结果。
- 🔴 **输出根目录跨平台硬编码** — `BASE_DIR = Path("/mnt/e/每日新中国")` 在 5 个 step 脚本中均出现（`step1_3.py:25`, `step4.py:17`, `step6.py:21`, `step7.py:22`, `step8.py:18`），含中文路径段，Windows / macOS / 非 WSL Linux 上完全不可移植，且修改输出目录需要改 5 处。
- 🔴 **异常被全局静默** — `rg "except Exception" *.py` 命中 6 处（step1_3.py:100/142, step4.py:94/247, step6.py:230, step7.py:185），其中 step4.py:94 直接 `return False`，吞掉所有 LLM 错误（鉴权失败 / 网络错误 / 模型不存在），运行结果看起来"成功"但实际未生效。

### 🟡 中优先级

- 🟡 **信源 URL/正则全硬编码** — `step1_3.py` 7 个抓取函数（`fetch_xinhua` / `fetch_cctv` / `fetch_cctv_mil` 等）的 base URL、`YYYYMMDD/c.html` 路径正则、DOM 选择器全部硬编码，新增信源或站点改版都需要改代码。
- 🟡 **`balance_columns()` O(2^n) 暴力枚举** — `step8.py:137-176` 用 `for mask in range(1 << n)` 穷举所有左右栏分配组合。当前 n ≤ 8 栏目（mask 256 个，毫秒级）够用，但未来扩展到 12+ 栏目会指数爆炸，且算法选型未注释说明。
- 🟡 **`python-dotenv` 加载不一致** — `step7.py:19-20` 主动 `from dotenv import load_dotenv; load_dotenv(...)`，但 `step4.py` 直接 `os.environ.get("MINIMAX_API_KEY")`（line 81）与 `os.environ.get("ZHIPU_API_KEY")`（line 212）不 load `.env`。同一仓库两套环境加载策略，从 shell 直接跑 step4 时会读不到 `.env` 中的 key。
- 🟡 **5 个 step 重复定义同名常量** — `BASE_DIR` / `CHROMIUM = "/snap/bin/chromium"` 在 step1_3.py:26 与 step6.py:22 各自重复定义；`chromium_dom()` 函数在 step1_3.py:69 与 step6.py:48 各自实现一遍，无共享 `common.py`。
- 🟡 **`import os` 散落在函数内部** — `step4.py:80` 在 `llm_is_china_related()` 函数体内才 `import os`，违反 PEP 8 顶部 import 约定，也阻碍静态分析。

### 🟢 低优先级

- 🟢 **无 TODO/FIXME 标记** — `rg "TODO|FIXME|XXX|HACK|deprecated"` 命中 0 处，债务未被显式记录，依赖维护者口口相传。
- 🟢 **`step5.py` 不存在** — pipeline 跳号（step1_3 → step4 → step6 → step7 → step8），README 未解释 step5 的命名空缺。
- 🟢 **HTML 模板内联在 step8.py** — `step8.py:238/385/398` 中的 `<title>每日新中国</title>` 等模板字符串直接 Python f-string 拼接，未抽出 `template.html`，渲染样式调整需改 Python 代码。

## 依赖风险

### 🔴 高优先级

- 🔴 **无依赖锁文件** — 仓库根目录 `ls requirements.txt pyproject.toml setup.py setup.cfg Pipfile` 全部不存在。README "Install" 段建议 `pip install python-dotenv openai Pillow`，但版本未锁定，未来 `openai>=2.0` 的 breaking change（已有先例）会直接破坏 step4/step7。
- 🔴 **API key 缺失即静默降级** — `step4.py:81-82` / `step4.py:212-213` / `step7.py:153` 都是 `api_key = os.environ.get(...); if not api_key: return ...`，缺 key 时不抛错、不日志，调用者无从知道功能已退化。

### 🟡 中优先级

- 🟡 **Chromium 路径硬编码** — `CHROMIUM = "/snap/bin/chromium"`（step1_3.py:26, step6.py:22, step8.py 中也调用）固定为 Ubuntu snap 安装路径，macOS / 非 snap Linux / Windows 全部失效，且未提供 `--chromium-path` 参数覆盖。
- 🟡 **`aiohttp` 仅 step1_3 使用** — `step1_3.py:13 import aiohttp`，其它 step 用同步 `urllib`，依赖图不统一；如果 step1_3 安装失败，整个 pipeline 第一步就断。
- 🟡 **`from openai import OpenAI` 用作通用 OpenAI 兼容客户端** — `step4.py:85` / `step7.py` 通过 `base_url="https://api.minimax.chat/v1"` 把 OpenAI SDK 当作 MiniMax / Zhipu 的薄封装。SDK 内部对非 OpenAI 行为（如响应字段、错误码、流式格式）的兼容性无保证，SDK 版本升级随时可能破坏。

### 🟢 低优先级

- 🟢 **依赖中国大陆网络可达** — 7 信源全部为 `news.cn` / `people.com.cn` / `cctv.com` / 中科院等大陆域名，在境外服务器或受限网络环境运行会大面积超时。
- 🟢 **`Pillow` 仅用于 `crop_bottom_whitespace`** — `step8.py` 中 Pillow 唯一作用是裁剪 PNG 底部空白，可用纯 Chromium `--clip` 参数替代以减少依赖。

---

*本文件由 sillyspec-scan 生成，依据 commit 5f76a1a 全仓 rg 扫描结果。*
