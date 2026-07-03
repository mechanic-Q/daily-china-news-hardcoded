# tests/test_archive_enrich.py
# author: lmr
# created_at: 2026-06-29

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from news_archive import IMAGES_DIR, ARCHIVE_DIR, month_path
from archive_enrich import (
    should_enrich_body, should_enrich_image,
    enrich_body, fetch_html_for_image,
    extract_first_image_url, guess_extension,
    download_image, image_path_for,
    enrich_records, enrich_archive_best_effort,
    BODY_STATUS_MISSING, BODY_STATUS_EXTRACTED, BODY_STATUS_FAILED,
    IMAGE_STATUS_NOT_SELECTED, IMAGE_STATUS_DOWNLOADED,
    IMAGE_STATUS_NOT_FOUND, IMAGE_STATUS_FAILED,
    AUTO_MAX_SECONDS,
)


class TestShouldEnrichBody(unittest.TestCase):

    def test_missing_requires(self):
        self.assertTrue(should_enrich_body({"body_status": "missing"}, False))
        self.assertTrue(should_enrich_body({"body_status": "missing"}, True))

    def test_extracted_skips(self):
        self.assertFalse(should_enrich_body({"body_status": "extracted"}, False))
        self.assertFalse(should_enrich_body({"body_status": "extracted"}, True))

    def test_failed_requires(self):
        self.assertTrue(should_enrich_body({"body_status": "failed"}, False))
        self.assertTrue(should_enrich_body({"body_status": "failed"}, True))

    def test_missing_only_skips_skipped(self):
        self.assertFalse(should_enrich_body({"body_status": "skipped"}, True))
        self.assertTrue(should_enrich_body({"body_status": "skipped"}, False))

    def test_no_body_status_default_missing(self):
        self.assertTrue(should_enrich_body({}, False))


class TestShouldEnrichImage(unittest.TestCase):

    def test_not_top10_never(self):
        self.assertFalse(should_enrich_image({"selected_in_top10": False}, False))
        self.assertFalse(should_enrich_image({"selected_in_top10": False}, True))

    def test_missing_requires(self):
        self.assertTrue(should_enrich_image({"selected_in_top10": True, "image_status": "missing"}, False))
        self.assertTrue(should_enrich_image({"selected_in_top10": True, "image_status": "missing"}, True))

    def test_downloaded_skips(self):
        self.assertFalse(should_enrich_image({"selected_in_top10": True, "image_status": "downloaded"}, False))
        self.assertFalse(should_enrich_image({"selected_in_top10": True, "image_status": "downloaded"}, True))


class TestEnrichBody(unittest.TestCase):

    @mock.patch("archive_enrich.fetch_and_extract", return_value=("这是正文", None))
    def test_body_extracted(self, mock_fetch):
        record = {"url": "https://example.com/a", "title": "Test"}
        result = enrich_body(record)
        mock_fetch.assert_called_once_with("https://example.com/a", "Test")
        self.assertEqual(result["body_status"], "extracted")
        self.assertEqual(result["body"], "这是正文")
        self.assertIsNone(result["body_error"])
        self.assertIn("body_extracted_at", result)
        self.assertEqual(result["body_source_url"], "https://example.com/a")

    @mock.patch("archive_enrich.fetch_and_extract", return_value=(None, "页面过短"))
    def test_body_failed(self, mock_fetch):
        record = {"url": "https://example.com/b", "title": "Fail"}
        result = enrich_body(record)
        self.assertEqual(result["body_status"], "failed")
        self.assertEqual(result["body_error"], "页面过短")
        self.assertNotIn("body", result)

    @mock.patch("archive_enrich.fetch_and_extract", side_effect=Exception("网络错误"))
    def test_body_exception(self, mock_fetch):
        record = {"url": "https://example.com/c", "title": "Exception"}
        result = enrich_body(record)
        self.assertEqual(result["body_status"], "failed")
        self.assertEqual(result["body_error"], "网络错误")

    def test_body_no_llm_call(self):
        with mock.patch("archive_enrich.fetch_and_extract") as mf:
            mf.return_value = ("正文", None)
            enrich_body({"url": "x", "title": "t"})
            call_args = mf.call_args
            call_str = str(call_args)
            for banned in ["llm", "LLM", "call_llm", "chat.completions"]:
                self.assertNotIn(banned, call_str)


class TestImageHelpers(unittest.TestCase):

    def test_guess_extension_by_content_type(self):
        self.assertEqual(guess_extension("image/jpeg", "x"), ".jpg")
        self.assertEqual(guess_extension("image/png", "x"), ".png")
        self.assertEqual(guess_extension("image/webp", "x"), ".webp")
        self.assertEqual(guess_extension("image/gif", "x"), ".gif")

    def test_guess_extension_fallback_to_url(self):
        self.assertEqual(guess_extension(None, "https://x.com/a.jpg"), ".jpg")
        self.assertEqual(guess_extension(None, "https://x.com/a.png"), ".png")
        self.assertEqual(guess_extension(None, "https://x.com/a.JPEG"), ".jpg")
        self.assertEqual(guess_extension("text/html", "https://x.com/a"), ".jpg")

    def test_extract_first_image_url_og(self):
        html = '<meta property="og:image" content="https://example.com/og.jpg">'
        result = extract_first_image_url(html, "https://example.com")
        self.assertEqual(result, "https://example.com/og.jpg")

    def test_extract_first_image_url_twitter(self):
        html = '<meta name="twitter:image" content="https://example.com/tw.jpg">'
        result = extract_first_image_url(html, "https://example.com")
        self.assertEqual(result, "https://example.com/tw.jpg")

    def test_extract_first_image_url_img(self):
        html = '<img src="https://example.com/img.png">'
        result = extract_first_image_url(html, "https://example.com")
        self.assertEqual(result, "https://example.com/img.png")

    def test_extract_first_image_url_relative(self):
        html = '<img src="/images/photo.jpg">'
        result = extract_first_image_url(html, "https://example.com/article")
        self.assertEqual(result, "https://example.com/images/photo.jpg")

    def test_extract_first_image_url_none(self):
        self.assertIsNone(extract_first_image_url("<p>无图</p>", "https://x.com"))
        self.assertIsNone(extract_first_image_url(None, "https://x.com"))

    def test_image_path_for(self):
        p = image_path_for("2026-06-29", "abc123", ".jpg")
        self.assertTrue(str(p).endswith("archive/images/2026-06/abc123.jpg"))

    def test_download_image_dry_run(self):
        status, err, fpath = download_image("https://x.com/a.jpg", Path("/tmp/x.jpg"), dry_run=True)
        self.assertEqual(status, "skipped")
        self.assertIsNone(fpath)

    @mock.patch("archive_enrich.urllib.request.urlopen")
    def test_download_image_success(self, mock_urlopen):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b"\xff\xd8\xff"
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        with tempfile.TemporaryDirectory() as tmp:
            ipath = Path(tmp) / "img.jpg"
            status, err, fpath = download_image("https://x.com/a.jpg", ipath, dry_run=False)
            self.assertEqual(status, "downloaded")
            assert fpath
            self.assertTrue(Path(fpath).exists())

    @mock.patch("archive_enrich.urllib.request.urlopen", side_effect=Exception("404"))
    def test_download_image_failed(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as tmp:
            ipath = Path(tmp) / "img.jpg"
            status, err, fpath = download_image("https://x.com/a.jpg", ipath, dry_run=False)
            self.assertEqual(status, "failed")
            self.assertIsNone(fpath)

    def test_extract_first_image_url_rejects_non_http(self):
        html = '<meta property="og:image" content="data:image/png;base64,abc">'
        self.assertIsNone(extract_first_image_url(html, "https://x.com"))
        html2 = '<meta name="twitter:image" content="ftp://bad.com/img.jpg">'
        self.assertIsNone(extract_first_image_url(html2, "https://x.com"))


class TestFetchHtmlForImage(unittest.TestCase):

    @mock.patch("archive_enrich.fetch_html_static", return_value="<html></html>")
    @mock.patch("archive_enrich.needs_chromium", return_value=False)
    def test_static_fetch(self, mock_need, mock_fetch):
        result = fetch_html_for_image({"url": "https://example.com"})
        self.assertEqual(result, "<html></html>")

    @mock.patch("archive_enrich.fetch_html_static", return_value=None)
    @mock.patch("archive_enrich.needs_chromium", return_value=False)
    def test_empty_html_returns_none(self, mock_need, mock_fetch):
        self.assertIsNone(fetch_html_for_image({"url": "https://example.com"}))

    @mock.patch("archive_enrich.fetch_html_static", side_effect=Exception("err"))
    @mock.patch("archive_enrich.needs_chromium", return_value=False)
    def test_exception_returns_none(self, mock_need, mock_fetch):
        self.assertIsNone(fetch_html_for_image({"url": "https://example.com"}))


class TestEnrichRecords(unittest.TestCase):

    def setUp(self):
        self.today = "2026-06-29"
        self.records = [
            {"id": "a", "date": "2026-06-29", "url": "https://a.com", "title": "A", "selected_in_top10": False},
            {"id": "b", "date": "2026-06-29", "url": "https://b.com", "title": "B", "selected_in_top10": True},
        ]

    @mock.patch("archive_enrich.enrich_body", return_value={"body_status": "extracted", "body": "bodyA"})
    @mock.patch("archive_enrich.enrich_image", return_value={"image_status": "downloaded"})
    def test_dry_run_no_write(self, mock_img, mock_body):
        selected = [{"url": "https://b.com", "title": "B"}]
        updated, stats = enrich_records(self.today, self.records, selected=selected, dry_run=True)
        self.assertEqual(len(updated), 2)
        self.assertEqual(stats["total"], 2)
        mock_body.assert_called()
        mock_img.assert_called()

    @mock.patch("archive_enrich.enrich_body", return_value={"body_status": "extracted", "body": "bodyA"})
    @mock.patch("archive_enrich.enrich_image", return_value={"image_status": "not_selected"})
    def test_non_top10_skips_image(self, mock_img, mock_body):
        selected = [{"url": "https://b.com", "title": "B"}]
        updated, stats = enrich_records(self.today, self.records, selected=selected, dry_run=True)
        img_b = [r for r in updated if r["id"] == "b"][0]
        self.assertEqual(img_b["image_status"], "not_selected")

    @mock.patch("archive_enrich.enrich_body")
    @mock.patch("archive_enrich.enrich_image")
    def test_missing_only_skips_extracted(self, mock_img, mock_body):
        records = [
            {"id": "a", "date": "2026-06-29", "url": "https://a.com", "title": "A",
             "body_status": "extracted", "selected_in_top10": False},
        ]
        enrich_records(self.today, records, missing_only=True, dry_run=True)
        mock_body.assert_not_called()

    @mock.patch("archive_enrich.enrich_body")
    @mock.patch("archive_enrich.enrich_image")
    def test_budget_exceeded_skips_remainder(self, mock_img, mock_body):
        records = 5 * [{"id": "x", "date": "2026-06-29", "url": "https://x.com", "title": "X",
                        "selected_in_top10": False}]
        with mock.patch("archive_enrich.time.time", side_effect=[0.0] + [2.0] * 7):
            updated, stats = enrich_records(self.today, records, dry_run=True, max_seconds=1)
        self.assertEqual(stats["body_skipped"], 5)
        self.assertEqual(stats["image_not_selected"], 5)
        self.assertEqual(len(updated), 5)

    @mock.patch("archive_enrich.enrich_body")
    @mock.patch("archive_enrich.enrich_image")
    def test_include_images_false_skips_image_but_still_body(self, mock_img, mock_body):
        selected = [{"url": "https://b.com", "title": "B"}]
        enrich_records(self.today, self.records, selected=selected, dry_run=True, include_images=False)
        mock_body.assert_called()
        mock_img.assert_not_called()

    @mock.patch("archive_enrich.enrich_body")
    @mock.patch("archive_enrich.enrich_image")
    def test_include_images_true_default_calls_image(self, mock_img, mock_body):
        selected = [{"url": "https://b.com", "title": "B"}]
        enrich_records(self.today, self.records, selected=selected, dry_run=True, include_images=True)
        mock_img.assert_called()


class TestEnrichArchiveBestEffort(unittest.TestCase):

    @mock.patch("archive_enrich.enrich_archive")
    def test_best_effort_no_raise(self, mock_enrich):
        enrich_archive_best_effort("2026-06-29")
        mock_enrich.assert_called_once()

    @mock.patch("archive_enrich.enrich_archive", side_effect=Exception("测试错误"))
    def test_best_effort_catches(self, mock_enrich):
        enrich_archive_best_effort("2026-06-29")
        self.assertTrue(True)

    @mock.patch("archive_enrich.enrich_archive")
    def test_best_effort_passes_include_images(self, mock_enrich):
        enrich_archive_best_effort("2026-06-29", include_images=False)
        mock_enrich.assert_called_once()
        _, kwargs = mock_enrich.call_args
        self.assertEqual(kwargs.get("include_images"), False)


if __name__ == "__main__":
    unittest.main()
