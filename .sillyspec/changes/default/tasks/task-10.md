---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-10
title: dry-run 集成验证
priority: P1
depends_on: [task-09]
blocks: [task-11]
requirement_ids: []
decision_ids: []
allowed_paths: []
---

## 修改文件

无（仅运行命令，记录输出）

## 覆盖来源

间接验证 FR-01~FR-08；S-02 dry-run / S-08 P95 ≤ 10 min

## 实现要求

1. 先确认 9router 本地服务可达：
   `curl -s http://localhost:20128/v1/models | head -c 200`
2. 跑 dry-run 历史日期：
   - `python3 step4.py --date 2026-06-25 --dry-run 2>&1 | tee /tmp/p13-dryrun-2026-06-25.log`
   - `python3 step4.py --date 2026-06-26 --dry-run 2>&1 | tee /tmp/p13-dryrun-2026-06-26.log`
3. 跑当天完整 step4（计时）：
   - `time python3 step4.py --date $(date +%F) 2>&1 | tee /tmp/p13-full.log`
4. 9router 离线降级测试（可选但建议）：
   - 临时把 llm.yaml base_url 改成无效地址或停 9router
   - `python3 step4.py --date 2026-06-25 --dry-run 2>&1 | tee /tmp/p13-offline.log`
   - 预期：stderr 有 `⚠ column-score 降级率` 输出，仍产出 top-10
   - 还原 llm.yaml
5. 旧 8 栏 1新闻_链接.md 兼容性：
   - 找一份旧 8 栏的 1新闻_链接.md 文件
   - `python3 step7.py --date <历史日期> --dry-run` 看是否报错

## 接口定义

不适用（运行型任务）

## 边界处理

1. 9router 不可达 → 全部走 legacy_path；不阻断
2. 真实日期目录缺失 → step4 输出 "0新闻_粗筛.md 为空"，跳过
3. dry-run 不落盘新文件
4. 真实运行会写 /mnt/e/每日新中国/<date>/1新闻_链接.md，需备份原文件
5. 离线降级测试后必须还原 llm.yaml
6. P95 ≤ 10 min：若超时记录但不立即 fail；P95 是软目标

## 非目标

- 不跑 step6 / step7 / step8 真实管道
- 不修改 run_all.sh
- 不做并发性能优化（Phase 14 范围）

## 参考

design §11 AC-01, AC-05

## TDD 步骤

1. 备份 /mnt/e/每日新中国/2026-06-25/1新闻_链接.md → .bak
2. 跑 dry-run 列表
3. diff 新 dry-run 输出 vs .bak 看栏目差异
4. 跑真实 step4 测 P95

## 验收标准

| AC-01 | dry-run 2026-06-25 exit 0 | True |
| AC-02 | dry-run 输出含 9 栏 heading（仅有数据的栏目） | True |
| AC-03 | dry-run 输出不含 "（当日无真实报道" | True |
| AC-04 | time 总耗时 ≤ 10 min（200 篇内） | True |
| AC-05 | 离线降级时 stderr 含 "⚠ column-score 降级率" | True |
| AC-06 | 旧 8 栏 md 由新 step7 解析不报错 | exit 0 |
