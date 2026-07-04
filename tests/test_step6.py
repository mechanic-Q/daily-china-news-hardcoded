import sys
import datetime
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from step6 import (
    _postprocess_text, _is_contaminated,
    _people_postprocess, _cas_postprocess, _cctv_postprocess,
    _extract_ckxx_content_txt,
    run,
)


class TestPostprocessText(unittest.TestCase):

    def test_postprocess_unescapes_html(self):
        result = _postprocess_text("Hello &amp; World")
        self.assertEqual(result, "Hello & World")

    def test_postprocess_removes_video_template(self):
        inp = "before[!--begin:htmlVideoCode--]data...[!--end:htmlVideoCode--]after"
        self.assertEqual(_postprocess_text(inp), "beforeafter")

    def test_postprocess_normalizes_whitespace(self):
        inp = "A  B\n\n\nC"
        self.assertEqual(_postprocess_text(inp), "A B C")

    def test_postprocess_dedup_sentences(self):
        inp = "A。A。"
        self.assertEqual(_postprocess_text(inp), "A。")

    def test_postprocess_people_removes_timestamp(self):
        inp = "content 2026-07-03 10:30:45:123456 /enpproperty--> tail"
        result = _postprocess_text(inp, "https://people.com.cn/article")
        self.assertNotIn("2026-07-03", result)
        self.assertNotIn("enpproperty", result)


class TestIsContaminated(unittest.TestCase):

    def test_contaminated_css_font_family(self):
        self.assertTrue(_is_contaminated("style=\"font-family: Arial\""))

    def test_contaminated_js_var_ih(self):
        self.assertTrue(_is_contaminated("foo var ih = document"))

    def test_contaminated_enpproperty(self):
        self.assertTrue(_is_contaminated("abc enpproperty--> xyz"))

    def test_clean_text_returns_false(self):
        self.assertFalse(_is_contaminated("正常新闻正文内容"))

    def test_contaminated_nav_kw(self):
        inp = "今天日报" + "x" * 50 + "本周周报" + "x" * 30 + "杂志导刊"
        self.assertTrue(_is_contaminated(inp))


class TestCasPostprocess(unittest.TestCase):

    def test_cas_removes_address_phone(self):
        inp = "内容。地址：北京市海淀区中关村邮编：100190 电话：010-12345678"
        result = _cas_postprocess(inp)
        self.assertNotIn("地址：", result)
        self.assertNotIn("电话：", result)
        self.assertNotIn("邮编：", result)


class TestCctvPostprocess(unittest.TestCase):

    def test_cctv_removes_ui_fragments(self):
        inp = "正文内容静音(m)全屏(f)播放(p)更多内容"
        result = _cctv_postprocess(inp)
        self.assertNotIn("静音(m)", result)
        self.assertNotIn("全屏(f)", result)
        self.assertNotIn("播放(p)", result)


class TestCkxxExtract(unittest.TestCase):

    def test_extract_ckxx_content_txt(self):
        content_txt = "test content " + "x" * 200
        html = f'''<html><script>var contentTxt = "{content_txt}"; var other = 1;</script></html>'''
        result = _extract_ckxx_content_txt(html)
        self.assertIsNotNone(result)
        self.assertIn("test content", result if result else "")

    def test_extract_ckxx_content_txt_too_short(self):
        html = '''<script>var contentTxt = "short"; var other = 1;</script>'''
        self.assertIsNone(_extract_ckxx_content_txt(html))

    def test_extract_ckxx_content_txt_not_found(self):
        html = "<html><body>no content</body></html>"
        self.assertIsNone(_extract_ckxx_content_txt(html))


class TestRunDatePropagation(unittest.TestCase):

    def test_run_uses_upstream_published_at(self):
        today = datetime.date(2026, 7, 4)
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("step6.BASE_DIR", Path(tmp)), \
             mock.patch("step6.fetch_and_extract", return_value=("正文内容", None)):
            workdir = Path(tmp) / "2026-07-04"
            workdir.mkdir()
            (workdir / "1新闻_链接.md").write_text(
                "# 2026-07-04 精选新闻\n\n"
                "## 🚀 科技\n\n"
                "### [人民日报] 测试新闻\n"
                "URL：https://example.com/a\n"
                "发布时间：2026-07-04\n",
                encoding="utf-8",
            )
            run(today, dry_run=False)
            content = (workdir / "2新闻_已审核.md").read_text("utf-8")
        self.assertIn("来源：人民日报  发布时间：2026-07-04", content)
