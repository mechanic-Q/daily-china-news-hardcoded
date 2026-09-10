import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daily.common import (
    BLOCKED_NEWS_TERMS,
    contains_blocked_term,
    clean_news_title,
)


class TestContainsBlockedTerm(unittest.TestCase):

    def test_detects_xijinping_in_title(self):
        self.assertTrue(contains_blocked_term("习近平向全国教师致以节日祝贺"))

    def test_detects_chairman_variant(self):
        self.assertTrue(contains_blocked_term("习主席视察某部队"))
        self.assertTrue(contains_blocked_term("习总书记的重要论述"))

    def test_detects_variant_after_real_verb_prefix(self):
        # 落实/贯彻/会见 + 习主席 是真指称，必须命中
        self.assertTrue(contains_blocked_term("深入贯彻落实习主席重要讲话精神"))
        self.assertTrue(contains_blocked_term("会见习主席并举行会谈"))
        self.assertTrue(contains_blocked_term("认真学习习主席重要讲话"))

    def test_does_not_misfire_on_study_verb_plus_chairman(self):
        # 学习/练习/复习 + 主席（泛指）不应误伤
        self.assertFalse(contains_blocked_term("学习主席重要讲话精神"))
        self.assertFalse(contains_blocked_term("练习主席台礼仪"))
        self.assertFalse(contains_blocked_term("复习主席团会议纪要"))

    def test_plain_chairman_reference_passes(self):
        self.assertFalse(contains_blocked_term("国家主席令发布"))
        self.assertFalse(contains_blocked_term("主席团会议举行"))

    def test_detects_in_body_list(self):
        body = "9月9日，习近平在会议上发表重要讲话，强调要推动高质量发展。"
        self.assertTrue(contains_blocked_term(body))

    def test_clean_text_returns_false(self):
        self.assertFalse(contains_blocked_term("我国科学家在云南发现丹尼索瓦人化石"))

    def test_empty_and_none_return_false(self):
        self.assertFalse(contains_blocked_term(""))
        self.assertFalse(contains_blocked_term(None))

    def test_terms_are_single_source_of_truth(self):
        for term in BLOCKED_NEWS_TERMS:
            self.assertTrue(contains_blocked_term(f"新闻标题含有{term}字样"))


class TestCleanNewsTitleStillWorks(unittest.TestCase):

    def test_strips_source_prefix(self):
        self.assertEqual(
            clean_news_title("【新华社】科学家发布新模型"),
            "科学家发布新模型",
        )


if __name__ == "__main__":
    unittest.main()
