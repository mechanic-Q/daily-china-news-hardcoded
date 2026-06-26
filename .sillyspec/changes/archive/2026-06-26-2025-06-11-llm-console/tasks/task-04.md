---
id: task-04
author: lmr
created_at: 2026-06-24 19:40:00
title: 追加 .env 新增 NINEROUTER_API_KEY 占位
priority: P0
depends_on: []
blocks: [task-09]
requirement_ids: []
decision_ids: [D-004@v1]
allowed_paths:
  - /mnt/e/Daily/.env
---

# task-04: 追加 .env 新增 NINEROUTER_API_KEY 占位

## 修改文件
- 修改 `/mnt/e/Daily/.env`（追加一行，不删旧 key）

## 覆盖来源
- Decisions: D-004@v1（新增 NINEROUTER_API_KEY，旧 key 保留）

## 实现要求
1. **必须先读现有 .env**，确认旧 key（MINIMAX_API_KEY, ZHIPU_API_KEY）位置
2. 用 append 追加 `NINEROUTER_API_KEY=` 占位行（值留空，用户手填）
3. 不修改 / 不删除任何已有行
4. 若已存在 NINEROUTER_API_KEY 行则跳过（幂等）

## 接口定义

预期最终内容（结构）：

```
# Daily 项目 .env (gitignored)
# author: lmr

# Zhipu AI - 应急 provider（保留）
ZHIPU_API_KEY=xxx

# MiniMax - 应急 provider（保留）
MINIMAX_API_KEY=xxx

# 9router - 主 provider（本次变更新增）
# TODO: 用户填入真实 API key
NINEROUTER_API_KEY=
```

## 实现命令示例

```bash
# 1. 检查是否已有
grep -q "^NINEROUTER_API_KEY" /mnt/e/Daily/.env

# 2. 不存在则追加（注意：不要 echo 到 .env 时多写空行）
if ! grep -q "^NINEROUTER_API_KEY" /mnt/e/Daily/.env; then
    printf "\n# 9router - 主 provider（本次变更新增）\n# TODO: 用户填入真实 API key\nNINEROUTER_API_KEY=\n" >> /mnt/e/Daily/.env
fi
```

## 边界处理
1. **.env 是敏感文件**：必须 append 不能 overwrite
2. **幂等性**：重复执行 task-04 不应导致重复行
3. **保留 gitignore 状态**：不动 .gitignore（已忽略 .env）
4. **占位值留空**：`NINEROUTER_API_KEY=` 后留空，避免误以为是真实 key
5. **明确 TODO 注释**：让用户知道要补值
6. **不修改文件权限**：保持现有 chmod
7. **跨平台**：避免使用 CRLF 行尾（用 LF）

## 非目标
- ❌ 不写真实 API key（保密）
- ❌ 不重命名旧 key（D-004 保留）
- ❌ 不创建 .env.example（YAGNI）
- ❌ 不修改 .gitignore

## 参考
- `.sillyspec/docs/Daily/scan/INTEGRATIONS.md` — 当前 .env 结构
- `.gitignore` — 已含 .env

## TDD 步骤
1. 备份现有 .env：`cp /mnt/e/Daily/.env /tmp/env.bak`
2. 执行追加
3. 验证：`diff /tmp/env.bak /mnt/e/Daily/.env` 应只新增行不动旧内容
4. 验证：`grep "^NINEROUTER_API_KEY" /mnt/e/Daily/.env` 返回 1 行

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep -c "^NINEROUTER_API_KEY" /mnt/e/Daily/.env` | 输出 1（恰好一行）|
| AC-02 | `grep -c "^ZHIPU_API_KEY" /mnt/e/Daily/.env` | 输出 1（旧 key 保留）|
| AC-03 | `grep -c "^MINIMAX_API_KEY" /mnt/e/Daily/.env` | 输出 1（旧 key 保留）|
| AC-04 | `grep "^NINEROUTER_API_KEY=" /mnt/e/Daily/.env` | 等号后允许为空（占位）|
| AC-05 | `grep "TODO" /mnt/e/Daily/.env` | 至少一行含 TODO |
| AC-06 | 重复执行追加逻辑 | `grep -c "^NINEROUTER_API_KEY" /mnt/e/Daily/.env` 仍为 1（幂等）|

## 执行结果

**状态**: completed (2026-06-24 19:30)

验收全部通过：

| AC | 结果 |
|----|------|
| AC-01 | NINEROUTER_API_KEY 计数 = 1 |
| AC-02 | ZHIPU_API_KEY 计数 = 1 |
| AC-03 | MINIMAX_API_KEY 计数 = 1 |
| AC-04 | NINEROUTER_API_KEY= 等号后为空 |
| AC-05 | TODO 注释存在 |
| AC-06 | 重复执行后计数仍为 1（幂等）|

文件最终行数：6 行（旧内容 3 行 + 新增 3 行）
