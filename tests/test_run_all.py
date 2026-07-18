import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRunAllInterpreter(unittest.TestCase):
    def test_missing_project_venv_has_actionable_error(self):
        source = Path(__file__).resolve().parent.parent / "run_all.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_all.sh").write_bytes(source.read_bytes())

            result = subprocess.run(
                ["bash", str(root / "run_all.sh"), "--date", "2026-07-18"],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("项目虚拟环境不存在", result.stderr)
            self.assertIn("python3 -m venv .venv", result.stderr)

    def test_uses_project_venv_python_for_every_step(self):
        source = Path(__file__).resolve().parent.parent / "run_all.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_all.sh").write_bytes(source.read_bytes())
            python = root / ".venv" / "bin" / "python3"
            python.parent.mkdir(parents=True)
            python.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$(dirname \"$0\")/../../calls.log\"\n",
                encoding="utf-8",
            )
            python.chmod(0o755)
            for step in ("step1_3.py", "step4.py", "step6.py", "step7.py", "step8.py"):
                (root / step).write_text("", encoding="utf-8")

            result = subprocess.run(
                ["bash", str(root / "run_all.sh"), "--date", "2026-07-18", "--dry-run"],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls_path = root / "calls.log"
            self.assertTrue(calls_path.exists(), "run_all.sh did not use the project venv interpreter")
            calls = calls_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 5)
            self.assertTrue(all("--date 2026-07-18 --dry-run" in call for call in calls))


if __name__ == "__main__":
    unittest.main()