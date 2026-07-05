import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import step7


class TestXijinpingRemoval(unittest.TestCase):

    def test_summarize_article_worker_removes_xijinping_llm(self):
        with mock.patch("step7.llm_summarize", return_value="习近平出席重要会议"):
            _, summary, fallback = step7.summarize_article_worker(0, {"title": "t", "body": "b"})
            self.assertNotIn("习近平", summary)
            self.assertEqual(summary, "出席重要会议")

    def test_summarize_article_worker_removes_xijinping_fallback(self):
        with mock.patch("step7.llm_summarize", return_value=None):
            with mock.patch("step7.fallback_summarize", return_value="习近平发表讲话"):
                _, summary, fallback = step7.summarize_article_worker(0, {"title": "t", "body": "b"})
                self.assertNotIn("习近平", summary)
                self.assertTrue(fallback)

    def test_summarize_article_worker_no_xijinping(self):
        with mock.patch("step7.llm_summarize", return_value="今天天气不错"):
            _, summary, fallback = step7.summarize_article_worker(0, {"title": "t", "body": "b"})
            self.assertEqual(summary, "今天天气不错")


if __name__ == "__main__":
    unittest.main()
