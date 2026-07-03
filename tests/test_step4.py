import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daily.common import COLUMN_ORDER
from step4 import (
    is_china_related, is_china_source,
    _strip_llm_json, _extract_json_array,
    _parse_china_bitstring, _parse_score_matrix,
    _chunks, is_quality_news,
    score_all_categories, high_confidence_keyword_category,
    llm_is_china_related_batch, score_signals_batch,
    build_classification_result,
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


class TestParseChinaBitstring(unittest.TestCase):

    def test_valid(self):
        self.assertEqual(_parse_china_bitstring("101", 3), [True, False, True])

    def test_valid_empty(self):
        self.assertEqual(_parse_china_bitstring("", 0), [])

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            _parse_china_bitstring("10", 3)

    def test_invalid_chars(self):
        with self.assertRaises(ValueError):
            _parse_china_bitstring("10x1", 4)


class TestParseScoreMatrix(unittest.TestCase):

    def test_valid_2rows(self):
        raw = "0|8,7,6,5,4,3,2,1,0|9|3\n1|0,1,2,3,4,5,6,7,8|2|7"
        result = _parse_score_matrix(raw, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["relevance"]["🔬 世界性科研突破"], 8)
        self.assertEqual(result[0]["relevance"]["🎖️ 军事"], 0)
        self.assertEqual(result[0]["importance"], 9)
        self.assertEqual(result[0]["timeliness"], 3)
        self.assertEqual(result[1]["relevance"]["🔬 世界性科研突破"], 0)
        self.assertEqual(result[1]["relevance"]["🎖️ 军事"], 8)
        self.assertEqual(result[1]["importance"], 2)
        self.assertEqual(result[1]["timeliness"], 7)

    def test_missing_row(self):
        raw = "0|1,2,3,4,5,6,7,8,9|5|5"
        with self.assertRaises(ValueError):
            _parse_score_matrix(raw, 2)

    def test_dup_index(self):
        raw = "0|1,2,3,4,5,6,7,8,9|5|5\n0|9,8,7,6,5,4,3,2,1|3|4"
        with self.assertRaises(ValueError):
            _parse_score_matrix(raw, 2)

    def test_wrong_column_count(self):
        raw = "0|1,2,3,4,5,6,7,8|5|5"
        with self.assertRaises(ValueError):
            _parse_score_matrix(raw, 1)

    def test_out_of_range(self):
        raw = "0|1,2,3,4,5,6,7,8,11|5|5"
        with self.assertRaises(ValueError):
            _parse_score_matrix(raw, 1)


class TestBatchE2E(unittest.TestCase):

    def test_china_bitstring_batch(self):
        articles = [
            {"title": "中国经济发展新成就", "url": "https://example.com/1"},
            {"title": "美国大选最新进展", "url": "https://example.com/2"},
            {"title": "北京冬奥会筹备顺利", "url": "https://example.com/3"},
        ]
        with mock.patch('llm_client.call_llm', return_value="101"):
            result = llm_is_china_related_batch(articles)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], articles[0]['title'])
        self.assertEqual(result[1]['title'], articles[2]['title'])

    def test_score_matrix_batch(self):
        articles = [
            {"title": "AI新突破", "url": "https://example.com/1"},
            {"title": "航母军演", "url": "https://example.com/2"},
        ]
        matrix = "0|9,8,7,6,5,4,3,2,1|9|5\n1|1,2,3,4,5,6,7,8,9|3|8"
        with mock.patch('step4.call_llm', return_value=matrix):
            result = score_signals_batch(articles)
        self.assertEqual(len(result), 2)
        for signals in result:
            self.assertIn('relevance', signals)
            self.assertIn('importance', signals)
            self.assertIn('timeliness', signals)
            self.assertEqual(len(signals['relevance']), 9)

    def test_e2e_signals_flow(self):
        today = datetime.date(2026, 7, 4)
        article = {
            "date": "2026-07-04",
            "title": "中美经贸摩擦最新动态",
            "url": "https://example.com/news/123",
        }
        matrix = "0|9,8,7,6,5,4,3,2,1|9|5"
        with mock.patch('step4.parse_0', return_value=[article]), \
             mock.patch('step4.call_llm', return_value=matrix):
            classified, selected = build_classification_result(today)
        all_articles = [a for items in classified.values() for a in items]
        self.assertEqual(len(all_articles), 1)
        result = all_articles[0]
        self.assertIsNotNone(result.get('signals'))
        self.assertNotEqual(result.get('score_source'), 'keyword-fallback')
        self.assertIn('category', result)
        self.assertIn('priority', result)

    def test_archive_compatibility(self):
        from news_archive import build_record
        article = {
            "url": "https://example.com/news/123",
            "title": "中美经贸摩擦最新动态",
            "date": "2026-07-04",
            "signals": {
                "relevance": {col: 5 for col in COLUMN_ORDER},
                "importance": 5,
                "timeliness": 5,
            },
            "score_source": "matrix",
            "category": "🚀 科技",
            "priority": 4.35,
        }
        selected_urls = {"https://example.com/news/123"}
        record = build_record(article, "2026-07-04", selected_urls)
        self.assertIn('signals', record)
        self.assertIn('category', record)
        self.assertIn('priority', record)
        self.assertTrue(record['selected_in_top10'])
        self.assertEqual(record['score_source'], 'matrix')


if __name__ == "__main__":
    unittest.main()
