---
id: task-10
author: lmr
created_at: 2026-06-24 19:40:00
title: 异常路径验证
priority: P1
depends_on: [task-09]
blocks: []
requirement_ids: [FR-01, FR-03]
decision_ids: [D-003@v1, D-006@v1]
allowed_paths:
  - /mnt/e/Daily/llm.yaml
---

# task-10: 异常路径验证

## 修改文件
- 无代码修改。临时改 `llm.yaml` 触发异常路径，测试完成后恢复。

## 覆盖来源
- Requirements: FR-01（配置加载错误处理），FR-03（LLM 调用异常可见）
- Decisions: D-003@v1（仅 YAML 错误反馈），D-006@v1（不做运行时 fallback）

## 验证步骤

### 验证 1：错配置 → ConfigError
```bash
cd /mnt/e/Daily

# 1a. 备份 yaml
cp llm.yaml llm.yaml.bak.2

# 1b. provider 改成不存在的 xxx
python3 -c "
import yaml
c = yaml.safe_load(open('llm.yaml'))
c['provider'] = 'xxx'
yaml.dump(c, open('llm.yaml', 'w'), allow_unicode=True, sort_keys=False, default_flow_style=False)
"

# 1c. 触发加载 → 期望 ConfigError
python3 -c "from llm_client import load_config; load_config()" 2>&1
# 期望：抛 ConfigError("provider 'xxx' not defined in providers")

# 1d. 恢复
mv llm.yaml.bak.2 llm.yaml
```

### 验证 2：错 base_url → traceback + fallback
```bash
cd /mnt/e/Daily

# 2a. 备份
cp llm.yaml llm.yaml.bak.3

# 2b. 把 9router base_url 改成不可达
python3 -c "
import yaml
c = yaml.safe_load(open('llm.yaml'))
c['providers']['9router']['base_url'] = 'https://unreachable.example.com/v1'
yaml.dump(c, open('llm.yaml', 'w'), allow_unicode=True, sort_keys=False, default_flow_style=False)
"

# 2c. 跑 step4 dry-run — 期望看到 traceback 但流水线走 fallback 完成
python3 step4.py --dry-run --date 2026-06-24 2>&1
# 期望：
# - stderr 含 traceback（D-007）
# - stdout 含 "⚠ LLM分类失败" 或类似 fallback 消息
# - exit 0，不限异常终止
# - 涉华判定返回 False，分类走关键词回退

# 2d. 类似验证 step7
python3 step7.py --dry-run --date 2026-06-24 2>&1
# 期望：
# - traceback + "⚠ API 异常: ..." + 3 次重试
# - 最终走 fallback_summarize 生成回退摘要

# 2e. 恢复
mv llm.yaml.bak.3 llm.yaml
```

### 验证 3：llm.yaml 不存在 → ConfigError
```bash
cd /mnt/e/Daily
# 临时改名
mv llm.yaml /tmp/llm.yaml.test
python3 -c "from llm_client import load_config; load_config()" 2>&1
# 期望：抛 ConfigError("llm.yaml not found at ...")
mv /tmp/llm.yaml.test llm.yaml
```

### 验证 4：call_sites 段缺 ID → ConfigError
```bash
cd /mnt/e/Daily
cp llm.yaml llm.yaml.bak.4
python3 -c "
import yaml
c = yaml.safe_load(open('llm.yaml'))
del c['call_sites']['china-relevance']
yaml.dump(c, open('llm.yaml', 'w'), allow_unicode=True, sort_keys=False, default_flow_style=False)
"
python3 -c "from llm_client import get_client; get_client('china-relevance')" 2>&1
# 期望：抛 ConfigError("call_site 'china-relevance' not defined")
mv llm.yaml.bak.4 llm.yaml
```

## 边界处理
1. **yaml 备份必须恢复**：每个子验证结束后用 `mv` 恢复备份
2. **不可逆操作保护**：冒号 url placeholder 是安全值，改回即可
3. **验证 2 需要真实 key**：如果 NINEROUTER_API_KEY 是空的，需要先设一个假值让它能走到 API 请求阶段

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | provider 写错 `xxx` → load_config 抛 ConfigError | stderr 含 "provider 'xxx' not defined in providers" |
| AC-02 | base_url 写错不可达 URL → step4 `--dry-run` | stderr 含 traceback，exit 0，流水线走 fallback |
| AC-03 | 同 AC-02 测 step7 `--dry-run` | stderr 含 traceback + "⚠ API 异常"，exit 0，走 fallback_summarize |
| AC-04 | llm.yaml 删除 china-relevance → get_client 抛 ConfigError | 错误含 "not defined" |
| AC-05 | llm.yaml 不存在 → load_config 抛 ConfigError | 错误含 "llm.yaml not found" |
| AC-06 | 所有 yaml 备份已恢复 | `grep "^provider:" llm.yaml` 输出 `provider: 9router` |
