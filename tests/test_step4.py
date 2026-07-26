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
    _is_conditional_excluded, DIPLOMATIC_PROTOCOL,
    _is_non_research_title, NON_RESEARCH_TITLES,
    assign_category, WORLD_CLASS_CATEGORY, WORLD_CLASS_THRESHOLD,
    OUTLOOK_WORDS,
    _is_b2_breakthrough,
    _fetch_article_body,
)


def make_category_signals(category, relevance=9, base=0):
    return {
        "relevance": {
            col: relevance if col == category else base
            for col in COLUMN_ORDER
        },
        "importance": 5,
        "timeliness": 5,
    }


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


class TestSectorKeywords(unittest.TestCase):
    """行业词表补全验收:农业水稻育种 + 扶贫乡村振兴"""

    def test_agriculture_rice_breeding(self):
        scores = score_all_categories("我国水稻育种技术取得新进展")
        self.assertIn("🌾 农业", scores)
        self.assertGreater(scores["🌾 农业"], 0)

    def test_agriculture_hybrid_rice(self):
        scores = score_all_categories("杂交稻新品种通过审定")
        self.assertIn("🌾 农业", scores)

    def test_poverty_rural_revitalization(self):
        scores = score_all_categories("乡村振兴示范村建设取得阶段性成果")
        self.assertIn("🤝 扶贫", scores)

    def test_poverty_consolidate(self):
        scores = score_all_categories("巩固脱贫成果与乡村振兴有效衔接")
        self.assertIn("🤝 扶贫", scores)

    def test_rice_news_uses_keyword_path_e2e(self):
        article = {
            "date": "2026-07-25",
            "title": "我国水稻育种技术取得新进展",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-101.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4._fetch_article_body", return_value=None), \
             mock.patch("step4.call_llm", side_effect=AssertionError("should not call LLM")):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items]
        self.assertEqual(result[0]["category"], "🌾 农业")
        self.assertEqual(result[0]["score_source"], "keyword-high-confidence")

    def test_rural_revitalization_uses_keyword_path_e2e(self):
        article = {
            "date": "2026-07-25",
            "title": "我国乡村振兴示范村建设取得阶段性成果",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-102.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.llm_is_china_related_batch", return_value=[article]), \
             mock.patch("step4.call_llm", side_effect=AssertionError("should not call LLM")):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items]
        self.assertEqual(result[0]["category"], "🤝 扶贫")
        self.assertEqual(result[0]["score_source"], "keyword-high-confidence")


class TestConditionalExclusion(unittest.TestCase):
    """B3 纯政治剔除 + 条件排除 helper"""

    def test_diplomatic_protocol_no_sector_excluded(self):
        """纯外交礼宾词,无行业关键词 -> 剔除"""
        result = _is_conditional_excluded(
            "泰国总理阿努廷会见董军",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertTrue(result)

    def test_diplomatic_with_sector_keyword_rescued(self):
        """外交事件+行业关键词 -> 不剔除(如能源协议)"""
        result = _is_conditional_excluded(
            "中俄签署能源合作协议",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertFalse(result)

    def test_diplomatic_joint_exercise_rescued(self):
        """联合军演(军事关键词) -> 不剔除"""
        result = _is_conditional_excluded(
            "中俄联合军演",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertFalse(result)

    def test_single_industry_keyword_rescues_protocol_event(self):
        result = _is_conditional_excluded(
            "习近平会见俄能源部长",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertFalse(result)

    def test_diplomatic_g20_excluded(self):
        """纯政治峰会发言 -> 剔除"""
        result = _is_conditional_excluded(
            "习近平出席G20峰会发言",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertTrue(result)

    def test_weak_cooperation_word_does_not_rescue_pure_politics(self):
        """军事栏弱词“合作”不能把纯政治会见救回"""
        result = _is_conditional_excluded(
            "中美元首会见共商合作",
            DIPLOMATIC_PROTOCOL,
            rescue_categories=COLUMN_ORDER,
        )
        self.assertTrue(result)

    def test_ticket_examples_e2e(self):
        today = datetime.date(2026, 7, 25)
        articles = [
            {"date": "2026-07-25", "title": "泰国总理阿努廷会见董军", "url": "https://www.news.cn/20260725/a.html"},
            {"date": "2026-07-25", "title": "中俄签署能源合作协议", "url": "https://www.news.cn/20260725/b.html"},
            {"date": "2026-07-25", "title": "中俄联合军演", "url": "https://www.news.cn/20260725/c.html"},
            {"date": "2026-07-25", "title": "习近平出席G20峰会发言", "url": "https://www.news.cn/20260725/d.html"},
        ]
        with mock.patch("step4.parse_0", return_value=articles), \
             mock.patch("step4.score_signals_batch", return_value=[
                 make_category_signals("⚡ 能源"),
                 make_category_signals("🎖️ 军事"),
             ]):
            classified, _ = build_classification_result(today)
        results = {a["title"]: a["category"] for items in classified.values() for a in items}
        self.assertNotIn(articles[0]["title"], results)
        self.assertEqual(results[articles[1]["title"]], "⚡ 能源")
        self.assertEqual(results[articles[2]["title"]], "🎖️ 军事")
        self.assertNotIn(articles[3]["title"], results)


class TestNonResearchGuard(unittest.TestCase):
    """T4 世突非科研负向闸"""

    def _make_world_signals(self, world_relevance=8, base=5):
        return {
            "relevance": {col: base for col in COLUMN_ORDER}
            | {WORLD_CLASS_CATEGORY: world_relevance},
            "importance": base,
            "timeliness": base,
        }

    def test_assign_category_blocks_non_research(self):
        """溃坝标题即使 LLM 给世突高分也不入世突"""
        signals = self._make_world_signals(8)
        cat = assign_category(signals, "国务院成立广西六蓝水库溃坝灾害调查评估组")
        self.assertIsNotNone(cat)
        self.assertNotEqual(cat, WORLD_CLASS_CATEGORY)

    def test_assign_category_allows_research(self):
        """真科研标题正常入世突"""
        signals = self._make_world_signals(8)
        cat = assign_category(signals, "量子计算研究取得重大突破")
        self.assertEqual(cat, WORLD_CLASS_CATEGORY)

    def test_non_research_guard_hits_non_research_title(self):
        self.assertTrue(_is_non_research_title("溃坝灾害调查评估"))
        self.assertTrue(_is_non_research_title("权威发布"))
        self.assertFalse(_is_non_research_title("量子计算重大突破"))
        self.assertFalse(_is_non_research_title("基于调查评估的遥感算法研究"))

    def test_dam_break_llm_override_blocked_e2e(self):
        today = datetime.date(2026, 7, 25)
        article = {
            "date": "2026-07-25",
            "title": "国务院成立广西六蓝水库溃坝灾害调查评估组",
            "url": "https://www.news.cn/20260725/dam.html",
        }
        signals = make_category_signals("🚀 科技", 7)
        signals["relevance"][WORLD_CLASS_CATEGORY] = 8
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.score_signals_batch", return_value=[signals]):
            classified, _ = build_classification_result(today)
        result = [a for items in classified.values() for a in items][0]
        self.assertNotEqual(result["category"], WORLD_CLASS_CATEGORY)


class TestArchetypeKeywords(unittest.TestCase):
    """T5 世突 A+B1 原型词表 + 剪过广词"""

    def test_agriculture_a_prototype(self):
        """杂交水稻世界首例 -> 世突(A原型,高分关键词路径)"""
        scores = score_all_categories("我国杂交水稻一系1号是世界首例")
        self.assertIn(WORLD_CLASS_CATEGORY, scores)
        self.assertGreater(scores[WORLD_CLASS_CATEGORY], 6)

    def test_agriculture_routine_stays_agriculture(self):
        """常规水稻育种无突破信号 -> 农业(不被世突抢)"""
        scores = score_all_categories("水稻育种常规推广")
        self.assertIn("🌾 农业", scores)
        if WORLD_CLASS_CATEGORY in scores:
            self.assertLess(scores[WORLD_CLASS_CATEGORY], scores["🌾 农业"])

    def test_routine_satellite_goes_to_tech_not_world(self):
        """例行卫星发射 -> 科技(世突中卫星已降权)"""
        scores = score_all_categories("我国成功发射天仪48星等5颗卫星")
        self.assertIn("🚀 科技", scores)
        if WORLD_CLASS_CATEGORY in scores:
            self.assertLess(scores[WORLD_CLASS_CATEGORY], scores["🚀 科技"])

    def test_routine_satellite_routes_to_tech_e2e(self):
        article = {
            "date": "2026-07-25",
            "title": "我国成功发射天仪48星等5颗卫星",
            "url": "https://www.news.cn/20260725/example.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.call_llm", side_effect=AssertionError("should not call LLM")):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items]
        self.assertEqual(result[0]["category"], "🚀 科技")
        self.assertEqual(result[0]["score_source"], "keyword-high-confidence")

    def test_euv_lithography_routes_to_world_e2e(self):
        article = {
            "date": "2026-07-25",
            "title": "国产EUV光刻机下线",
            "url": "https://www.news.cn/20260725/euv.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.call_llm", side_effect=AssertionError("should not call LLM")):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items][0]
        self.assertEqual(result["category"], WORLD_CLASS_CATEGORY)
        self.assertEqual(result["score_source"], "keyword-b2")

    def test_co2_starch_routes_to_world_e2e(self):
        article = {
            "date": "2026-07-25",
            "title": "二氧化碳人工合成淀粉 世界首例",
            "url": "https://www.cas.cn/20260725/starch.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.call_llm", side_effect=AssertionError("should not call LLM")):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items][0]
        self.assertEqual(result["category"], WORLD_CLASS_CATEGORY)
        self.assertEqual(result["score_source"], "keyword-high-confidence")


class TestOutlookExclusion(unittest.TestCase):
    """T3 展望/口号剔除"""

    def test_outlook_no_rescue_excluded(self):
        """展望口号词无具体行动 -> 剔除"""
        result = _is_conditional_excluded(
            "夺取全年粮食丰收有较好基础",
            OUTLOOK_WORDS,
            rescue_word_groups=(step4.OUTLOOK_ACTION_WORDS, step4.OUTLOOK_OBJECT_WORDS),
        )
        self.assertTrue(result)

    def test_outlook_slogan_excluded(self):
        """纯口号无具体行动 -> 剔除"""
        result = _is_conditional_excluded(
            "进一步实现扩量提质可靠替代",
            OUTLOOK_WORDS,
            rescue_word_groups=(step4.OUTLOOK_ACTION_WORDS, step4.OUTLOOK_OBJECT_WORDS),
        )
        self.assertTrue(result)

    def test_outlook_with_action_rescued(self):
        """展望词+具体行动词 -> 不剔除(如部署工程)"""
        result = _is_conditional_excluded(
            "印发可再生能源发展十五五规划部署X工程",
            OUTLOOK_WORDS,
            rescue_word_groups=(step4.OUTLOOK_ACTION_WORDS, step4.OUTLOOK_OBJECT_WORDS),
        )
        self.assertFalse(result)

    def test_no_outlook_not_excluded(self):
        """无展望词 -> 不剔除"""
        result = _is_conditional_excluded(
            "我国成功发射天仪48星",
            OUTLOOK_WORDS,
            rescue_word_groups=(step4.OUTLOOK_ACTION_WORDS, step4.OUTLOOK_OBJECT_WORDS),
        )
        self.assertFalse(result)

    def test_scientific_stability_term_is_not_outlook(self):
        """“稳定同位素”不是展望套话"""
        result = _is_conditional_excluded(
            "我国稳定同位素研究取得世界首次成果",
            OUTLOOK_WORDS,
            rescue_word_groups=(step4.OUTLOOK_ACTION_WORDS, step4.OUTLOOK_OBJECT_WORDS),
        )
        self.assertFalse(result)

    def test_ticket_examples_e2e(self):
        articles = [
            {"date": "2026-07-25", "title": "夺取全年粮食丰收有较好基础(权威发布)", "url": "https://www.news.cn/20260725/outlook.html"},
            {"date": "2026-07-25", "title": "进一步实现扩量提质可靠替代", "url": "https://www.news.cn/20260725/slogan.html"},
            {"date": "2026-07-25", "title": "印发可再生能源发展十五五规划部署X工程", "url": "https://www.news.cn/20260725/action.html"},
        ]
        with mock.patch("step4.parse_0", return_value=articles), \
             mock.patch("step4.score_signals_batch", return_value=[make_category_signals("⚡ 能源")]):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        results = {a["title"]: a["category"] for items in classified.values() for a in items}
        self.assertNotIn(articles[0]["title"], results)
        self.assertNotIn(articles[1]["title"], results)
        self.assertEqual(results[articles[2]["title"]], "⚡ 能源")


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
        dedup_raw = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": 0, "reason": "同一项电池效率成果"}]
        }, ensure_ascii=False)
        # After dedup: 2 articles → 1. Then LLM needs signals for that remaining article.
        score_fallback = make_signals(8)

        with mock.patch("step4.parse_0", return_value=articles), \
             mock.patch("step4.call_llm", side_effect=[dedup_raw, json.dumps([{"index": 0, **score_fallback}], ensure_ascii=False)]):
            _, selected = step4.build_classification_result(today)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["url"], articles[0]["url"])

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


class TestB2Breakthrough(unittest.TestCase):
    """T6 世突 B2 白名单+信号+新突破闸"""

    def test_deepseek_b2(self):
        """DeepSeek全栈自主 -> B2世突"""
        self.assertTrue(_is_b2_breakthrough(
            "DeepSeek大模型国产算力光模块全栈自主可控"
        ))

    def test_c919_production_b2(self):
        """C919投产 -> B2世突"""
        self.assertTrue(_is_b2_breakthrough("C919大飞机首次投产"))

    def test_phone_mass_production_not_b2(self):
        """国产手机量产 -> 非B2(手机非前沿域)"""
        self.assertFalse(_is_b2_breakthrough("国产手机规模化量产交付"))

    def test_tons_breakthrough_not_b2(self):
        """突破1亿吨(数量) -> 非B2(无前沿域)"""
        self.assertFalse(_is_b2_breakthrough("杂交水稻种植面积突破1亿亩"))

    def test_frontier_and_signal_without_milestone_not_b2(self):
        """只有前沿域+国产化信号，没有新突破里程碑 -> 非B2"""
        self.assertFalse(_is_b2_breakthrough("C919大飞机实现国产化"))

    def test_frontier_and_milestone_without_signal_not_b2(self):
        """只有前沿域+首次里程碑，没有全链/国产化信号 -> 非B2"""
        self.assertFalse(_is_b2_breakthrough("C919大飞机首次亮相"))

    def test_first_delivery_is_milestone_not_routine(self):
        self.assertTrue(_is_b2_breakthrough("C919大飞机国产化首次交付"))

    def test_numbered_delivery_is_routine(self):
        self.assertFalse(_is_b2_breakthrough("C919大飞机国产化第100架交付"))

    def test_ticket_examples_e2e(self):
        articles = [
            {"date": "2026-07-25", "title": "DeepSeek大模型国产算力光模块全栈自主", "url": "https://www.news.cn/20260725/deepseek.html"},
            {"date": "2026-07-25", "title": "C919大飞机投产", "url": "https://www.news.cn/20260725/c919.html"},
            {"date": "2026-07-25", "title": "国产手机规模化量产", "url": "https://www.news.cn/20260725/phone.html"},
            {"date": "2026-07-25", "title": "杂交水稻种植面积突破1亿亩", "url": "https://www.news.cn/20260725/rice.html"},
        ]
        phone = make_category_signals("🚀 科技")
        quantity = make_category_signals("🌾 农业", 7)
        quantity["relevance"][WORLD_CLASS_CATEGORY] = 8
        with mock.patch("step4.parse_0", return_value=articles), \
             mock.patch("step4._fetch_article_body", return_value=None), \
             mock.patch("step4.score_signals_batch", return_value=[phone, quantity]):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        results = {a["title"]: a["category"] for items in classified.values() for a in items}
        self.assertEqual(results[articles[0]["title"]], WORLD_CLASS_CATEGORY)
        self.assertEqual(results[articles[1]["title"]], WORLD_CLASS_CATEGORY)
        self.assertEqual(results[articles[2]["title"]], "🚀 科技")
        self.assertEqual(results[articles[3]["title"]], "🌾 农业")


class TestBodySignalG1(unittest.TestCase):
    """T8 正文信号 G1"""

    def test_weak_title_strong_body_routes_to_world(self):
        """#41 原始杂交水稻标题+正文A信号 -> 世突，并复用step6抽取"""
        today = datetime.date(2026, 7, 25)
        article = {
            "date": "2026-07-25",
            "title": "我国杂交水稻育种科研取得重要进展",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-123.html",
        }
        body_with_signal = "中国水稻研究所王克剑团队成功研发一系法杂交水稻'一系1号'，克隆效率超99%，论文发表于《生命》期刊，属世界首例。"
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4._fetch_article_body", return_value=body_with_signal) as fetch:
            classified, selected = step4.build_classification_result(today)
        result = [a for items in classified.values() for a in items]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], WORLD_CLASS_CATEGORY)
        self.assertEqual(result[0]["score_source"], "body-signal")
        fetch.assert_called_once_with(article["url"], article["title"])

    def test_weak_medical_research_title_triggers_body_signal(self):
        article = {
            "date": "2026-07-25",
            "title": "我国疗法研制取得重要进展",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-789.html",
        }
        body = "该疗法完成同行评议并发表于期刊，是全球首例，填补空白。"
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4._fetch_article_body", return_value=body):
            classified, _ = build_classification_result(datetime.date(2026, 7, 25))
        result = [a for items in classified.values() for a in items][0]
        self.assertEqual(result["category"], WORLD_CLASS_CATEGORY)
        self.assertEqual(result["score_source"], "body-signal")

    def test_no_research_keyword_does_not_trigger_fetch(self):
        """标题无研究/科研等词 -> 不触发正文抓取"""
        today = datetime.date(2026, 7, 25)
        article = {
            "date": "2026-07-25",
            "title": "今日天气晴朗",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-456.html",
        }
        with mock.patch("step4.parse_0", return_value=[article]), \
             mock.patch("step4.call_llm") as mocked_llm, \
             mock.patch("step4._fetch_article_body") as mocked_fetch:
            _, _ = step4.build_classification_result(today)
        mocked_fetch.assert_not_called()


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
            assert signals is not None
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

    def test_e2e_b2_deepseek_routes_to_world(self):
        """DeepSeek B2 突破 -> 世突(不被AI栏抢)"""
        today = datetime.date(2026, 7, 25)
        article = {
            "date": "2026-07-25",
            "title": "DeepSeek大模型国产算力光模块全栈自主可控",
            "url": "https://www.people.com.cn/n1/2026/0725/c1001-123.html",
        }
        self.assertEqual(
            high_confidence_keyword_category(article["title"])[0],
            "🤖 AI智能前沿",
        )
        with mock.patch('step4.parse_0', return_value=[article]), \
             mock.patch('step4.call_llm') as mocked_llm:
            classified, selected = build_classification_result(today)
        all_items = [a for items in classified.values() for a in items]
        self.assertEqual(len(all_items), 1)
        result = all_items[0]
        self.assertEqual(result.get('category'), WORLD_CLASS_CATEGORY)
        self.assertEqual(result.get('score_source'), 'keyword-b2')

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
