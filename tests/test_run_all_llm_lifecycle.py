"""run_all.sh LLM 服务生命周期跟随 llm.yaml provider 的静态测试（issue #58 T3）。

run_all.sh 是 bash 编排脚本，无 Python 可导入面；本测试以文本断言锁定关键行为，
防止 provider 切换后端口硬编码漂移（8899 旧栈 → kvmem 27182）。
"""

import unittest
from pathlib import Path


RUN_ALL = Path(__file__).resolve().parent.parent / "run_all.sh"


class TestRunAllLlmLifecycle(unittest.TestCase):
    def setUp(self):
        self.source = RUN_ALL.read_text(encoding="utf-8")

    def test_llm_port_not_hardcoded_to_old_backend(self):
        # 旧栈 8899 不得再作为默认端口硬编码；端口必须从 llm.yaml base_url 解析
        self.assertNotIn("LLM_SERVER_PORT=8899", self.source)
        self.assertIn("llm.yaml", self.source)

    def test_parses_provider_from_llm_yaml(self):
        # 必须读 provider 字段决定生命周期：本地 provider 才管启停，云 provider 跳过
        self.assertIn("provider", self.source)
        self.assertIn("base_url", self.source)
        self.assertIn("local", self.source.lower())

    def test_kvmem_start_mode_passed_to_start_llm(self):
        # kvmem provider 走 start-llm.sh kvmem 分支
        self.assertIn("start-llm.sh", self.source)
        self.assertIn("kvmem", self.source)

    def test_memory_mutex_check_covers_known_ports(self):
        # 16G 卡互斥清单：本地 provider 启动前须检查其它本地 LLM 端口占用
        for port in ("8888", "8899", "18200", "18201"):
            self.assertIn(port, self.source)

    def test_reused_instance_is_not_killed_on_exit(self):
        # 所有权语义：端口已在线实例 → 复用但退出不杀（2026-09-24 误杀生产实例教训）
        self.assertIn("复用，退出时不关闭", self.source)
        self.assertIn("LLM_PID=\"\"", self.source)

    def test_foreign_port_conflict_refuses_to_start(self):
        # 互斥端口被占 → 拒绝启动报错，绝不替用户杀进程
        self.assertIn("16G 显存互斥", self.source)

    def test_stop_lifecycle_still_present(self):
        # 用完必关的契约不变（仅针对自家启动实例）
        self.assertIn("stop_llm_server", self.source)
        self.assertIn("trap", self.source)


if __name__ == "__main__":
    unittest.main()
