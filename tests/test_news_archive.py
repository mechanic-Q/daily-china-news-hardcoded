# tests/test_news_archive.py
# author: lmr
# created_at: 2026-06-28

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from news_archive import (
    normalize_url, article_id, month_path,
    infer_source, build_record,
    load_month_records, write_month_records, archive_articles,
    archive_articles_best_effort,
)


class TestNewsArchive(unittest.TestCase):

    def test_normalize_url(self):
        self.assertEqual(normalize_url("https://example.com/path/"), "example.com/path")
        self.assertEqual(normalize_url("https://example.com/path?q=1"), "example.com/path")
        self.assertEqual(normalize_url(""), "")

    def test_article_id_stability(self):
        id1 = article_id("https://example.com/path")
        id2 = article_id("https://example.com/path/")
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 40)

    def test_month_path(self):
        p = month_path("2026-06-15")
        self.assertTrue(str(p).endswith("archive/articles/2026-06.jsonl"))

    def test_infer_source_xinhua(self):
        self.assertEqual(infer_source("https://news.cn/2026/test", {}), "新华社")
        self.assertEqual(infer_source("https://xinhuanet.com/test", {}), "新华社")

    def test_infer_source_cankaoxiaoxi(self):
        self.assertEqual(infer_source("https://cankaoxiaoxi.com/test", {}), "参考消息")
        self.assertEqual(infer_source("https://ckxxapp.ckxx.net/test", {}), "参考消息")

    def test_build_record_all_keys(self):
        article = {"url": "https://example.com/a", "title": "测试标题", "category": "🚀 科技", "priority": 8.5, "score_source": "llm", "signals": {"r": 1}}
        record = build_record(article, "2026-06-27", set())
        expected_keys = {"schema_version", "id", "date", "archived_at", "updated_at", "source", "url", "normalized_url", "title", "column", "category", "rank_within_column", "aggregate_score", "priority", "selected_in_top10", "score_source", "signals", "archive_status"}
        self.assertEqual(set(record.keys()), expected_keys)
        self.assertEqual(record["title"], "测试标题")
        self.assertEqual(record["priority"], 8.5)

    def test_build_record_selected_in_top10(self):
        article = {"url": "https://example.com/b", "title": "精选标题"}
        record = build_record(article, "2026-06-27", {"https://example.com/b"})
        self.assertTrue(record["selected_in_top10"])

    def test_build_record_not_selected(self):
        article = {"url": "https://example.com/c", "title": "非精选"}
        record = build_record(article, "2026-06-27", {"https://other.com"})
        self.assertFalse(record["selected_in_top10"])

    def test_build_record_signals_none(self):
        article = {"url": "https://example.com/d", "title": "无信号"}
        record = build_record(article, "2026-06-27", set())
        self.assertIsNone(record["signals"])

    def test_load_empty_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "2026-06.jsonl"
            result = load_month_records(p)
            self.assertEqual(result, {})

    def test_write_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "2026-06.jsonl"
            records = {
                "a": {"id": "a", "title": "A"},
                "b": {"id": "b", "title": "B"},
                "c": {"id": "c", "title": "C"},
            }
            write_month_records(p, records)
            loaded = load_month_records(p)
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded["a"]["title"], "A")

    def test_upsert_keep_archived_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "2026-06.jsonl"
            old_records = {
                "x": {"id": "x", "archived_at": "2026-06-01T00:00:00", "updated_at": "2026-06-01T00:00:00", "title": "Old"},
            }
            write_month_records(p, old_records)
            existing = load_month_records(p)
            self.assertEqual(existing["x"]["archived_at"], "2026-06-01T00:00:00")
            from datetime import datetime, timezone, timedelta
            CST = timezone(timedelta(hours=8))
            new_rec = {"id": "x", "archived_at": datetime.now(CST).isoformat(), "updated_at": datetime.now(CST).isoformat(), "title": "New"}
            new_rec["archived_at"] = existing["x"]["archived_at"]
            existing["x"] = new_rec
            write_month_records(p, existing)
            reloaded = load_month_records(p)
            self.assertEqual(reloaded["x"]["archived_at"], "2026-06-01T00:00:00")

    def test_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles = [{"url": "https://example.com/1", "title": "标题1"}]
            with mock.patch('news_archive.ARTICLES_DIR', Path(tmp)):
                archive_articles(articles, "2026-06-27", [], dry_run=True)
                expected = Path(tmp) / "2026-06.jsonl"
                self.assertFalse(expected.exists())

    def test_best_effort_catches_exception(self):
        with mock.patch('news_archive.archive_articles', side_effect=ValueError("mock error")):
            archive_articles_best_effort("2026-06-27", {"col": [{"url": "https://x.com/1", "title": "T"}]}, [])

    def test_best_effort_normal_path(self):
        with mock.patch('news_archive.archive_articles', return_value=(1, 0)):
            with mock.patch('builtins.print') as mock_print:
                archive_articles_best_effort("2026-06-27", {"col": [{"url": "https://x.com/1", "title": "T"}]}, [])
                mock_print.assert_any_call("✅ 新闻归档: 1新 0更新")

    def test_archive_uses_configured_articles_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles = [{"url": "https://example.com/a", "title": "A"}, {"url": "https://example.com/b", "title": "B"}]
            selected = [{"url": "https://example.com/a", "title": "A"}]
            with mock.patch('news_archive.ARTICLES_DIR', Path(tmp)):
                new, upd = archive_articles(articles, "2026-06-27", selected, dry_run=False)
                self.assertEqual(new, 2)
                self.assertEqual(upd, 0)
                expected = Path(tmp) / "2026-06.jsonl"
                self.assertTrue(expected.exists())
                loaded = load_month_records(expected)
                self.assertEqual(len(loaded), 2)
                self.assertTrue(loaded[article_id("https://example.com/a")]["selected_in_top10"])
                self.assertFalse(loaded[article_id("https://example.com/b")]["selected_in_top10"])

    def test_best_effort_dry_run_no_exception(self):
        archive_articles_best_effort("2026-06-27", {}, [], dry_run=True)


if __name__ == "__main__":
    unittest.main()
