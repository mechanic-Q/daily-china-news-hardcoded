---
id: task-03
author: lmr
created_at: 2026-06-24 19:40:00
title: 编写 requirements.txt
priority: P1
depends_on: []
blocks: [task-09]
requirement_ids: []
decision_ids: []
risk_ids: [R-03]
allowed_paths:
  - /mnt/e/Daily/requirements.txt
---

# task-03: 编写 requirements.txt

## 修改文件
- 新增 `/mnt/e/Daily/requirements.txt`

## 覆盖来源
- Risks: R-03（依赖锁定，解决 known-issue「无 requirements.txt」）
- 顺手解决 known-issues.md 中的「无 requirements.txt」🟡 风险

## 实现要求
1. 列出 Daily 项目所有运行时依赖（5 个包）
2. 不锁死小版本号（用 >= 而不是 ==），方便后续升级
3. 顶部加注释说明用途和外部依赖（Chromium）

## 接口定义

```
# Daily 项目 Python 依赖
# author: lmr
# created_at: 2026-06-24
#
# 外部依赖（非 pip）：
# - Chromium headless: /snap/bin/chromium (apt: chromium-browser 或 snap install chromium)
# - Python: 3.12+

openai>=1.0          # OpenAI SDK（兼容 Zhipu/MiniMax/9router 等 base_url 协议）
aiohttp>=3.9         # step1_3.py 异步 HTTP-200 校验
Pillow>=10.0         # step8.py 截图后底部空白裁剪
python-dotenv>=1.0   # .env 文件加载
PyYAML>=6.0          # llm.yaml 解析（新增依赖，本次变更引入）
```

## 边界处理
1. **不锁死版本**：用 `>=` 而非 `==`，让 pip 选最新兼容版
2. **不引入测试依赖**（无单元测试）
3. **不引入开发依赖**（无 linter 配置）
4. **注释 Chromium**：requirements.txt 只能列 pip 包，外部工具用注释提示
5. **不分离 dev/prod**：项目无此区分

## 非目标
- ❌ 不引入 pyproject.toml（YAGNI，requirements.txt 已够用）
- ❌ 不引入 pip-tools / poetry / pipenv
- ❌ 不锁定具体 patch 版本

## 参考
- `.sillyspec/docs/Daily/scan/INTEGRATIONS.md` §4 Python 包
- `.sillyspec/knowledge/known-issues.md` — 「无 requirements.txt」风险

## TDD 步骤
1. 写文件
2. `pip install -r /mnt/e/Daily/requirements.txt --dry-run` 不报错（dry-run 验证可解析）
3. 实际 `pip install -r /mnt/e/Daily/requirements.txt`

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `ls /mnt/e/Daily/requirements.txt` | 文件存在 |
| AC-02 | `grep -cE "^(openai|aiohttp|Pillow|python-dotenv|PyYAML)" /mnt/e/Daily/requirements.txt` | 输出 5 |
| AC-03 | `pip install -r /mnt/e/Daily/requirements.txt --dry-run 2>&1` | 无 error |
| AC-04 | `grep "Chromium" /mnt/e/Daily/requirements.txt` | 注释含 Chromium 说明 |
