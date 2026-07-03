import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from step4 import (
    is_china_related, is_china_source,
    _strip_llm_json, _extract_json_array,
    _chunks, is_quality_news,
    score_all_categories, high_confidence_keyword_category,
)


class TestIsChinaRelated(unittest.TestCase):

    def test_china_keyword_xijinping(self):
        self.assertTrue(is_china_related("习近平会见外宾"))

    def test_china_keyword_beijing(self):
        self.assertTrue(is_china_related("北京举办活动"))

    def test_not_china_related(self):
        self.assertFalse(is_china_related("美国大选最新进展"))

    def test_china_keyword_south_china_sea(self):
        self.assertTrue(is_china_related("南海局势"))


class TestIsChinaSource(unittest.TestCase):

    def test_xinhuanet(self):
        self.assertTrue(is_china_source("https://xinhuanet.com/article"))

    def test_people_daily(self):
        self.assertTrue(is_china_source("https://people.com.cn/article"))

    def test_non_china_domain(self):
        self.assertFalse(is_china_source("https://bbc.com/article"))


class TestStripLlmJson(unittest.TestCase):

    def test_strip_think_block(self):
        result = _strip_llm_json("先思考<think>推理过程</think>然后回答")
        self.assertEqual(result, "先思考然后回答")

    def test_strip_markdown_fence(self):
        result = _strip_llm_json("```json\n{\"key\": \"value\"}\n```")
        self.assertEqual(result, '{"key": "value"}')

    def test_no_fence(self):
        result = _strip_llm_json('{"key": "value"}')
        self.assertEqual(result, '{"key": "value"}')


class TestExtractJsonArray(unittest.TestCase):

    def test_direct_array(self):
        self.assertEqual(_extract_json_array('[{"a": 1}]'), [{"a": 1}])

    def test_array_with_prefix_text(self):
        self.assertEqual(
            _extract_json_array('说明文字[{"a": 1}]更多文字'),
            [{"a": 1}],
        )

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            _extract_json_array("")


class TestChunks(unittest.TestCase):

    def test_chunks_exact(self):
        self.assertEqual(list(_chunks([1, 2, 3, 4], 2)), [[1, 2], [3, 4]])

    def test_chunks_with_remainder(self):
        self.assertEqual(list(_chunks([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]])


class TestIsQualityNews(unittest.TestCase):

    def test_valid_news(self):
        self.assertTrue(is_quality_news("两会召开"))

    def test_excluded_entertainment(self):
        self.assertFalse(is_quality_news("明星八卦"))

    def test_excluded_negative(self):
        self.assertFalse(is_quality_news("落马官员"))

    def test_empty_title(self):
        self.assertTrue(is_quality_news(""))


class TestScoreAllCategories(unittest.TestCase):

    def test_ai_title(self):
        scores = score_all_categories("人工智能大模型新突破")
        self.assertIn("🤖 AI智能前沿", scores)

    def test_military_title(self):
        scores = score_all_categories("航母编队军演")
        self.assertIn("🎖️ 军事", scores)

    def test_no_keywords(self):
        self.assertEqual(score_all_categories("今日天气晴朗"), {})


class TestHighConfidenceCategory(unittest.TestCase):

    def test_strong_ai_match(self):
        cat, scores = high_confidence_keyword_category(
            "人工智能大模型ChatGPT突破性进展"
        )
        self.assertIsNotNone(cat)
        self.assertIn("🤖 AI智能前沿", cat or "")

    def test_no_match(self):
        cat, scores = high_confidence_keyword_category("今日天气晴朗")
        self.assertIsNone(cat)
        self.assertIsNone(scores)


if __name__ == "__main__":
    unittest.main()
