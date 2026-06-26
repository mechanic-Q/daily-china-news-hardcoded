---
schema_version: 1
doc_type: module-card
module_id: orchestrator
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# orchestrator

## 定位
- 负责：5 个 step 脚本的串行编排 + 命令行参数透传 + 失败短路（fail-fast）
- 不负责：
  - 业务逻辑（所有抓取、分类、抽取、摘要、渲染均封装在 5 个 step 模块内部）
  - 并发 / 异步调度（严格串行执行）
  - 重试 / 退避（任一 step 失败立即终止整条流水线）
  - 状态持久化与断点续跑（依赖各 step 自身的幂等性）
  - 日志归档（仅输出到 stdout/stderr，由调用方负责重定向）

## 契约摘要

### 入口与参数
- 单一入口：`./run_all.sh`（bash 脚本，约 50 行）
- 参数解析（while + case 循环）：
  - `--date YYYY-MM-DD`：指定运行日期；未提供时回退到 `date +%Y-%m-%d`（今天，本地时区）
  - `--dry-run`：透传给每个 step，启用演练模式（不写入持久化产物）
  - 未知参数：写 stderr 后 `exit 1`，并打印用法提示

### 执行顺序（STEPS 数组）
1. `step1_3.py` — 采集 + 清洗 + 去重（合并原 step1/2/3 三个阶段）
2. `step4.py`   — 分类
3. `step6.py`   — 抽取（注意编号跳过 5）
4. `step7.py`   — 摘要
5. `step8.py`   — 渲染

### 失败处理
- 脚本头部 `set -euo pipefail`：未定义变量、管道中任一命令失败、未捕获错误均立即退出
- 每个 step 执行后显式检查 `$?`：非零则 echo `❌ <step> 失败，停止执行` 后 `exit 1`
- 全部成功后输出 `✅ 全管道完成: <date>`

### 输出格式
- 每个 step 执行前 echo 空行 + `═══ 运行: <step> --date <date> <dry_run> ═══`
- 全流程结束 echo 空行 + `✅ 全管道完成: <date>`
- 错误信息通过 `>&2` 写入 stderr

## 关键逻辑
```bash
# 1. 解析参数：while + case → DATE / DRY_RUN
# 2. DATE 兜底：if [[ -z "$DATE" ]]; then DATE=$(date +%Y-%m-%d); fi
# 3. SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"   # 解析脚本所在绝对目录
# 4. STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")
# 5. for step in "${STEPS[@]}":
#        python3 "$SCRIPT_DIR/$step" --date "$DATE" $DRY_RUN
#        if [[ $exit_code -ne 0 ]] → echo 失败 → exit 1
# 6. 全部完成 → echo ✅
```

## 注意事项

### 编号约定
- **step5 不存在**：流水线编号 1_3 → 4 → 6 → 7 → 8 是历史演进残留，跳过 5 是有意为之，不要尝试补齐
- **step1_3.py 命名**：合并了原 step1（抓取）、step2（清洗）、step3（去重）三个阶段为单一脚本，但仍保留下划线编号以体现职责范围

### 接口约束
- 5 个 step 脚本必须接受 `--date YYYY-MM-DD` 和 `--dry-run` 两个命令行参数
- 新增 step 或调整顺序时需同步更新 `STEPS` 数组
- 修改本脚本前需确保各 step 的 CLI 契约保持兼容

### Bash 陷阱
- `$DRY_RUN` 不加引号：当未指定 `--dry-run` 时变量为空字符串，需让 bash 自动丢弃该 token；加引号会向 python 传入一个空参数 `""`，可能被 argparse 拒绝
- `set -e` 与显式 `exit_code` 检查并存：`set -e` 本身已会在 step 失败时退出，显式 `if [[ $exit_code -ne 0 ]]` 的存在仅为打印中文错误提示后再退出，便于人工阅读
- `SCRIPT_DIR` 使用 `cd ... && pwd` 解析绝对路径，确保跨工作目录调用时 step 文件能被正确定位

### 可重入性
- 每个 step 必须对同一 `--date` 反复执行幂等（覆盖写或跳过已存在产物）
- 编排器自身不做状态持久化，重跑直接从 step1_3 开始

### 依赖
- bash 4+
- python3 ≥ 3.10（与各 step 一致）
- 5 个 step 脚本与 `run_all.sh` 位于同一目录

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
