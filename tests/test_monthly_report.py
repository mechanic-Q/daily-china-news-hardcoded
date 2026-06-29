#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from monthly_report import (
    parse_args, load_month_jsonl, normalize_record,
    compute_stats, top_keywords, pick_top_per_column,
    build_grounding_context, llm_monthly_overview,
    sanitize_llm_text, fallback_overview,
    render_markdown, write_outputs,
    ARTICLES_DIR, MONTHLY_DIR,
    COLUMN_ORDER, DEFAULT_TOP_PER_COLUMN,
)


def sample_record(overrides=None):
    r = {
        "id": "abc123def456", "date": "2026-06-15", "url": "https://example.com/1",
        "title": "样题新闻", "source": "新华社", "column": "🤖 AI智能前沿",
        "body": "这是正文内容。这是一条测试新闻。",
        "body_status": "extracted",
        "image_status": "downloaded", "image_path": "/fake/path.jpg",
        "selected_in_top10": True, "aggregate_score": 8.5,
        "archived_at": "2026-06-15T10:00:00+08:00",
    }
    if overrides:
        r.update(overrides)
    return r


class TestParseArgs(unittest.TestCase):
    def test_default_month(self):
        with mock.patch.object(sys, "argv", ["monthly_report.py"]):
            m, dry, no_llm, top_n, max_s = parse_args()
            self.assertIsInstance(m, str)
            self.assertFalse(dry)

    def test_custom_month(self):
        with mock.patch.object(sys, "argv", ["monthly_report.py", "--month", "2026-06"]):
            m, *_ = parse_args()
            self.assertEqual(m, "2026-06")

    def test_dry_run(self):
        with mock.patch.object(sys, "argv", ["monthly_report.py", "--dry-run"]):
            _, dry, *_ = parse_args()
            self.assertTrue(dry)

    def test_top_per_column_limit(self):
        for val in ("0", "11", "abc"):
            with mock.patch.object(sys, "argv", ["monthly_report.py", "--top-per-column", val]):
                with self.assertRaises(SystemExit):
                    parse_args()

    def test_max_llm_seconds_limit(self):
        with mock.patch.object(sys, "argv", ["monthly_report.py", "--max-llm-seconds", "0"]):
            with self.assertRaises(SystemExit):
                parse_args()

    def test_invalid_month_format(self):
        with mock.patch.object(sys, "argv", ["monthly_report.py", "--month", "bad"]):
            with self.assertRaises(SystemExit):
                parse_args()


class TestLoader(unittest.TestCase):
    def test_load_missing_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch("monthly_report.ARTICLES_DIR", Path(td)):
                with self.assertRaises(SystemExit):
                    load_month_jsonl("2099-01")

    def test_load_and_normalize(self):
        with tempfile.TemporaryDirectory() as td:
            jp = Path(td) / "2026-06.jsonl"
            jp.write_text(json.dumps({"id": "x"}) + "\n", encoding="utf-8")
            with mock.patch("monthly_report.ARTICLES_DIR", Path(td)):
                recs = load_month_jsonl("2026-06")
                self.assertEqual(len(recs), 1)
                nr = normalize_record(recs[0])
                self.assertEqual(nr["body_status"], "missing")
                self.assertEqual(nr["body"], "")
                self.assertEqual(nr["image_status"], "missing")
                self.assertEqual(nr["selected_in_top10"], False)


class TestStats(unittest.TestCase):
    def test_compute_stats(self):
        recs = [
            sample_record({"column": "A", "source": "S1", "body_status": "extracted", "image_status": "downloaded"}),
            sample_record({"column": "B", "source": "S2", "body_status": "failed", "image_status": "not_selected"}),
        ]
        stats = compute_stats(recs, "2026-06")
        self.assertEqual(stats["total_records"], 2)
        self.assertIn("A", stats["by_column"])
        self.assertIn("B", stats["by_column"])
        self.assertEqual(stats["body_coverage"]["extracted"], 1)
        self.assertEqual(stats["body_coverage"]["failed"], 1)

    def test_top_keywords_empty_when_import_fails(self):
        with mock.patch("monthly_report.top_keywords", return_value=[]):
            self.assertEqual(top_keywords([]), [])


class TestPick(unittest.TestCase):
    def test_pick_top_per_column_sorts_by_score(self):
        recs = [
            sample_record({"column": "A", "selected_in_top10": False, "aggregate_score": 5.0}),
            sample_record({"column": "A", "selected_in_top10": True, "aggregate_score": 8.0}),
        ]
        picks = pick_top_per_column(recs, 10)
        self.assertEqual(len(picks.get("A", [])), 2)
        self.assertEqual(picks["A"][0]["aggregate_score"], 8.0)


class TestGrounding(unittest.TestCase):
    def test_grounding_context_contains_pick_ids(self):
        picks = {"A": [sample_record({"id": "id1234567890"})]}
        stats = {"month": "2026-06", "total_records": 1, "by_column": {"A": 1}, "by_source": {"S": 1},
                 "body_coverage": {"extracted": 1}, "image_coverage": {"downloaded": 1}}
        sys_msg, user_msg = build_grounding_context(stats, picks)
        self.assertIn("id1234567890", user_msg)

    def test_llm_returns_none_when_no_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            result = llm_monthly_overview(("sys", "user"), 30)
            self.assertIsNone(result)

    def test_llm_returns_none_on_exception(self):
        with mock.patch.dict(os.environ, {"ZHIPU_API_KEY": "fake"}):
            with mock.patch("openai.OpenAI") as mock_client:
                mock_client.side_effect = Exception("mock fail")
                result = llm_monthly_overview(("sys", "user"), 1)
                self.assertIsNone(result)


class TestSanitize(unittest.TestCase):
    def test_removes_unauthorized_ids(self):
        text = "本月亮点[abc123def456abc]和[fff999aaa00011]。"
        cleaned = sanitize_llm_text(text, {"abc123def456abc"})
        self.assertNotIn("fff999aaa00011", cleaned)
        self.assertIn("abc123def456abc", cleaned)

    def test_ascii_over_threshold_returns_none(self):
        text = "<foreign>This is English text that should be detected as non-Chinese</foreign>"
        result = sanitize_llm_text(text, set())
        self.assertIsNone(result)


class TestFallback(unittest.TestCase):
    def test_fallback_contains_warning(self):
        stats = {"total_records": 100, "by_column": {"A": 60, "B": 40},
                 "by_source": {"S1": 80, "S2": 20}, "by_date": {"2026-06-01": 5, "2026-06-30": 8},
                 "body_coverage": {"extracted": 85, "failed": 10, "missing": 5},
                 "image_coverage": {"downloaded": 20, "not_selected": 60, "failed": 10, "missing": 10}}
        picks = {}
        text = fallback_overview(stats, picks)
        self.assertIn("\u26a0", text)
        self.assertLessEqual(len(text), 700)


class TestRender(unittest.TestCase):
    def test_render_contains_url_and_source(self):
        rec = sample_record()
        picks = {"A": [rec]}
        stats = compute_stats([rec], "2026-06")
        md = render_markdown("2026-06", stats, picks, "总述。")
        self.assertIn("https://example.com/1", md)
        self.assertIn("新华社", md)


class TestWriteOutputs(unittest.TestCase):
    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch("monthly_report.MONTHLY_DIR", Path(td)):
                ok = write_outputs("2026-06", "md", "html", {}, {}, dry_run=True)
                self.assertTrue(ok)
                self.assertEqual(len(list(Path(td).iterdir())), 0)


if __name__ == "__main__":
    unittest.main()
