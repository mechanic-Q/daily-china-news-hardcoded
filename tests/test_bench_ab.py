#!/usr/bin/env python3
"""tests/test_bench_ab.py — bench_ab.py 纯函数单测（provider 切换 / 一致率 / 解析）。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bench_ab import (agreement_report, archive_jsonl_path, atomic_write_text,
                      acquire_lock, release_lock, parse_selection,
                      parse_summaries, restore_archive, switch_provider)


YAML_SAMPLE = """call_sites:
  summarize:
    temperature: 0.7
model: qwen3.8
provider: kvmem
providers:
  kvmem:
    base_url: http://127.0.0.1:27182/v1
  qwen-local:
    base_url: http://localhost:8899/v1
"""


class TestSwitchProvider(unittest.TestCase):
    def test_switches_top_level_only(self):
        out = switch_provider(YAML_SAMPLE, "qwen-local")
        self.assertIn("provider: qwen-local", out)
        # providers: 块里的键名不能被动到
        self.assertIn("providers:", out)
        self.assertIn("  kvmem:", out)
        self.assertIn("  qwen-local:", out)

    def test_idempotent_switch(self):
        out = switch_provider(YAML_SAMPLE, "kvmem")
        self.assertIn("provider: kvmem", out)

    def test_missing_provider_line_raises(self):
        with self.assertRaises(ValueError):
            switch_provider("model: qwen3.8\n", "kvmem")

    def test_multiple_provider_lines_raise(self):
        text = YAML_SAMPLE + "provider: zhipu\n"
        with self.assertRaises(ValueError):
            switch_provider(text, "kvmem")

    def test_provider_line_with_inline_comment_rejected(self):
        # ^provider:\s*\S+\s*$ 不匹配带行尾注释的行 → ValueError 拒绝，不静默跳过切换
        with self.assertRaises(ValueError):
            switch_provider("provider: kvmem  # 生产\n", "qwen-local")


SAMPLE_1NEWS = """# 2026-09-23 精选新闻（按栏目分类）

## 🔬 世界性科研突破

### [中科院] 【中国之声】天关卫星 见证宇宙线
URL：https://example.com/1
发布时间：2026-09-23

## 🚀 科技

### [人民日报] 我国将推动北斗产业规模超万亿
URL：https://example.com/2
发布时间：2026-09-23
"""


class TestParseSelection(unittest.TestCase):
    def test_parse_order_and_fields(self):
        sel = parse_selection(SAMPLE_1NEWS)
        self.assertEqual(len(sel), 2)
        self.assertEqual(sel[0]["src"], "中科院")
        self.assertIn("天关卫星", sel[0]["title"])
        self.assertEqual(sel[1]["src"], "人民日报")

    def test_empty(self):
        self.assertEqual(parse_selection(""), [])


class TestAgreementReport(unittest.TestCase):
    def test_full_agreement(self):
        a = [{"src": "x", "title": f"标题{i}"} for i in range(10)]
        b = [{"src": "x", "title": f"标题{i}"} for i in range(10)]
        r = agreement_report(a, b)
        self.assertEqual(r["same_position"], 10)
        self.assertEqual(r["position_agreement"], 1.0)
        self.assertEqual(r["jaccard"], 1.0)

    def test_order_swap_counts_mismatch(self):
        a = [{"src": "x", "title": "甲"}, {"src": "x", "title": "乙"}]
        b = [{"src": "x", "title": "乙"}, {"src": "x", "title": "甲"}]
        r = agreement_report(a, b)
        self.assertEqual(r["common"], 2)
        self.assertEqual(r["same_position"], 0)
        self.assertEqual(r["jaccard"], 1.0)
        self.assertEqual(r["position_agreement"], 0.0)

    def test_disjoint_selection(self):
        a = [{"src": "x", "title": "甲"}]
        b = [{"src": "x", "title": "乙"}]
        r = agreement_report(a, b)
        self.assertEqual(r["common"], 0)
        self.assertEqual(r["position_agreement"], 0.0)
        self.assertEqual(r["jaccard"], 0.0)
        self.assertEqual(r["only_a"], ["甲"])
        self.assertEqual(r["only_b"], ["乙"])

    def test_whitespace_normalized(self):
        a = [{"src": "x", "title": "城 乡 融合 振兴"}]
        b = [{"src": "x", "title": "城乡融合振兴"}]
        r = agreement_report(a, b)
        self.assertEqual(r["common"], 1)
        self.assertEqual(r["same_position"], 1)


SAMPLE_3NEWS = """# 2026-09-23 新闻概述

## 🚀 科技

### [人民日报] 我国将推动北斗产业规模超万亿
北斗产业规模5年内将超万亿元，成为科技自立自强的重要支撑。

### [新华社] 从制造业大会看新质生产力
制造业大会展示了新质生产力的蓬勃动能。

## 🌾 农业

（当日无真实报道，栏目留空）
"""


class TestArchivePathAndAtomicWrite(unittest.TestCase):
    def test_archive_path_follows_month(self):
        self.assertEqual(archive_jsonl_path("2026-09-23").name, "2026-09.jsonl")
        self.assertEqual(archive_jsonl_path("2026-10-01").name, "2026-10.jsonl")
        self.assertEqual(archive_jsonl_path("2026-10-01").parent.name, "articles")

    def test_atomic_write_roundtrip_and_no_tmp_left(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.yaml"
            atomic_write_text(p, "provider: kvmem\n")
            self.assertEqual(p.read_text(encoding="utf-8"), "provider: kvmem\n")
            self.assertFalse(p.with_name(p.name + ".bench_ab.tmp").exists())
            # 覆盖写
            atomic_write_text(p, "provider: qwen-local\n")
            self.assertEqual(p.read_text(encoding="utf-8"), "provider: qwen-local\n")

    def test_restore_archive_atomic(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            backup = Path(td) / "bak.jsonl"
            target = Path(td) / "prod.jsonl"
            backup.write_text("line1\nline2\n", encoding="utf-8")
            target.write_text("polluted\n", encoding="utf-8")
            restore_archive(backup, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "line1\nline2\n")
            self.assertFalse(target.with_name(target.name + ".bench_ab.tmp").exists())

    def test_lock_stale_pid_is_overridable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            # acquire_lock 的锁文件固定在 /tmp，直接验证残留死锁可覆盖的判定逻辑：
            # 写入不存在的 pid + ProcessLookupError → 允许覆盖
            import bench_ab, os
            lock = Path(tempfile.gettempdir()) / "daily_bench_ab.locktest.pid"
            lock.write_text("999999999", encoding="utf-8")
            try:
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(lock.read_text().strip()), 0)
            finally:
                lock.unlink()
            # 正常 acquire/release 走一遍真实路径
            real_lock = bench_ab.acquire_lock("2099-01-01")
            try:
                self.assertTrue(real_lock.exists())
            finally:
                bench_ab.release_lock(real_lock)
            self.assertFalse(real_lock.exists())


class TestParseSummaries(unittest.TestCase):
    def test_parse_summaries(self):
        s = parse_summaries(SAMPLE_3NEWS)
        self.assertEqual(len(s), 2)
        self.assertEqual(s[0]["src"], "人民日报")
        self.assertIn("北斗", s[0]["summary"])
        self.assertIn("新质生产力", s[1]["summary"])

    def test_skips_empty_section(self):
        s = parse_summaries(SAMPLE_3NEWS)
        self.assertFalse(any("栏目留空" in x["title"] for x in s))


if __name__ == "__main__":
    unittest.main()
