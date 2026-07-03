# tests/test_llm_client.py
# author: lmr
# created_at: 2026-07-03

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import call_llm, LLMCallError
from daily_logging import setup_logging


class TestLLMErrorHandling(unittest.TestCase):

    def test_llm_failure_raises_llm_call_error(self):
        with mock.patch('llm_client.get_client', side_effect=Exception("generic error")):
            with self.assertRaises(LLMCallError):
                call_llm("test-site", [{"role": "user", "content": "test"}])

    def test_llm_error_message_no_exception_details(self):
        with mock.patch('llm_client.get_client', side_effect=Exception("connection refused")):
            with self.assertRaises(LLMCallError) as ctx:
                call_llm("test-site", [{"role": "user", "content": "test"}])
            self.assertNotIn("connection refused", str(ctx.exception))

    def test_llm_failure_redacts_api_key_from_log(self):
        fake_key = "sk-fake-key-abc123"

        class MockAPIError(Exception):
            def __init__(self):
                super().__init__(f"Invalid API key: {fake_key}")
                self.status_code = 401

        with mock.patch('llm_client.get_client', side_effect=MockAPIError()):
            with self.assertRaises(LLMCallError) as ctx:
                call_llm("test-site", [{"role": "user", "content": "test"}])
            self.assertNotIn(fake_key, str(ctx.exception))

        with mock.patch('llm_client._logger') as mock_logger:
            with mock.patch('llm_client.get_client', side_effect=MockAPIError()):
                with self.assertRaises(LLMCallError):
                    call_llm("test-site", [{"role": "user", "content": "test"}])
            for call_args, call_kwargs in mock_logger.error.call_args_list:
                for arg in call_args:
                    if isinstance(arg, str):
                        self.assertNotIn(fake_key, arg)
                for arg in call_kwargs.values():
                    if isinstance(arg, str):
                        self.assertNotIn(fake_key, arg)


if __name__ == "__main__":
    unittest.main()
