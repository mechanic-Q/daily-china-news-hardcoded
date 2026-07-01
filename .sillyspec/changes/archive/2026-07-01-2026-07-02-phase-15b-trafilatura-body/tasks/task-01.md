---
id: task-01
title: 新增或更新依赖声明，确保 `trafilatura` 可安装与导入（覆盖：FR-01, D-001@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on: []
blocks: []
requirement_ids: [FR-01]
decision_ids: [D-001@v1]
allowed_paths:
  - requirements.txt
goal: >
  在 requirements.txt 中声明 trafilatura>=1.12，使依赖可安装、可导入，
  为 Wave 2 正文抽取核心替换提供前置条件。
implementation:
  - 读取当前 requirements.txt，确认现有依赖与格式
  - 在文件末尾新增一行 `trafilatura>=1.12`，保持现有注释与条目不变
  - 执行 pip install 安装验证，确认 trafilatura 可成功导入
acceptance:
  - requirements.txt 包含 `trafilatura>=1.12`，且现有依赖不变
  - pip install -r requirements.txt 成功退出
  - python3 -c "import trafilatura" 成功，无 ImportError
verify:
  - pip install -r requirements.txt
  - python3 -c "import trafilatura"
constraints:
  - 仅修改 requirements.txt，不涉及其他文件
  - 保留现有注释头（author、created_at、外部依赖说明）和已有条目
  - 最低版本锁定 >=1.12，与 design.md D-001@v1 一致
  - 若 pip 安装失败（如系统缺编译工具），记录错误日志但不阻塞后续任务——该问题属环境准备而非任务失败
