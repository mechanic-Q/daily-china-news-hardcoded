---
id: task-03
title: 新增 archive_enrich.py CLI 与路径工具（覆盖：FR-05, FR-09, D-004@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-01]
blocks: [task-04, task-05, task-06]
requirement_ids: [FR-05, FR-09]
decision_ids: [D-004@v1]
allowed_paths: [archive_enrich.py]
goal: >
  在项目根目录新建 archive_enrich.py，提供 CLI 入口与路径/日期 helper，为后续正文补全与首图下载建立骨架。
implementation:
  - 新建 archive_enrich.py，#!/usr/bin/env python3，与 archive_news.py 同级的独立 CLI 模块
  - 从 news_archive 导入 BASE_DIR, ARCHIVE_DIR, ARTICLES_DIR, IMAGES_DIR, SCHEMA_VERSION
  - 定义常量：AUTO_MAX_SECONDS = 180, MAX_IMAGE_BYTES = 5 * 1024 * 1024, IMAGE_EXT_BY_TYPE（jpg/png/webp/gif）
  - handwrite parse_args：支持 --date, --missing-only, --dry-run, --max-seconds，风格同 archive_news.parse_args
  - 实现 image_month_dir(today_str) → ARCHIVE_DIR / "images" / "YYYY-MM"
  - 实现 main()：解析参数，print 日期与路径信息，dry-run 时打印目标路径与统计骨架
  - if __name__ == "__main__": main() 入口
  - 正文补全与首图函数只留函数签名占位（pass 或 return {}），备注由 task-04/task-05 实现
acceptance:
  - python3 archive_enrich.py 执行不报错，输出日期、目标 JSONL 路径、图片目录路径
  - python3 archive_enrich.py --date 2026-06-29 --dry-run 打印对应信息，不写文件
  - parse_args 正确处理 --missing-only 与 --max-seconds
  - 常量可被 from archive_enrich import AUTO_MAX_SECONDS 导入
verify:
  - python3 archive_enrich.py --date 2026-06-29 --dry-run
constraints:
  - 遵循项目风格：无 type hints，手写 parse_args，print 中文消息
  - 不实现正文提取逻辑（task-04）和图片下载逻辑（task-05）
  - 不引入 json 等不必要的 import（future tasks 可追加）
  - 不修改其他文件
---
