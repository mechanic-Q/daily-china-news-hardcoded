---
author: lmr
created_at: 2026-06-27 03:13:46
---

# USER_MANUAL.md — 每日新中国·Daily China News 用户手册

## 1. 项目是什么

每日新中国（Daily China News）是一套自动化的中国新闻数字报纸生成流水线。

工作流程：7 个权威新闻信源采集 -> 三淘汰验证（HTTP/HTTPS/内容有效性）-> 涉华过滤 + 负面过滤 -> 关键词加权 + LLM 双引擎分类 -> 5 层策略链正文提取 -> LLM 逐条摘要（含 retry 3 次诊断回退）-> CSS Grid 双栏 HTML 渲染 -> Chromium headless 截图输出 1080px PNG。

产出 10 条精选新闻，分布于 8 个栏目：科研突破、农业、扶贫、能源、医疗、科技、材料、军事。

技术栈：Python 3.12、aiohttp、openai SDK（OpenAI 兼容协议调用 Zhipu / MiniMax LLM）、urllib、Pillow、Chromium headless。无框架、无数据库、无自动化测试。

当前状态：v1.1 milestone 已完成（Phase 1-9）。本仓库不含标准 build、test、lint 流程（local.yaml 中 test_strategy: skip）。

## 2. 快速开始

### 前提

- Python 3.12+，安装依赖：pip install aiohttp openai Pillow python-dotenv
- Chromium（路径 /snap/bin/chromium，snap 安装）
- 环境变量（从 .env 加载或 shell export）：
  - ZHIPU_API_KEY — GLM-4 Flash（分类 + 摘要）
  - MINIMAX_API_KEY — 涉华判断回退

### 一键运行

```bash
./run_all.sh                          # 默认今天
./run_all.sh --date 2026-06-22        # 指定日期
./run_all.sh --date 2026-06-22 --dry-run  # 演练模式
```

全流水线串行执行 5 个 step，任一失败立即中止。无 --date 时自动使用系统当前日期。

### --dry-run 说明

演练模式：执行完整逻辑和写入中间文件，但 step8 跳过最后一步 Chromium 截图（HTML 仍会生成）。step7 的 --dry-run 行为由脚本内部决定。

## 3. 输出文件

所有输出写入独立数据目录：

```
/mnt/e/每日新中国/YYYY-MM-DD/
├── 0新闻_粗筛.md          # step1_3 产出：7 信源原始链接（已过三淘汰 HTTP 验证）
├── 1新闻_链接.md          # step4   产出：分类 + 优先级排序后的精选标题与链接
├── 2新闻_已审核.md        # step6   产出：抽取完正文的链接清单
├── 3新闻_概述.md          # step7   产出：含 1-2 句摘要的最终素材
├── YYYY-MM-DD_每日新中国_N.html   # step8 产出：双栏报纸 HTML
└── YYYY-MM-DD_每日新中国_N.png    # step8 产出：HTML 截图（Pillow 裁白边）
```

{N} 为中文序数刊号（由 step8 推算）。

中间文件格式为 Markdown，可直接人工阅读和编辑。任一 step 可单独重跑，前提是上游文件存在。

## 4. 分步命令

每个 step 脚本都接受 --date 和 --dry-run 参数：

```bash
python3 step1_3.py --date 2026-06-22            # 采集 + 三淘汰
python3 step4.py   --date 2026-06-22            # 分类 + 筛选
python3 step6.py   --date 2026-06-22            # 正文提取
python3 step7.py   --date 2026-06-22            # LLM 摘要
python3 step8.py   --date 2026-06-22            # 渲染 HTML + 截图
```

### step 职责

| 脚本 | 行数 | 职责 |
|------|------|------|
| step1_3.py | 475 | 7 信源并行采集 + HTTP 三淘汰验证，产出 0新闻_粗筛.md |
| step4.py   | 434 | 8 栏目关键词打分 + LLM 兜底分类 + 涉华/负面过滤，产出 1新闻_链接.md |
| step6.py   | 286 | 5 层策略链正文提取（静态 urllib + 部分 chromium 分流），产出 2新闻_已审核.md |
| step7.py   | 271 | 逐条 LLM 摘要（1-2 句）+ 规则回退 + 3 次重试，产出 3新闻_概述.md |
| step8.py   | 513 | 解析摘要 md -> CSS Grid 双栏 HTML -> Chromium 截图 -> Pillow 裁边，产出 .html + .png |

### 编号说明

step1_3.py 合并了原 step1（抓取）、step2（清洗）、step3（去重）三个阶段。编号中的 step5 不存在，这是历史演进中的编号空缺，请勿添加 step5.py。

### 重跑注意事项

- 每个 step 幂等，对同一日期反复执行会覆盖写入。
- 重跑 step 前确保上游文件已存在（例如重跑 step6 需要 1新闻_链接.md 已存在）。
- 全流水线对同一日期重跑会重新采集所有信源。

## 5. 计时与性能量化

### 基本计时

```bash
time ./run_all.sh --date 2026-06-22
time python3 step8.py --date 2026-06-22
```

time 输出 real（挂钟时间）、user（用户态 CPU）、sys（内核态 CPU）。

### 详细资源统计

```bash
/usr/bin/time -v python3 step1_3.py --date 2026-06-22
```

-v 输出包括：最大驻留内存（Maximum resident set size）、CPU 占用比、上下文切换次数、缺页次数等。

### 耗时参考

全流水线耗时受网络、LLM 响应速度、Chromium 截图速度影响。主要耗时来源：
- step1_3：7 信源并发 HTTP 采集 + 三淘汰验证，网络依赖强
- step4 / step7：LLM 调用，受 API 响应速度和额度/速率限制影响
- step8：Chromium 截图约 120s 超时上限

## 6. SillySpec 工作流

本仓库使用 SillySpec 管理变更。常用命令：

```bash
# 初始化新变更
sillyspec brainstorm     # 需求分析 + 技术方案

# 制定实现计划
sillyspec plan           # 拆解为 Wave + Task

# 执行实现
sillyspec execute        # 按 plan 逐步实现

# 验证
sillyspec verify         # 验收测试

# 归档
sillyspec archive        # 归档已完成变更

# 快速修复
sillyspec quick          # 跳过 brainstorm/plan，直接执行

# 状态查看
sillyspec status         # 查看当前进度
sillyspec state          # 查看 SillySpec 工作状态
sillyspec doctor         # 修复进度数据不一致

# 探索/讨论
sillyspec explore        # 只读分析，不修改文件
```

标准 GSD 流程：brainstorm -> plan -> execute -> verify -> archive。每次 phase 的 discuss 阶段自动创建 feature 分支。

## 7. 故障排查

### step1_3 信源采集失败

- 检查网络连接和信源域名是否可达。
- Chromium 抓取失败时检查 /snap/bin/chromium 是否存在。
- 部分信源有降级链（如中核集团），失败不会中断流水线。

### step4 / step7 LLM 调用失败

- 确认 .env 中包含有效的 ZHIPU_API_KEY 和 MINIMAX_API_KEY。
- 检查 API 账户余额和速率限制。
- step7 内置 3 次重试 + 规则回退，最终失败会输出警告但不会中止流水线。
- 从 shell 运行 step4 前需要 `export` 环境变量（step4 不自动加载 .env）。

### Chromium 截图失败（step8）

- chromium 硬编码路径 /snap/bin/chromium，snap 安装后需确认该路径存在。
- 截图超时 120s，大体积 HTML 可能导致超时。
- dry-run 模式下截图被显式跳过，不是故障。

### 流水线中途中断

- 因使用文件接力，从中断的下一步继续即可：`python3 stepN.py --date YYYY-MM-DD`。
- 排查中断 step 的 stderr 输出。

### 命令未找到

- python3 可能需要替换为 python3.12 或 python。
- 确保在项目根目录执行命令（step 脚本和 run_all.sh 在同级目录）。

## 8. 已知风险

### BASE_DIR 硬编码

所有 step 脚本中输出目录硬编码为 `/mnt/e/每日新中国`（5 处）。迁移到其他路径需要修改全部脚本。

### 无自动化测试

项目无任何单元测试或集成测试（test_strategy: skip）。修改代码后依赖人工验证输出。

### Chromium 路径依赖

/usr/bin/time 和 step 脚本中 chromium 路径硬编码为 /snap/bin/chromium。非 snap 安装或路径变更时需修改对应脚本。

### balance_columns O(2^n) 算法

step8.py 的 balance_columns 使用暴力子集枚举（`1 << n`）做双栏拆分。当前 8 个栏目时 256 循环安全，但 n > 20 时性能崩盘。

### 隐式依赖

仓库无 requirements.txt，依赖透传为隐式安装。pip install 遗漏可能导致 ImportError。

### API Key 安全

API key 通过环境变量传入（ZHIPU_API_KEY、MINIMAX_API_KEY）。step7 读取 .env 文件，step4 从 os.environ 读取。注意不要提交 .env 到版本控制。

### LLM 费用依赖

流水线调用外部 LLM API，每日运行费用取决于调用次数和 token 消耗。速率限制可能导致 step4/step7 延迟。

### 截图裁白边局限

step8 的 Pillow 裁边以左下角像素为参考底色，若版面底部非纯色则裁切不准确。

## 9. 后续路线

以下议题已记录方向，但尚未实现：

### Phase 12: 性能量化（未实现）

对流水线各 step 进行时间、内存、LLM token 消耗的系统性测量和记录。建立基准以便后续优化。

### Phase 13: 栏目算法完全重做（未实现）

当前基于关键词加权的栏目分类方案准确率有限，计划使用 LLM 主导的智能分类替换现有规则流水线。

### Phase 14: 性能优化（未实现）

基于 Phase 12 量化结果，对瓶颈 step（LLM 调用、Chromium 截图等）进行针对性优化，减少端到端运行时间。
