import sys
import json
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import step7


class TestPlaceholderRetryChain(unittest.TestCase):
    """占位文本必须永不进入概述：LLM 顽固输出占位 → 重试3次耗完 → 返回 None → 走规则 fallback。"""

    def test_placeholder_never_survives_llm_summarize(self):
        placeholder = "由于提供的正文仅包含日期和天气，未包含具体新闻事实，无法概括实质内容。现有信息仅表明9月1日天气晴朗。"
        with mock.patch("llm_client.call_llm", return_value=placeholder) as m:
            result = step7.llm_summarize("一根玉米", "9月1日 晴\n真实正文…")
        # 3 次尝试全部被占位拦截 → 返回 None（不把占位当摘要）
        self.assertIsNone(result)
        self.assertEqual(m.call_count, 3)

    def test_placeholder_then_good_summary_accepted(self):
        placeholder = "请提供新闻正文内容，我才能根据具体信息生成摘要。"
        good = "泥石流灾害后，村民达娃免费向救援人员及群众提供热玉米。"
        with mock.patch("llm_client.call_llm", side_effect=[placeholder, good]) as m:
            result = step7.llm_summarize("一根玉米", "9月1日 晴\n真实正文…")
        # 第1次占位被拦截 → 重试 → 第2次正常 → 返回好摘要
        self.assertEqual(result, good)
        self.assertEqual(m.call_count, 2)

    def test_placeholder_worker_falls_back_to_rule_summary(self):
        """整条 worker 链路：LLM 占位 → llm_summarize None → fallback_summarize 用真实首句。"""
        placeholder = "请提供新闻正文内容，我才能根据具体信息生成摘要。"
        body = "9月1日 晴。中午采访完，我又去了趟安置点。在村口，村民达娃捞出一根玉米递过来。"
        with mock.patch("llm_client.call_llm", return_value=placeholder):
            idx, summary, fallback = step7.summarize_article_worker(0, {"title": "一根玉米", "body": body})
        self.assertTrue(fallback)
        # fallback 用真实正文首句，不含占位特征
        self.assertIn("采访完", summary)
        for pat in step7.PLACEHOLDER_PATTERNS:
            self.assertNotIn(pat, summary)


class TestPlaceholderDetection(unittest.TestCase):
    def test_placeholder_summary_detected(self):
        # 2026-09-02 实际占位文本
        bad = "由于提供的正文仅包含日期和天气，未包含具体新闻事实，无法概括实质内容。现有信息仅表明9月1日天气晴朗。"
        self.assertEqual(step7._why_invalid(bad, "真实正文"), "placeholder")

    def test_normal_summary_passes(self):
        good = "泥石流灾害后，村民达娃免费向救援人员及群众提供热玉米，其子尼玛多吉亦积极协助物资运输。"
        self.assertIsNone(step7._why_invalid(good, "真实正文"))


class TestParse2NewsMultilineBody(unittest.TestCase):
    def test_multiline_body_is_not_truncated(self):
        tmp = Path("/tmp/2news_multiline.md")
        tmp.write_text(
            "# 2026-09-02 新闻（已审核）\n\n"
            "## 【人民日报】一根玉米\n\n"
            "来源：人民日报  发布时间：2026-09-02\n\n"
            "正文：9月1日 晴\n"
            "中午采访完，我又去了趟安置点。\n"
            "在村口，村民达娃捞出一根玉米递过来。\n",
            encoding="utf-8",
        )
        d = step7.parse_2news(tmp, "2026-09-02")
        self.assertEqual(d["一根玉米"]["body"], "9月1日 晴\n中午采访完，我又去了趟安置点。\n在村口，村民达娃捞出一根玉米递过来。")
        tmp.unlink()

    def test_single_line_body_unchanged(self):
        tmp = Path("/tmp/2news_single.md")
        tmp.write_text(
            "# 2026-09-02 新闻（已审核）\n\n"
            "## 【新华社】智神星一号\n\n"
            "来源：新华社  发布时间：2026-09-02\n\n"
            "正文：记者从星河动力航天公司获悉，火箭首飞成功。\n",
            encoding="utf-8",
        )
        d = step7.parse_2news(tmp, "2026-09-02")
        self.assertEqual(d["智神星一号"]["body"], "记者从星河动力航天公司获悉，火箭首飞成功。")
        tmp.unlink()


class TestRejectFailureBody(unittest.TestCase):
    def test_run_rejects_placeholder_body(self):
        with \
            mock.patch("step7.parse_1news", return_value={"key": {"title": "测试", "category": "🚀 科技"}}), \
            mock.patch("step7.parse_2news", return_value={"key": {"title": "测试", "src": "新华社", "body": "[正文提取失败: SSL EOF]"}}):
            with self.assertRaises(SystemExit):
                import datetime
                step7.run(datetime.date(2026, 7, 5), dry_run=True)


class TestBlockedTermRewrite(unittest.TestCase):

    def test_rewrites_leader_attendance_without_blocked_terms(self):
        summary = step7.rewrite_blocked_terms(
            "国家主席将出席2026年7月17日至20日在上海举行的世界人工智能大会暨人工智能全球治理高级别会议开幕式并发表主旨讲话。"
        )
        self.assertNotIn("习近平", summary)
        self.assertNotIn("国家主席", summary)
        self.assertIn("最高规格", summary)
        self.assertIn("高度重视", summary)

    def test_summarize_article_worker_rejects_unknown_blocked_term_from_llm(self):
        with mock.patch("step7.llm_summarize", return_value="习近平出席重要会议"):
            with self.assertRaisesRegex(ValueError, "无法安全改写屏蔽词"):
                step7.summarize_article_worker(0, {"title": "t", "body": "b"})

    def test_summarize_article_worker_rejects_unknown_blocked_term_from_fallback(self):
        with mock.patch("step7.llm_summarize", return_value=None), \
             mock.patch("step7.fallback_summarize", return_value="习近平发表讲话"):
            with self.assertRaisesRegex(ValueError, "无法安全改写屏蔽词"):
                step7.summarize_article_worker(0, {"title": "t", "body": "b"})

    def test_run_skips_unknown_blocked_term_without_stopping_safe_articles(self):
        news1 = {
            "bad": {"title": "现代化道路研究", "category": "🤖 AI智能前沿"},
            "safe": {"title": "科学模型升级", "category": "🤖 AI智能前沿"},
        }
        news2 = {
            "bad": {"src": "人民日报", "body": "含屏蔽词的足够长正文"},
            "safe": {"src": "新华社", "body": "安全稿件的足够长正文"},
        }

        def summarize(title, body):
            return "习近平发表讲话" if title == "现代化道路研究" else "科学模型完成升级并服务科研。"

        with mock.patch("step7.parse_1news", return_value=news1), \
             mock.patch("step7.parse_2news", return_value=news2), \
             mock.patch("step7.llm_summarize", side_effect=summarize), \
             mock.patch("step4.find_duplicate_candidate_groups", return_value=[]):
            import contextlib
            import datetime
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 14), dry_run=True)

        output = buf.getvalue()
        self.assertNotIn("### [人民日报] 现代化道路研究", output)
        self.assertNotIn("习近平", output)
        self.assertIn("### [新华社] 科学模型升级", output)

    def test_run_skips_unsafe_title_without_stopping_safe_articles(self):
        news1 = {
            "bad": {
                "title": "坚持以习近平总书记关于国家粮食安全重要论述精神为指导",
                "category": "🌾 农业",
            },
            "safe": {"title": "粮食安全保障能力提升", "category": "🌾 农业"},
        }
        news2 = {
            "bad": {"src": "人民日报", "body": "不安全标题稿件的足够长正文"},
            "safe": {"src": "新华社", "body": "安全稿件的足够长正文"},
        }

        with mock.patch("step7.parse_1news", return_value=news1), \
             mock.patch("step7.parse_2news", return_value=news2), \
             mock.patch("step7.llm_summarize", return_value="粮食安全保障能力持续提升。"), \
             mock.patch("step4.find_duplicate_candidate_groups", return_value=[]):
            import contextlib
            import datetime
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 18), dry_run=True)

        output = buf.getvalue()
        self.assertNotIn("习近平", output)
        self.assertNotIn("### [人民日报]", output)
        self.assertIn("### [新华社] 粮食安全保障能力提升", output)

    def test_run_sanitizes_fallback_after_generic_worker_error(self):
        with mock.patch("step7.parse_1news", return_value={
                 "key": {"title": "普通标题", "category": "🚀 科技"}
             }), \
             mock.patch("step7.parse_2news", return_value={
                 "key": {"src": "人民日报", "body": "足够长的正文"}
             }), \
             mock.patch("step7.summarize_article_worker", side_effect=RuntimeError("worker failed")), \
             mock.patch("step7.fallback_summarize", return_value="习近平发表讲话"):
            import datetime
            with self.assertRaisesRegex(ValueError, "无法安全改写屏蔽词"):
                step7.run(datetime.date(2026, 7, 14), dry_run=True)

    def test_summarize_article_worker_no_xijinping(self):
        with mock.patch("step7.llm_summarize", return_value="今天天气不错"):
            _, summary, fallback = step7.summarize_article_worker(0, {"title": "t", "body": "b"})
            self.assertEqual(summary, "今天天气不错")


class TestOverviewSourceLabel(unittest.TestCase):

    def test_run_rewrites_blocked_terms_in_heading(self):
        with \
            mock.patch("step7.parse_1news", return_value={"key": {"title": "习近平将出席人工智能大会开幕式并讲话", "category": "🤖 AI智能前沿"}}), \
            mock.patch("step7.parse_2news", return_value={"key": {"title": "习近平将出席人工智能大会开幕式并讲话", "src": "人民日报", "body": "足够长的测试正文，用于生成新闻摘要并验证标题屏蔽词改写。"}}), \
            mock.patch("step7.llm_summarize", return_value="这场人工智能大会开幕式将以最高规格举行，体现出对相关议题的高度重视。"):
            import datetime, io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 14), dry_run=True)
            output = buf.getvalue()
            self.assertNotIn("习近平", output)
            self.assertNotIn("国家主席", output)

    def test_run_output_has_source_prefix(self):
        with \
            mock.patch("step7.parse_1news", return_value={"key": {"title": "测试", "category": "🚀 科技"}}), \
            mock.patch("step7.parse_2news", return_value={"key": {"title": "测试", "src": "新华社", "body": "正文"}}), \
            mock.patch("step7.llm_summarize", return_value="摘要"), \
            mock.patch("step7.BASE_DIR", Path("/tmp")):
            import datetime, io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 5), dry_run=True)
            self.assertIn("### [新华社] 测试", buf.getvalue())


class TestPreOverviewDuplicateGate(unittest.TestCase):

    def test_run_deduplicates_before_writing_overview(self):
        first = "新型钙钛矿-有机叠层太阳能电池光电转换效率刷新世界纪录"
        second = "超28%！钙钛矿-有机叠层太阳能电池效率破纪录"
        news1 = {
            "a": {"title": first, "category": "🔬 世界性科研突破"},
            "b": {"title": second, "category": "🔬 世界性科研突破"},
        }
        news2 = {
            "a": {"title": first, "src": "中科院", "body": "第一篇足够长的正文，用于验证重复新闻在摘要生成之前会被移除。"},
            "b": {"title": second, "src": "中科院", "body": "第二篇足够长的正文，用于验证不同网址标题报道同一科研成果。"},
        }
        review = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": 0, "reason": "同一项28.04%效率成果"}]
        }, ensure_ascii=False)

        with mock.patch("step7.parse_1news", return_value=news1), \
             mock.patch("step7.parse_2news", return_value=news2), \
             mock.patch("step7.llm_summarize", return_value="中国科研团队刷新了叠层太阳能电池效率世界纪录。"), \
             mock.patch("step4.call_llm", return_value=review), \
             mock.patch("step7.BASE_DIR", Path("/tmp")):
            import datetime, io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 14), dry_run=True)

        output = buf.getvalue()
        self.assertEqual(output.count("### [中科院]"), 1)

    def test_run_deduplicates_same_event_revealed_by_final_summaries(self):
        news1 = {
            "a": {
                "title": "2026世界人工智能大会开幕式将以最高规格举行",
                "category": "🤖 AI智能前沿",
            },
            "b": {
                "title": "总书记引领推动人工智能发展",
                "category": "🤖 AI智能前沿",
            },
        }
        news2 = {
            "a": {"src": "人民日报", "body": "大会正文甲"},
            "b": {"src": "新华社", "body": "大会正文乙"},
        }
        summaries = {
            "大会正文甲": "2026世界人工智能大会将于7月17日至20日在上海举行，将出席开幕式并发表主旨讲话。",
            "大会正文乙": "2026年世界人工智能大会将于7月17日至20日在上海举行，总书记将出席开幕式并发表主旨讲话。",
        }
        review = json.dumps({
            "duplicate_groups": [{"indices": [0, 1], "keep": 0, "reason": "同一大会开幕式事件"}]
        }, ensure_ascii=False)

        with mock.patch("step7.parse_1news", return_value=news1), \
             mock.patch("step7.parse_2news", return_value=news2), \
             mock.patch("step7.llm_summarize", side_effect=lambda title, body: summaries[body]), \
             mock.patch("step4.call_llm", return_value=review), \
             mock.patch("step7.BASE_DIR", Path("/tmp")):
            import datetime, io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                step7.run(datetime.date(2026, 7, 14), dry_run=True)

        output = buf.getvalue()
        self.assertEqual(output.count("### [人民日报]"), 1)
        self.assertNotIn("### [新华社] 总书记引领推动人工智能发展", output)


if __name__ == "__main__":
    unittest.main()
