import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import step8


class _FakeCompleted:
    def __init__(self, rc=0, stderr=""):
        self.returncode = rc
        self.stdout = ""
        self.stderr = stderr


def _write_png(path, w=200, h=200):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (w, h), step8.BODY_BG)
    ImageDraw.Draw(img).rectangle([10, 10, w - 10, h // 2], fill=(20, 20, 20))
    img.save(path)


class LateWriteChrome:
    """模拟 chrome：进程立刻退出，--screenshot 指定的文件在 delay 秒之后才落盘。

    这是 2026-10-19 实录的形态：step8 在 subprocess.run 返回瞬间查 exists()，
    查不到就打「截图未生成」并放弃；而真正的写盘发生在约 4s 之后，
    4320x20000 的未裁剪原图仍然留在了产物路径上，被下游当成报纸图。
    """

    def __init__(self, delay=1.0, write=True):
        self.delay = delay
        self.write = write
        self.calls = 0

    def __call__(self, cmd, *a, **kw):
        self.calls += 1
        target = Path([c for c in cmd if c.startswith("--screenshot=")][0].split("=", 1)[1])
        if self.write:
            threading.Thread(target=self._later, args=(target,), daemon=True).start()
        return _FakeCompleted()

    def _later(self, target):
        time.sleep(self.delay)
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_png(target)


class TestScreenshotLateWrite(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.html = self.dir / "paper.html"
        self.html.write_text("<html><body>paper</body></html>", encoding="utf-8")
        self.png = self.dir / "paper.png"

    def tearDown(self):
        self._tmp.cleanup()

    def test_waits_for_file_written_after_process_exit(self):
        """文件在进程退出后 1s 才落盘：必须等待并裁剪，不得判失败。"""
        fake = LateWriteChrome(delay=1.0)
        with mock.patch.object(step8.subprocess, "run", fake), \
             mock.patch.object(step8, "SCREENSHOT_WAIT_SECONDS", 10.0, create=True):
            ok = step8.screenshot_and_crop(self.html, self.png)

        self.assertTrue(ok, "chromium 退出后文件才落盘，应等待落盘而不是判「截图未生成」")
        self.assertTrue(self.png.exists(), "产物必须留在目标路径")
        self.assertEqual(fake.calls, 1, "首次尝试等到文件后不应再重试")
        from PIL import Image
        with Image.open(self.png) as im:
            got = im.size
        self.assertLess(
            got[1], 200,
            "迟到落盘的图同样必须裁剪；未裁剪的大图不得作为产物",
        )

    def test_failure_leaves_no_bogus_artifact(self):
        """chromium 始终不产文件：返回 False，且产物路径不得留下半成品。"""
        fake = LateWriteChrome(write=False)
        with mock.patch.object(step8.subprocess, "run", fake), \
             mock.patch.object(step8, "SCREENSHOT_WAIT_SECONDS", 0.4, create=True):
            ok = step8.screenshot_and_crop(self.html, self.png)

        self.assertFalse(ok)
        self.assertFalse(self.png.exists(), "失败时不能把未裁剪/半成品留在下游会读的路径上")

    def test_uncropped_full_window_is_flagged(self):
        """裁剪没生效（图仍是整窗高度）时不得静默当成成功产物。"""
        raw_h = step8.SCREENSHOT_HEIGHT * step8.SCREENSHOT_SCALE

        def fake_run(cmd, *a, **kw):
            target = Path([c for c in cmd if c.startswith("--screenshot=")][0].split("=", 1)[1])
            from PIL import Image
            Image.new("RGB", (80, raw_h), step8.BODY_BG).save(target)
            return _FakeCompleted()

        with mock.patch.object(step8.subprocess, "run", fake_run):
            ok = step8.screenshot_and_crop(self.html, self.png)
        self.assertFalse(ok, "整窗高度说明内容包围盒就是整图，裁剪失效，不能报成功")


if __name__ == "__main__":
    unittest.main(verbosity=2)
