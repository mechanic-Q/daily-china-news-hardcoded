import importlib.util
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parent.parent / "daily_china_news_full_to_feishu.py"


def load_module():
    if not SCRIPT.exists():
        raise AssertionError(f"缺少可版本化的飞书流水线脚本: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("daily_china_news_full_to_feishu", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestVideoIntegrity(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.date = "2026-07-18"
        self.video_dir = self.base / self.date / "video"
        self.video_dir.mkdir(parents=True)
        self.build_script = self.base / "build_full.py"
        self.build_script.write_text("", encoding="utf-8")
        self.sections = [("旁白一", "提示一", "科技"), ("旁白二", "提示二", "能源")]

    def _patch_build(self):
        return mock.patch.multiple(
            self.module,
            BASE_DIR=self.base,
            BUILD_FULL=self.build_script,
            ensure_intro_bg=mock.DEFAULT,
            run=mock.DEFAULT,
        )

    def _write_media(self):
        final = self.video_dir / f"每日新中国_{self.date}_GPT最终版.mp4"
        final.write_bytes(b"final")
        for index in range(1, 3):
            (self.video_dir / f"clip_{index:02d}.mp4").write_bytes(b"clip")
            (self.video_dir / f"audio_{index:02d}.mp3").write_bytes(b"audio")
        return final

    def test_rejects_missing_news_clip(self):
        final = self.video_dir / f"每日新中国_{self.date}_GPT最终版.mp4"
        final.write_bytes(b"final")
        with self._patch_build():
            with self.assertRaisesRegex(SystemExit, "missing clip_01.mp4"):
                self.module.build_video(self.date, self.sections)

    def test_rejects_missing_news_audio(self):
        self._write_media()
        (self.video_dir / "audio_02.mp3").unlink()
        with self._patch_build():
            with self.assertRaisesRegex(SystemExit, "missing audio_02.mp3"):
                self.module.build_video(self.date, self.sections)

    def test_rejects_short_final_video(self):
        self._write_media()
        probe = subprocess.CompletedProcess([], 0, json.dumps({"format": {"duration": "12.0"}}), "")
        with self._patch_build(), mock.patch.object(self.module.subprocess, "run", return_value=probe):
            with self.assertRaisesRegex(SystemExit, "Video too short"):
                self.module.build_video(self.date, self.sections)

    def test_accepts_complete_video(self):
        final = self._write_media()
        probe = subprocess.CompletedProcess([], 0, json.dumps({"format": {"duration": "60.0"}}), "")
        with self._patch_build(), mock.patch.object(self.module.subprocess, "run", return_value=probe):
            self.assertEqual(self.module.build_video(self.date, self.sections), final)


class TestFeishuConfig(unittest.TestCase):
    def test_requires_daily_news_chat_id(self):
        module = load_module()
        with self.assertRaisesRegex(SystemExit, "FEISHU_DAILY_NEWS_CHAT_ID"):
            module.feishu_chat_id({})

    def test_returns_configured_daily_news_chat_id(self):
        module = load_module()
        self.assertEqual(
            module.feishu_chat_id({"FEISHU_DAILY_NEWS_CHAT_ID": "oc_test"}),
            "oc_test",
        )


class TestSensitiveCommandLogging(unittest.TestCase):
    def test_sensitive_command_hides_command_and_response(self):
        module = load_module()
        result = subprocess.CompletedProcess(
            [], 0, '{"tenant_access_token":"secret-response"}', "secret-stderr"
        )
        output = io.StringIO()
        with mock.patch.object(module.subprocess, "run", return_value=result), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            module.run(["curl", "-d", "app_secret=secret-request"], sensitive=True)

        logged = output.getvalue()
        self.assertIn("[sensitive arguments redacted]", logged)
        self.assertNotIn("secret-request", logged)
        self.assertNotIn("secret-response", logged)
        self.assertNotIn("secret-stderr", logged)

    def test_sensitive_command_failure_hides_command(self):
        module = load_module()
        result = subprocess.CompletedProcess([], 1, "", "secret-stderr")
        with mock.patch.object(module.subprocess, "run", return_value=result):
            with self.assertRaises(SystemExit) as caught:
                module.run(["curl", "-d", "app_secret=secret-request"], sensitive=True)

        self.assertNotIn("secret-request", str(caught.exception))
        self.assertNotIn("secret-stderr", str(caught.exception))

    def test_non_json_feishu_response_is_not_echoed(self):
        module = load_module()
        result = subprocess.CompletedProcess([], 0, "secret-response", "")
        with mock.patch.object(module, "run", return_value=result):
            with self.assertRaises(SystemExit) as caught:
                module.curl_json(["curl"], 1)

        self.assertNotIn("secret-response", str(caught.exception))

    def test_feishu_error_json_is_not_echoed(self):
        module = load_module()
        with mock.patch.object(
            module, "curl_json", return_value={"code": 1, "msg": "secret-response"}
        ):
            with self.assertRaises(SystemExit) as caught:
                module.send_text("token", "oc_test", "text")

        self.assertIn("code=1", str(caught.exception))
        self.assertNotIn("secret-response", str(caught.exception))


class TestFailureAlert(unittest.TestCase):
    def test_alert_failure_does_not_mask_original_system_exit(self):
        module = load_module()
        with mock.patch.object(module, "main", side_effect=SystemExit("原始失败")), \
             mock.patch.object(module, "load_env", return_value={}), \
             mock.patch.object(module, "feishu_token", side_effect=SystemExit("告警失败")):
            with self.assertRaisesRegex(SystemExit, "原始失败"):
                module.main_with_alert()

    def test_unexpected_exception_sends_alert_and_is_reraised(self):
        module = load_module()
        with mock.patch.object(module, "main", side_effect=RuntimeError("意外失败")), \
             mock.patch.object(module, "load_env", return_value={"FEISHU_DAILY_NEWS_CHAT_ID": "oc_test"}), \
             mock.patch.object(module, "feishu_token", return_value="token"), \
             mock.patch.object(module, "send_text") as send:
            with self.assertRaisesRegex(RuntimeError, "意外失败"):
                module.main_with_alert()

        self.assertIn("意外失败", send.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
