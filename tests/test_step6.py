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
    _extract_ckxx_content_txt, _extract_cas_article_txt,
    fetch_and_extract,
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


class TestCasArticleExtract(unittest.TestCase):

    def test_extract_cas_article_txt_skips_nav(self):
        html = (
            '<dl class="nav_down"><dd>主要职责</dd><dd>办院方针</dd>'
            '<dd>科技奖励</dd><dd>科技期刊</dd><dd>科技专项</dd>'
            '<dd>中国科学院学部</dd><dd>中国科学院院部</dd><dd>语音播报</dd></dl>'
            '<div class="xl_content"><div class="trs_editor_view TRS_UEDITOR trs_paper_default trs_web">'
            '<p>记者从中国科学院物理研究所获悉，该所孟庆波研究员团队成功制备出大面积铜锌锡硫硒薄膜光伏组件，'
            '组件光电转换效率达到13.0%，刷新了该类组件效率的世界纪录，为下一代低成本、环境友好型太阳能电池产业化奠定坚实基础。</p>'
            '<p>铜锌锡硫硒是一种新型薄膜光伏材料，由铜、锌、锡等地球储量丰富、价格低廉且环境友好的元素组成。</p></div></div>'
        )
        result = _extract_cas_article_txt(html)
        self.assertIsNotNone(result)
        for kw in ['主要职责', '办院方针', '科技奖励', '科技期刊', '科技专项', '语音播报']:
            self.assertNotIn(kw, result or "")
        self.assertIn('记者从中国科学院物理研究所获悉', result or "")

    def test_extract_cas_article_txt_no_container(self):
        html = '<html><body><p>没有 TRS 文章容器</p></body></html>'
        self.assertIsNone(_extract_cas_article_txt(html))

    def test_extract_cas_article_txt_video_caption(self):
        html = (
            '<div class="xl_content"><div class="trs_editor_view TRS_UEDITOR">'
            '<video src="x.mp4" width="700"></video>'
            '<p>揭示经典非溶剂诱导相分离成膜理论新机制（视频由AI生成）</p>'
            '</div><!--文章正文--></div>'
        )
        result = _extract_cas_article_txt(html)
        self.assertIsNotNone(result)
        self.assertIn('揭示经典非溶剂诱导相分离成膜理论新机制', result or "")

    def test_extract_cas_article_txt_too_short(self):
        html = '<div class="xl_content"><div class="trs_editor_view"><p>short</p></div></div>'
        self.assertIsNone(_extract_cas_article_txt(html))


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


class TestFetchAndExtractFallback(unittest.TestCase):

    def test_fallback_on_static_ssl_error(self):
        with \
            mock.patch("step6.chromium_dom", return_value=("<html>" + "x" * 1000 + "</html>")), \
            mock.patch("step6.fetch_html_static", side_effect=[None, Exception("SSL EOF")]):
            body, err = fetch_and_extract("https://example.com/a", "t")
        self.assertIsNone(err)
        self.assertIsNotNone(body)

    def test_fallback_on_chromium_empty_to_static(self):
        with \
            mock.patch("step6.chromium_dom", return_value=""), \
            mock.patch("step6.fetch_html_static", return_value="<html>" + "x" * 1000 + "</html>"), \
            mock.patch("step6.extract_body", return_value="正文内容"), \
            mock.patch("step6._postprocess_text", return_value="正文内容"):
            body, err = fetch_and_extract("https://military.cctv.com/article", "t")
        self.assertIsNotNone(body)

    def test_fail_closed_on_all_fallbacks_fail(self):
        with \
            mock.patch("step6.chromium_dom", return_value=""), \
            mock.patch("step6.fetch_html_static", return_value=None):
            body, err = fetch_and_extract("https://military.cctv.com/article", "t")
        self.assertIsNone(body)
        self.assertIsNotNone(err)


class TestRunFailClosed(unittest.TestCase):

    def test_run_raises_system_exit_on_failure(self):
        today = datetime.date(2026, 7, 5)
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("step6.BASE_DIR", Path(tmp)), \
             mock.patch("step6.fetch_and_extract", return_value=(None, "模拟失败")):
            workdir = Path(tmp) / "2026-07-05"
            workdir.mkdir()
            (workdir / "1新闻_链接.md").write_text(
                "# 2026-07-05 精选新闻\n\n"
                "## 🚀 科技\n\n"
                "### [人民日报] 测试新闻\n"
                "URL：https://example.com/a\n"
                "发布时间：2026-07-05\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                run(today, dry_run=False)
