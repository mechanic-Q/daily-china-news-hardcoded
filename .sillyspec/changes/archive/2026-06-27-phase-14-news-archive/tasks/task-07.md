---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-07
title: 新增 archive_news.py CLI
priority: P1
depends_on: [task-05]
blocks: [task-08]
requirement_ids: [FR-07]
decision_ids: [D-004@v1, D-010@v1]
allowed_paths:
  - archive_news.py
---

# task-07: 新增 archive_news.py CLI

## 修改文件
- `archive_news.py`（新文件）

## 覆盖来源
- Requirements: FR-07 (独立补跑命令)
- Decisions: D-004@v1 (archive_news.py --date)、D-010@v1 (build_classification_result 共享)

## 实现要求

创建独立 CLI 脚本 `archive_news.py`：

```python
#!/usr/bin/env python3
"""
archive_news.py — 独立历史日期补跑新闻归档
用法: python3 archive_news.py --date YYYY-MM-DD [--dry-run]
"""
import datetime
import sys
from pathlib import Path
from step4 import build_classification_result
from news_archive import archive_articles, archive_articles_best_effort
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

def parse_args():
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry

def main():
    today, dry_run = parse_args()
    today_str = today.strftime("%Y-%m-%d")

    print(f"═══ 新闻归档: {today_str} ═══")

    classified, selected = build_classification_result(today)

    if not classified:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    # 本次不调 best_effort wrapper（wrapper 也是 best-effort，此处简要版）
    from news_archive import archive_articles
    all_articles = []
    for items in classified.values():
        all_articles.extend(items)
    try:
        new, upd = archive_articles(all_articles, today_str, selected, dry_run)
        print(f"✅ 归档完成: {new}新 {upd}更新")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"⚠ 归档失败: {e}")

if __name__ == "__main__":
    main()
```

## 接口定义

CLI: `python3 archive_news.py --date YYYY-MM-DD [--dry-run]`
遵从项目约定：手写 `parse_args()`，`--date` 缺省当天，`--dry-run` 预览。

## 边界处理

1. 日期目录无 `0新闻_粗筛.md` → `build_classification_result` 返回空，正常终止
2. `--dry-run` → 穿透到 `archive_articles`，不落盘
3. JSONL 写失败 → catch Exception，打印 warning，exit 0
4. 重复跑同一日期 → 幂等（archived_at 保留，updated_at 更新）
5. 不写 `1新闻_链接.md` — 确保补跑不覆盖日报
6. 不写 type hints

## 非目标
- 不修改 `run_all.sh`
- 不支持批量日期
- 不实现正文/图片抓取

## 参考
- step4.py parse_args 模式
- archive_news.py 命令行风格与 step4.py 一致
- design.md §5.3 backfill CLI

## TDD 步骤
1. mock build_classification_result
2. 跑 `archive_news.py --date 2026-06-25 --dry-run`
3. 断言输出含 "✅ 归档完成" 且无文件写入
4. 确认测试通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `python3 archive_news.py --date 2026-06-25 --dry-run` 不报错 | exit 0 |
| AC-02 | 输入文件缺失 → 打印 "0新闻_粗筛.md 为空" | stdout 含 "为空" |
| AC-03 | 重复跑同一日期 → 同 URL 记录数不变 | archived_at 保持不变 |
| AC-04 | 不写 `1新闻_链接.md` | 日期目录下无新 md |
| AC-05 | 手写 parse_args 风格与 step4 一致 | `--date` / `--dry-run` 可用 |
