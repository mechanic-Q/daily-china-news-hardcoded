# ADR-0004:本地 LLM 后端切换 KVMem rc1 + IQ2_S

## Status
Accepted

## Date
2026-09-24

## Context
Daily 全链路 6 个 call_site（china-relevance / column-classify / column-score / event-dedup / summarize / monthly-overview）此前由 vanilla llama-server @ 8899（Qwen3.8-27B IQ3_XS HauhauCS，qwen-local provider）承载。2026-09-23/24 实测（RTX 5080 16G / WSL2）表明 KVMem rc1（Linux sm120a 专用包）+ IQ2_S 去限款（8.95G 权重）是同机最快路线：256-token 真实负载稳定 87-90 t/s（旧栈参照更慢且权重大 1.6G+），MTP 接受率 ~97%。

切换约束：
- 16G 显存同一时刻只能跑一个 27B 实例（双实例必 OOM），与视频侧 8888(np4)/18200/18201(视频 KVMem) 互斥；8899(旧栈) 同样占用显存，一并纳入互斥清单。
- 18201/18202 端口让给视频侧，Daily 用冷门端口 27182，避免互踩实例与共享劣化计数。
- KVMem rc1 连续 ~30 轮请求后解码会劣化至 4 t/s（指南红线#1），Daily 日均一轮 6-10 次调用，远低于劣化阈值。

## Decision
1. `llm.yaml` 新增 `kvmem` provider（base_url `http://127.0.0.1:27182/v1`，api_key_env 沿用 LLAMA_API_KEY，max_output_tokens=16384，reasoning="off" 与 qwen-local 完全对齐）；默认 `provider: kvmem`。**回滚 = 一行改回 `provider: qwen-local`**，旧栈启动方式不变（`bash start-llm.sh`）。
2. `start-llm.sh` 新增 kvmem 子命令：模型 `~/models/llm/qwen38-27b/iq2s/Qwen3.8-27B-Abliterated-GSQ-Orca-IQ2_S-MTP.gguf`，参数 kvmem-budget 36864 / Q8 KV / draft-mtp n3 / ctx 262144 / `--no-think`。启动前检查 8888/8899/18200/18201/27182 任一占用即拒绝；启动后自检 gen_tps ≥75（不达标自动 kill 刚起实例）。
3. 思维链双保险：服务端 `--no-think` + 客户端 `extra_body.reasoning_effort=none`。冒烟实测 rc1 **接受** `reasoning_effort` 字段（HTTP 200），故无需给 llm_client.py 加 per-provider 关闭开关——既有 `reasoning: "off"` 键即天然 per-provider。

## Consequences
- 冒烟三项事实（2026-09-24 实测定案）：① rc1 支持 `--no-think`（`--help` 明列，且 Qwen thinking 默认 off）；② `reasoning_effort=none` 被 kvmem-server 接受，与 9router 专属字段 `thinking:{type:disabled}` 不同；③ 空 content → reasoning_content 回退路径由 `tests/test_llm_client.py::test_empty_content_falls_back_to_reasoning_content` 覆盖。
- KVMem 响应体**无** `timings` 字段（vanilla llama.cpp 专属），速度自检只能读服务端日志 `KVMEM_CHAT_TURN ... gen_toks=`。
- 自检负载用 256-token 生成（数 1 到 100）：数十 token 的短生成中 MTP 固定开销占比大，速度波动 68-75 t/s 会误杀健康实例；256 token 下稳定 87-90 t/s。
- `tests/test_monthly_report.py::test_llm_returns_none_on_exception` 原先 patch `"openai.OpenAI"` 不生效（llm_client 以 `from openai import OpenAI` 拷贝了引用），靠 8899 停机假阳性通过；后端常驻后暴露，已修正 patch 目标为 `llm_client.OpenAI`。
