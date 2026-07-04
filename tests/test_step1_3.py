import asyncio
import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from step1_3 import (
    _date_from_html,
    _date_from_url,
    fetch_cas,
    split_by_publish_date,
    verify_http,
    write_0,
)


class TestPublishDateParsing(unittest.TestCase):

    def test_date_from_cas_url(self):
        self.assertEqual(
            _date_from_url("https://www.cas.cn/syky/202607/t20260702_5114306.shtml"),
            "2026-07-02",
        )

    def test_date_from_cctv_url(self):
        self.assertEqual(
            _date_from_url("https://news.cctv.com/2026/07/04/ARTI.shtml"),
            "2026-07-04",
        )

    def test_date_from_html(self):
        html = "<div>发布时间：2026年7月4日 10:20</div>"
        self.assertEqual(_date_from_html(html), "2026-07-04")

    def test_unlabeled_body_date_is_not_publish_date(self):
        html = "<p>活动于2026年7月3日举行。</p>"
        self.assertIsNone(_date_from_html(html))

    def test_fetch_cas_only_collects_target_date_urls(self):
        today = datetime.date(2026, 7, 4)
        homepage = '''
        <a href="//www.cas.cn/../../syky/202607/t20260702_1.shtml">旧闻</a>
        <a href="//www.cas.cn/../../syky/202607/t20260704_2.shtml">今日</a>
        '''
        with mock.patch("step1_3.fetch_html_static", return_value=homepage), \
             mock.patch("step1_3._fetch_many_sync", return_value=["<title>今日科研突破----中国科学院</title>"]):
            items = fetch_cas(today)
        self.assertEqual(len(items), 1)
        self.assertIn("t20260704", items[0]["url"])
        self.assertEqual(items[0]["published_at"], "2026-07-04")


class TestSameDayGate(unittest.TestCase):

    def test_split_by_publish_date_rejects_old_and_missing_dates(self):
        today = datetime.date(2026, 7, 4)
        items = [
            {"title": "今日", "url": "https://example.com/a", "published_at": "2026-07-04"},
            {"title": "旧闻", "url": "https://example.com/b", "published_at": "2026-07-02"},
            {"title": "无日期", "url": "https://example.com/c", "published_at": None},
        ]
        with mock.patch("step1_3.fetch_published_at", return_value=None):
            passed, failed = split_by_publish_date(items, today)
        self.assertEqual([x["title"] for x in passed], ["今日"])
        self.assertEqual([x["reason"] for x in failed], ["非当日发布:2026-07-02", "无可信发布日期"])

    def test_verify_http_applies_date_gate_before_http(self):
        today = datetime.date(2026, 7, 4)
        items = [
            {"title": "今日", "url": "https://example.com/a", "published_at": "2026-07-04"},
            {"title": "旧闻", "url": "https://example.com/b", "published_at": "2026-07-02"},
        ]
        with mock.patch("step1_3.http_200_async", return_value=True):
            passed, failed, _ = asyncio.run(verify_http(items, today))
        self.assertEqual([x["title"] for x in passed], ["今日"])
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["reason"], "非当日发布:2026-07-02")

    def test_write_0_uses_item_published_at_not_run_date(self):
        today = datetime.date(2026, 7, 4)
        entries = [{
            "source": "测试源",
            "passed": [{"title": "测试标题", "url": "https://example.com/a", "published_at": "2026-07-03"}],
            "failed": [],
            "tool": "test",
        }]
        with mock.patch("step1_3.BASE_DIR", Path("/tmp/daily-test")):
            with mock.patch.object(Path, "write_text") as write_text:
                write_0(today, entries, dry_run=False)
        content = write_text.call_args.args[0]
        self.assertIn("[2026-07-03] 测试标题", content)
        self.assertNotIn("[2026-07-04] 测试标题", content)


if __name__ == "__main__":
    unittest.main()
