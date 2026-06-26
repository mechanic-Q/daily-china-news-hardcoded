---
id: task-01
title: 编写 llm.yaml 配置
priority: P0
depends_on: []
blocks: [task-02, task-05, task-06, task-07]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-002@v1, D-009@v1, D-011@v1]
allowed_paths:
  - /mnt/e/Daily/llm.yaml
---

# task-01: 编写 llm.yaml 配置

## 修改文件
- 新增 `/mnt/e/Daily/llm.yaml`

## 覆盖来源
- Requirements: FR-01（集中配置加载）
- Decisions: D-001@v1（9router 私有, base_url 占位）, D-002@v1（low 字符串）, D-009@v1（统一管理无 vision 预留）, D-011@v1（temperature 统一 0.7）

## 实现要求
1. 文件路径：`/mnt/e/Daily/llm.yaml`（项目根目录）
2. 顶部加 YAML 注释 `# author: lmr` 和 `# created_at: 2026-06-24`
3. 完整 schema 见接口定义
4. base_url 用 placeholder + TODO 注释（D-001）
5. 3 个 call_sites 的 temperature 全部为 0.7（D-011）
6. providers 段保留 zhipu/minimax 应急 provider（D-004）

## 接口定义
完整文件内容：

```yaml
# author: lmr
# created_at: 2026-06-24

provider: 9router
model: low

providers:
  9router:
    base_url: https://9router.example.com/v1   # TODO: 用户填入真实 base_url
    api_key_env: NINEROUTER_API_KEY
  zhipu:
    base_url: https://open.bigmodel.cn/api/paas/v4/
    api_key_env: ZHIPU_API_KEY
  minimax:
    base_url: https://api.minimax.chat/v1
    api_key_env: MINIMAX_API_KEY

call_sites:
  china-relevance:
    temperature: 0.7
    max_tokens: 10
    timeout: 15
  column-classify:
    temperature: 0.7
    max_tokens: 10
    timeout: 15
  summarize:
    temperature: 0.7
    max_tokens: 300
    timeout: 30
```

## 边界处理
1. **占位符 base_url**：用 example.com 域名，明确标 TODO，避免误以为是真实地址
2. **应急 provider 保留**：zhipu / minimax 必须存在于 providers 段，否则 yaml 切回失败
3. **call_sites 不可少 3 项**：china-relevance / column-classify / summarize 三个 ID 必须存在
4. **api_key_env 字段格式**：纯环境变量名（不带 $ 符号、不带引号外的空格）
5. **YAML 缩进**：2 空格缩进，不混 tab
6. **文件编码**：UTF-8 无 BOM
7. **不要写入实际 key**：api_key 不放在 yaml，仅放 env name

## 非目标
- 不实现 yaml 加载逻辑（task-02 做）
- 不引入 profiles 段（D-009 已决定无 vision 预留）
- 不加 fallback 段（D-006 不做运行时 fallback）
- 不加 retry 段（重试逻辑在 step7 业务侧）

## 参考
- `.sillyspec/docs/Daily/scan/INTEGRATIONS.md` — Zhipu/MiniMax base_url 来源
- `.sillyspec/docs/Daily/scan/PROJECT.md` — 当前 LLM provider 列表

## TDD 步骤
（配置文件，无独立测试）
1. 写文件
2. `python3 -c "import yaml; print(yaml.safe_load(open('llm.yaml')))"` 验证可解析
3. 验证 dict 结构含 provider/model/providers/call_sites 4 个 key

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `ls -la /mnt/e/Daily/llm.yaml` | 文件存在，size > 0 |
| AC-02 | `python3 -c "import yaml; c = yaml.safe_load(open('/mnt/e/Daily/llm.yaml')); print(sorted(c.keys()))"` | 输出 `['call_sites', 'model', 'provider', 'providers']` |
| AC-03 | `python3 -c "import yaml; c = yaml.safe_load(open('/mnt/e/Daily/llm.yaml')); print(c['provider'], c['model'])"` | 输出 `9router low` |
| AC-04 | `python3 -c "import yaml; c = yaml.safe_load(open('/mnt/e/Daily/llm.yaml')); print(sorted(c['call_sites'].keys()))"` | 输出 `['china-relevance', 'column-classify', 'summarize']` |
| AC-05 | `python3 -c "import yaml; c = yaml.safe_load(open('/mnt/e/Daily/llm.yaml')); print([s['temperature'] for s in c['call_sites'].values()])"` | 三个值都是 0.7 |
| AC-06 | `grep TODO /mnt/e/Daily/llm.yaml` | 至少 1 处含 TODO 注释 |
| AC-07 | `grep -E "(MINIMAX_API_KEY|ZHIPU_API_KEY|NINEROUTER_API_KEY)" /mnt/e/Daily/llm.yaml | wc -l` | 输出 3 |
