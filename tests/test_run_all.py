import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


def _find_bash() -> str:
    """定位可用于 subprocess 的 Git Bash。

    subprocess('bash') 的 CreateProcess 搜索 System32 先于 PATH, 会命中 WSL launcher
    (System32\\bash.exe, 认不得 C:/ 与 /c/ 路径); 本项目运行环境假定 Git Bash 存在。
    """
    exe = shutil.which("bash")
    if not exe or "system32" in exe.lower():
        git_bash = Path(r"C:\Program Files\Git\usr\bin\bash.exe")
        if git_bash.exists():
            return str(git_bash)
    return exe or "bash"


BASH = _find_bash()


class TestRunAllInterpreter(unittest.TestCase):
    def test_missing_project_venv_has_actionable_error(self):
        source = Path(__file__).resolve().parent.parent / "run_all.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_all.sh").write_bytes(source.read_bytes())

            result = subprocess.run(
                [BASH, (root / "run_all.sh").as_posix()],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("项目虚拟环境不存在", result.stderr)
            self.assertIn("py -3 -m venv .venv", result.stderr)

    def test_uses_project_venv_python_for_every_step(self):
        source = Path(__file__).resolve().parent.parent / "run_all.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_all.sh").write_bytes(source.read_bytes())
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            # Windows venv 布局 .venv/Scripts/python.exe。fake 解释器:
            # 首参 "-" (llm.yaml 解析 heredoc) 静默不记账 → 只有 5 个 step 调用入 calls.log
            python.write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "$1" != "-" ]]; then printf \'%s\\n\' "$*" >> "$(dirname "$0")/../../calls.log"; fi\n',
                encoding="utf-8",
            )
            python.chmod(0o755)
            for step in ("step1_3.py", "step4.py", "step6.py", "step7.py", "step8.py"):
                (root / step).write_text("", encoding="utf-8")
            # 保险: 即便 llm.yaml 被真实解析, 9999 端口也无服务在线 → 走"跳过启动"分支,
            # 沙箱结果不依赖宿主机真实 LLM 实例状态
            sandbox_yaml = (Path(__file__).resolve().parent.parent / "llm.yaml").read_text(
                encoding="utf-8")
            sandbox_yaml = sandbox_yaml.replace("127.0.0.1:8080", "127.0.0.1:9999")
            (root / "llm.yaml").write_text(sandbox_yaml, encoding="utf-8")

            result = subprocess.run(
                [BASH, (root / "run_all.sh").as_posix(), "--date", "2026-07-18", "--dry-run"],
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
