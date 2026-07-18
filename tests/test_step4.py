import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import step4
from daily.common import COLUMN_ORDER
from step4 import (
    is_china_related, is_china_source,
    _strip_llm_json, _extract_json_array,
    _parse_china_json_array, _parse_score_json_array,
    _chunks, is_quality_news,
    score_all_categories, high_confidence_keyword_category,
    llm_is_china_related_batch, score_signals, score_signals_batch,
    build_classification_result, run,
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


class TestEventDedup(unittest.TestCase):

    def test_same_normalized_url_is_duplicate_candidate(self):
        articles = [
            {
                "date": "2026-07-14",
                "title": "量子芯片发布",
                "url": "https://www.example.com/news/123?utm_source=feed",
            },
            {
                "date": "2026-07-14",
                "title": "南极科考启航",
                "url": "http://example.com/news/123",
            },
        ]

        self.assertEqual(step4.find_duplicate_candidate_groups(articles), [[0, 1]])

    def test_candidate_threshold_includes_eight_char_common_event_fragment(self):
        articles = [
            {
                "date": "2026-07-14",
                "title": "甲乙丙丁共同事件八个汉字戊己庚辛",
                "url": "https://example.com/a",
            },
            {
                "date": "2026-07-14",
                "title": "壹贰叁肆共同事件八个汉字伍陆柒玖",
                "url": "https://example.com/b",
            },
        ]

        self.assertEqual(step4.find_duplicate_candidate_groups(articles), [[0, 1]])

    def test_finds_perovskite_same_event_with_different_urls(self):
        articles = [
            {
                "date": "2026-07-14",
                "title": "新型钙钛矿-有机叠层太阳能电池光电转换效率刷新世界纪录",
                "url": "https://www.cas.cn/cm/202607/t20260714_5115479.shtml",
            },
            {
                "date": "2026-07-14",
                "title": "超28%！钙钛矿-有机叠层太阳能电池效率破纪录",
                "url": "https://www.cas.cn/cm/202607/t20260714_5115493.shtml",
            },
            {
                "date": "2026-07-14",
                "title": "钙钛矿太阳能电池产业化基地在江苏投产",
                "url": "https://example.com/independent-event",
            },
        ]

        groups = step4.find_duplicate_candidate_groups(articles)

        self.assertEqual(groups, [[0, 1]])

    def test_llm_review_keeps_one_article_from_same_event(self):
        articles = [
            {"title": "新型钙钛矿-有机叠层太阳能电池光电转换效率刷新世界纪录", "url": "https://example.com/a"},
            {"title": "超28%！钙钛矿-有机叠层太阳能电池效率破纪录", "url": "https://example.com/b"},
        ]
        raw = json.dumps({
            "duplicate_groups": [{
                "indices": [0, 1],
                "keep": 0,
                "reason": "同为28.04%稳态效率的同一项成果",
            }]
        }, ensure_ascii=False)

        with mock.patch("step4.call_llm", return_value=raw):
            kept, audit = step4.llm_review_duplicate_candidates(articles, [[0, 1]])

        self.assertEqual(kept, [articles[0]])
        self.assertEqual(audit[0]["removed"], [1])

    def test_llm_review_uses_local_indices_for_nonzero_candidate_group(self):
        articles = [
            {"title": f"独立新闻{i}", "url": f"https://example.com/{i}"}
            for i in range(15)
        ]
        articles[11]["title"] = "两部门紧急预拨4.3亿元中央自然灾害救灾资金"
        articles[14]["title"] = "两部门紧急预拨4.3亿元中央自然灾害救灾资金"
        raw = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": 0, "reason": "同一事件"}]
        }, ensure_ascii=False)

        with mock.patch("step4.call_llm", return_value=raw) as call:
            kept, audit = step4.llm_review_duplicate_candidates(articles, [[11, 14]])

        prompt = call.call_args.kwargs["messages"][1]["content"]
        self.assertIn("[0] 两部门紧急预拨", prompt)
        self.assertIn("[1] 两部门紧急预拨", prompt)
        self.assertNotIn("[11]", prompt)
        self.assertNotIn("[14]", prompt)
        self.assertNotIn(articles[14], kept)
        self.assertEqual(audit[0]["indices"], [11, 14])
        self.assertEqual(audit[0]["keep"], 11)

    def test_llm_review_skips_boolean_keep_index(self):
        articles = [
            {"title": "同一事件甲", "url": "https://example.com/a"},
            {"title": "同一事件乙", "url": "https://example.com/b"},
        ]
        raw = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": True, "reason": "同一事件"}]
        })

        with mock.patch("step4.call_llm", return_value=raw):
            kept, audit = step4.llm_review_duplicate_candidates(articles, [[0, 1]])

        self.assertEqual(kept, articles)
        self.assertEqual(audit, [])

    def test_llm_review_skips_singleton_group_and_processes_valid_group(self):
        articles = [
            {"title": "同一事件甲", "url": "https://example.com/a"},
            {"title": "同一事件乙", "url": "https://example.com/b"},
            {"title": "独立事件", "url": "https://example.com/c"},
        ]
        raw = json.dumps({
            "duplicate_groups": [
                {"indices": [2], "keep": 2, "reason": "错误的单元素组"},
                {"indices": [0, 1], "keep": 0, "reason": "同一事件"},
            ]
        }, ensure_ascii=False)

        with mock.patch("step4.call_llm", return_value=raw):
            kept, audit = step4.llm_review_duplicate_candidates(articles, [[0, 1, 2]])

        self.assertEqual(kept, [articles[0], articles[2]])
        self.assertEqual(audit[0]["removed"], [1])

    def test_llm_review_invalid_json_stops_with_context(self):
        articles = [
            {"title": "同一成果报道甲", "url": "https://example.com/a"},
            {"title": "同一成果报道乙", "url": "https://example.com/b"},
        ]

        with mock.patch("step4.call_llm", return_value="not json"):
            with self.assertRaisesRegex(ValueError, "event-dedup"):
                step4.llm_review_duplicate_candidates(articles, [[0, 1]])

    def test_classification_deduplicates_same_event_before_selection(self):
        today = datetime.date(2026, 7, 14)
        articles = [
            {
                "date": "2026-07-14",
                "title": "我国团队全球首次实现钙钛矿-有机叠层太阳能电池效率突破",
                "url": "https://www.cas.cn/news/a.shtml",
            },
            {
                "date": "2026-07-14",
                "title": "中国团队世界首次实现钙钛矿-有机叠层太阳能电池效率突破",
                "url": "https://www.cas.cn/news/b.shtml",
            },
        ]
        raw = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": 0, "reason": "同一项电池效率成果"}]
        }, ensure_ascii=False)

        with mock.patch("step4.parse_0", return_value=articles), \
             mock.patch("step4.call_llm", return_value=raw) as call:
            _, selected = step4.build_classification_result(today)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["url"], articles[0]["url"])
        self.assertEqual(call.call_args.args[0], "event-dedup")

    def test_llm_prompt_says_same_type_is_not_same_event(self):
        articles = [
            {"title": "王大明同志逝世", "url": "https://example.com/a"},
            {"title": "李彦同志逝世", "url": "https://example.com/b"},
        ]

        with mock.patch("step4.call_llm", return_value='{"duplicate_groups": []}') as call:
            kept, _ = step4.llm_review_duplicate_candidates(articles, [[0, 1]])

        prompt = call.call_args.kwargs["messages"][1]["content"]
        self.assertIn("同类型不等于同一事件", prompt)
        self.assertEqual(kept, articles)


def make_signals(base=5):
    return {
        "relevance": {col: base for col in COLUMN_ORDER},
        "importance": base,
        "timeliness": base,
    }


class TestParseChinaJsonArray(unittest.TestCase):

    def test_valid(self):
        raw = '[{"index": 0, "is_china_related": true}, {"index": 1, "is_china_related": false}]'
        self.assertEqual(_parse_china_json_array(raw, 2), [True, False])

    def test_valid_empty(self):
        self.assertEqual(_parse_china_json_array("[]", 0), [])

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            _parse_china_json_array('[{"index": 0, "is_china_related": true}]', 2)

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            _parse_china_json_array('[{"index": 0, "is_china_related": "true"}]', 1)


class TestParseScoreJsonArray(unittest.TestCase):

    def test_valid_2rows(self):
        raw = json.dumps([
            {"index": 0, **make_signals(8)},
            {"index": 1, **make_signals(3)},
        ], ensure_ascii=False)
        result = _parse_score_json_array(raw, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["relevance"]["🔬 世界性科研突破"], 8)
        self.assertEqual(result[1]["importance"], 3)

    def test_missing_row(self):
        raw = json.dumps([{"index": 0, **make_signals()}], ensure_ascii=False)
        with self.assertRaises(ValueError):
            _parse_score_json_array(raw, 2)

    def test_dup_index(self):
        raw = json.dumps([
            {"index": 0, **make_signals()},
            {"index": 0, **make_signals()},
        ], ensure_ascii=False)
        with self.assertRaises(ValueError):
            _parse_score_json_array(raw, 2)

    def test_wrong_schema(self):
        signals = make_signals()
        del signals["relevance"][COLUMN_ORDER[0]]
        raw = json.dumps([{"index": 0, **signals}], ensure_ascii=False)
        with self.assertRaises(ValueError):
            _parse_score_json_array(raw, 1)

    def test_out_of_range(self):
        raw = json.dumps([{"index": 2, **make_signals()}], ensure_ascii=False)
        with self.assertRaises(ValueError):
            _parse_score_json_array(raw, 1)


class TestBatchE2E(unittest.TestCase):

    def test_china_json_batch(self):
        articles = [
            {"title": "中国经济发展新成就", "url": "https://example.com/1"},
            {"title": "美国大选最新进展", "url": "https://example.com/2"},
            {"title": "北京冬奥会筹备顺利", "url": "https://example.com/3"},
        ]
        raw = json.dumps([
            {"index": 0, "is_china_related": True},
            {"index": 1, "is_china_related": False},
            {"index": 2, "is_china_related": True},
        ])
        with mock.patch('llm_client.call_llm', return_value=raw):
            result = llm_is_china_related_batch(articles)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], articles[0]['title'])
        self.assertEqual(result[1]['title'], articles[2]['title'])

    def test_china_batch_retries_before_single_fallback(self):
        articles = [
            {"title": "中国经济发展新成就", "url": "https://example.com/1"},
            {"title": "美国大选最新进展", "url": "https://example.com/2"},
        ]
        raw = json.dumps([
            {"index": 0, "is_china_related": True},
            {"index": 1, "is_china_related": False},
        ])
        with mock.patch('llm_client.call_llm', side_effect=["bad", raw]) as call:
            result = llm_is_china_related_batch(articles)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(result, [articles[0]])

    def test_score_json_batch(self):
        articles = [
            {"title": "AI新突破", "url": "https://example.com/1"},
            {"title": "航母军演", "url": "https://example.com/2"},
        ]
        raw = json.dumps([
            {"index": 0, **make_signals(9)},
            {"index": 1, **make_signals(4)},
        ], ensure_ascii=False)
        with mock.patch('step4.call_llm', return_value=raw):
            result = score_signals_batch(articles)
        self.assertEqual(len(result), 2)
        for signals in result:
            self.assertIsNotNone(signals)
            self.assertIn('relevance', signals)
            self.assertIn('importance', signals)
            self.assertIn('timeliness', signals)
            self.assertEqual(len(signals['relevance']), 9)

    def test_score_batch_failure_returns_none_for_single_llm_fallback(self):
        articles = [{"title": "AI新突破", "url": "https://example.com/1"}]
        with mock.patch('step4.call_llm', side_effect=["bad", "still bad"]):
            result = score_signals_batch(articles)
        self.assertEqual(result, [None])

    def test_score_signals_failure_does_not_fake_keyword_signals(self):
        with mock.patch('step4.call_llm', return_value="not json"):
            self.assertIsNone(score_signals("AI新突破", "新华社"))

    def test_e2e_signals_flow(self):
        today = datetime.date(2026, 7, 4)
        article = {
            "date": "2026-07-04",
            "title": "中美经贸摩擦最新动态",
            "url": "https://www.people.com.cn/n1/2026/0704/c1001-123.html",
        }
        raw = json.dumps([{"index": 0, **make_signals(9)}], ensure_ascii=False)
        with mock.patch('step4.parse_0', return_value=[article]), \
             mock.patch('step4.call_llm', return_value=raw):
            classified, selected = build_classification_result(today)
        all_articles = [a for items in classified.values() for a in items]
        self.assertEqual(len(all_articles), 1)
        result = all_articles[0]
        self.assertIsNotNone(result.get('signals'))
        self.assertEqual(result.get('score_source'), 'llm-batch')
        self.assertIn('category', result)
        self.assertIn('priority', result)

    def test_e2e_batch_failure_uses_single_llm_not_keyword_fake(self):
        today = datetime.date(2026, 7, 4)
        article = {
            "date": "2026-07-04",
            "title": "中美经贸摩擦最新动态",
            "url": "https://www.people.com.cn/n1/2026/0704/c1001-123.html",
        }
        with mock.patch('step4.parse_0', return_value=[article]), \
             mock.patch('step4.score_signals_batch', return_value=[None]), \
             mock.patch('step4.score_signals', return_value=make_signals(8)):
            classified, selected = build_classification_result(today)
        result = [a for items in classified.values() for a in items][0]
        self.assertEqual(result.get('score_source'), 'llm')
        self.assertIsNotNone(result.get('signals'))

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
            "score_source": "llm-batch",
            "category": "🚀 科技",
            "priority": 4.35,
        }
        selected_urls = {"https://example.com/news/123"}
        record = build_record(article, "2026-07-04", selected_urls)
        self.assertIn('signals', record)
        self.assertIn('category', record)
        self.assertIn('priority', record)
        self.assertTrue(record['selected_in_top10'])
        self.assertEqual(record['score_source'], 'llm-batch')

    def test_run_writes_published_at_to_selected_links(self):
        today = datetime.date(2026, 7, 4)
        article = {
            "url": "https://www.people.com.cn/n1/2026/0704/c1001-123.html",
            "title": "中美经贸摩擦最新动态",
            "date": "2026-07-04",
            "column": "🚀 科技",
            "priority": 7,
        }
        classified = {col: [] for col in COLUMN_ORDER}
        classified["🚀 科技"] = [article]
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("step4.BASE_DIR", Path(tmp)), \
             mock.patch("step4.build_classification_result", return_value=(classified, [article])), \
             mock.patch("news_archive.archive_articles_best_effort"), \
             mock.patch("archive_enrich.enrich_archive_best_effort"):
            (Path(tmp) / "2026-07-04").mkdir()
            run(today, dry_run=False)
            content = (Path(tmp) / "2026-07-04" / "1新闻_链接.md").read_text("utf-8")
        self.assertIn("URL：https://www.people.com.cn/n1/2026/0704/c1001-123.html", content)
        self.assertIn("发布时间：2026-07-04", content)


if __name__ == "__main__":
    unittest.main()
