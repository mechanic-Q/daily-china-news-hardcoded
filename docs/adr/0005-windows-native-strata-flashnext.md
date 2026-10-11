# ADR-0005:管道 Windows 原生化 + Strata Flash-Next IQ3_S 后端

## Status
Accepted

## Date
2026-10-12

## Context
27B GGUF 模型文件删除后，kvmem(27182)/qwen-local(8899) 两个本地后端永远无法启动（ADR-0004 记录的两代栈同日退役）。同日新装 Strata 引擎 0.1.42 + Qwen3.8-Flash-Next IQ3_S（Windows 原生，127.0.0.1:8080，ctx 65536，KV int8）。

连通性实测（2026-10-12）：管道宿主 WSL2(NAT) → Windows 两条路均不通——`127.0.0.1:8080` connection refused（WSL loopback ≠ Windows loopback）、网关 IP 超时（防火墙丢包 + Strata 只绑 127.0.0.1）。若管道留 WSL，需 Strata 改绑 0.0.0.0 + 防火墙规则 + 动态宿主 IP（或 portproxy 同步脚本），比把管道搬到 Windows 更重且更脆。

管道对 Linux 的真实依赖经排查只有三样：venv、`/snap/bin/chromium`（硬编码 3 处）、`/mnt/e` 路径常量（6 文件 + 2 测试）；无 fcntl/uvloop/os.fork 等 Linux-only import；WSL crontab 无管道定时任务。Windows 侧 Chrome、Python 3.11.6、输出目录 E:\每日新中国 本就齐备。

Strata 冒烟事实（2026-10-12）：OpenAI 兼容 /v1；请求 model 名被忽略（响应恒回真实模型名 `qwen3.8-flash-next-iq3_s`）；任意 API key 可用；`reasoning_effort=none` 被接受且真正关闭思维链（响应无 reasoning_content）；默认 CoT 开，小 max_tokens 下思维链吃满预算致 content=null（max_tokens=32 实测 null）——`reasoning: "off"` 键不可去；速度 76-136 tok/s（优于 kvmem 87-90）；加载后显存 15.7/16.3GB；taskkill 树杀后显存干净回落基线（~600MB）。

## Decision
1. **管道整体迁 Windows 原生**（Git Bash 编排 + Windows Python 3.11 venv + 本机 Chrome）。`daily_china_news_full_to_feishu.py`（飞书/视频编排器，引用 ~/projects/Daily 与 ~/.hermes 视频技能）不随迁，留在原环境。
2. **llm.yaml 只留 strata + 云端应急**（zhipu/minimax）；kvmem/qwen-local 条目删除。strata provider 沿用 `reasoning: "off"`（llm_client 现有机制 → `reasoning_effort=none`）与 `max_output_tokens: 16384` 钳制，llm_client.py 零改动。
3. **互斥口径从 ss 端口清单改为 nvidia-smi 显存阈值**（>2000MiB 拒绝启动）：WSL 侧 CUDA 负载在 Windows nvidia-smi 同样可见，覆盖一切 GPU 占用方；空闲基线 ~600MB。
4. **生命周期语义沿用**（2026-09-24 所有权教训照旧）：自动启动→退出 `taskkill //PID x //T //F` 树杀；已在线实例复用不杀；端口被占但健康未过 → 报错退出不代杀。树杀是必须的——server.py 被硬杀没有优雅卸载路径，不树杀会残留 strata.exe 继续占 15.7GB。
5. bench 三件套（bench_ab/bench_llm/bench_kvmem_degrade）连同其单测删除，属 27B 时代工具；历史由 docs/bench-*.md + ADR-0004 保留。

## Consequences
- venv 布局 `.venv/bin/python3` → `.venv/Scripts/python.exe`；编排层 llm.yaml 解析走 venv python（PyYAML 已在 requirements.txt）。
- chromium 三处硬编码收敛为 `daily/http.py:CHROMIUM` 单点（step8/monthly_report 改为导入）；monthly_report 的 `file://{path}` 在 Windows 是坏 URI，改 `Path.as_uri()`。
- Chrome 与 snap chromium 同内核，`--headless=new/--dump-dom/--screenshot` 旗标全兼容；`--disable-gpu` 保留，渲染不与 Strata 抢显存。
- run_all.sh 导出 `PYTHONUTF8=1`（Windows 默认 cp936 会炸中文管道输出）。
- 测试侧 Windows 适配：`/tmp` 绝对路径改 `tempfile.gettempdir()`；路径断言用 `as_posix()`；subprocess 调 bash 必须用绝对路径——CreateProcess 搜索 System32 先于 PATH，裸 `"bash"` 会命中 WSL launcher（认不得 C:/ 与 /c/ 路径），见 `tests/test_run_all.py:_find_bash`。
- start-llm.sh 自检一发小对话（ASCII prompt——Git Bash 命令行中文按 GBK 编码会被服务端 400），校验 /v1/models + content 非空（防 CoT 未关）。
- T0 冒烟（2026-10-12）：6 call_site 全过，单次 0.5-1.4s。
- 回滚路径 = llm.yaml `provider:` 改 zhipu/minimax（需 .env 填真实 key）；本地 27B 栈不可回滚（模型文件已删）。
