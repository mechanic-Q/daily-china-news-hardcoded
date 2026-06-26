---
id: task-09
author: lmr
created_at: 2026-06-24 19:40:00
title: 干跑验证
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08]
blocks: [task-10]
requirement_ids: [FR-06]
decision_ids: [D-004@v1, D-006@v1]
allowed_paths:
  - /mnt/e/Daily/.env
  - /mnt/e/Daily/llm.yaml
---

# task-09: 干跑验证

## 修改文件
- 无代码修改。这是纯验证任务。可能临时改 `llm.yaml` 用于测试，测试完恢复。

## 覆盖来源
- Requirements: FR-06（切回旧 provider）
- Decisions: D-004@v1（旧 key 保留），D-006@v1（手动切回）

## 验证步骤

### 验证 1：检查代码清理度
```bash
# 1a. 确认 step4 和 step7 中没有旧 LLM 构造
cd /mnt/e/Daily
grep -rn "OpenAI(" step4.py step7.py | grep -v "llm_client" | grep -v "#"
# 期望：无输出（所有 OpenAI() 构造都被 llm_client 取代）

# 1b. 确认旧 model 字符串已清除
grep -rn "glm-4-flash\|minimax-m2.7" step4.py step7.py
# 期望：无输出

# 1c. 确认旧 base_url 已清除
grep -rn "open.bigmodel.cn\|api.minimax.chat" step4.py step7.py
# 期望：无输出
```

### 验证 2：配置完整性
```bash
cd /mnt/e/Daily

# 2a. yaml 可解析
python3 -c "import yaml; c = yaml.safe_load(open('llm.yaml')); print('OK:', sorted(c.keys()))"

# 2b. llm_client 可导入
python3 -c "from llm_client import load_config, get_client, call_llm; print('OK:', load_config()['provider'])"

# 2c. step4 / step7 可导入
python3 -c "import step4; print('step4 OK')"
python3 -c "import step7; print('step7 OK')"

# 2d. requirements 完整
pip install -r requirements.txt --quiet 2>&1 | tail -1
```

### 验证 3：dry-run 流水线（9router）
```bash
cd /mnt/e/Daily
# 确保 NINEROUTER_API_KEY 已设（用户手动填入）
export NINEROUTER_API_KEY="<用户填入真实 key>"

# step4: 生成 1新闻_链接.md
python3 step4.py --dry-run --date 2026-06-24 2>&1
# 期望：不报错，print 输出含涉华判定 + 分类 + 选出的 10 条精选

# step7: 生成 3新闻_概述.md
python3 step7.py --dry-run --date 2026-06-24 2>&1
# 期望：不报错，print 输出含每条摘要生成 + 栏目分组
```

### 验证 4：切回 Zhipu 重测
```bash
cd /mnt/e/Daily

# 4a. 备份 yaml
cp llm.yaml llm.yaml.bak

# 4b. 修改 yaml → Zhipu
python3 -c "
import yaml
c = yaml.safe_load(open('llm.yaml'))
c['provider'] = 'zhipu'
c['model'] = 'glm-4-flash'
yaml.dump(c, open('llm.yaml', 'w'), allow_unicode=True, sort_keys=False, default_flow_style=False)
"

# 4c. 确认 ZHIPU_API_KEY 有效
grep ZHIPU_API_KEY .env | grep -v '^#'

# 4d. 重跑 dry-run
python3 step4.py --dry-run --date 2026-06-24 2>&1
python3 step7.py --dry-run --date 2026-06-24 2>&1
# 期望：同样不报错，正常输出

# 4e. 恢复 yaml 到 9router
mv llm.yaml.bak llm.yaml
```

## 边界处理
1. **NINEROUTER_API_KEY 未设**：验证 3 会失败——这是期望行为，用户必须先填 key
2. **没有对应日期的数据**：`--dry-run` 会打印"文件不存在"，但不抛异常——这是预期
3. **yaml 备份安全**：用 `cp` 备份而不是 `mv`，防止断电/yaml 源丢失

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep -rn "OpenAI(" step4.py step7.py` 不含 import 外的构造 | 无手动 `OpenAI(base_url=...)` |
| AC-02 | `grep -rn "glm-4-flash\|minimax-m2.7" step4.py step7.py` | 无输出 |
| AC-03 | `pip install -r requirements.txt --quiet` | 无 error |
| AC-04 | `python3 step4.py --dry-run --date 2026-06-24` | exit 0，含分类/精选正常输出 |
| AC-05 | `python3 step7.py --dry-run --date 2026-06-24` | exit 0，含摘要正常输出 |
| AC-06 | yaml 切到 zhipu + glm-4-flash 重跑 step4/step7 | 同样 exit 0 |
| AC-07 | yaml 恢复后 `grep "^provider:" llm.yaml` | 输出 `provider: 9router` |
