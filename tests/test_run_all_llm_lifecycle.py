"""run_all.sh LLM 服务生命周期跟随 llm.yaml provider 的静态测试（issue #62 重写）。

run_all.sh 是 bash 编排脚本，无 Python 可导入面；本测试以文本断言锁定关键行为：
strata provider 启停、nvidia-smi 显存互斥、复用不杀所有权语义、taskkill 树杀。
历史: 2026-09-24 起锁定 kvmem 27182 + ss 端口清单（issue #58 T3）；
2026-10-12 随 Windows 原生化重写（ADR-0005）。
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

    def test_strata_start_script_invoked(self):
        # strata provider 走 start-llm.sh 启动
        self.assertIn("start-llm.sh", self.source)

    def test_vram_mutex_check_replaces_port_list(self):
        # 16G 卡互斥改为 nvidia-smi 显存阈值（WSL 侧 CUDA 负载同样可见, ADR-0005）；
        # 旧互斥端口清单不得残留
        self.assertIn("nvidia-smi", self.source)
        self.assertIn("显存互斥", self.source)
        self.assertNotIn("18201", self.source)

    def test_reused_instance_is_not_killed_on_exit(self):
        # 所有权语义：端口已在线实例 → 复用但退出不杀（2026-09-24 误杀生产实例教训）
        self.assertIn("复用，退出时不关闭", self.source)
        # 机制断言：复用分支显式清空 LLM_OWNED（注释尾随, 区别于顶部初始化行）
        self.assertIn('LLM_OWNED=""   # 非自家启动, 退出时不杀', self.source)

    def test_stop_kills_by_port_read_windows_pid(self):
        # $! 是 MSYS 伪 pid, taskkill 不认 —— 必须按端口回读真实 Windows pid 再树杀
        self.assertIn('srv=$(port_pid)', self.source)
        self.assertIn('taskkill //PID "$srv" //T //F', self.source)
        self.assertNotIn('LLM_PID', self.source)

    def test_stop_uses_taskkill_tree_kill(self):
        # server.py 被硬杀无优雅卸载路径, 必须 //T 树杀 engine 子进程, 否则显存残留
        self.assertIn("taskkill //PID", self.source)
        self.assertIn("//T //F", self.source)

    def test_stop_verifies_vram_released(self):
        # 树杀后核对显存回落, engine 残留要告警
        self.assertIn("GPU 仍占用", self.source)

    def test_foreign_gpu_conflict_refuses_to_start(self):
        # 互斥: GPU 被其它负载占用 → 拒绝启动报错，绝不替用户杀
        self.assertIn("16G 显存互斥", self.source)

    def test_occupied_port_without_health_fails_closed(self):
        # 端口被占但健康未过 → 报错退出（可能是用户正在手动启动）, 不代杀
        self.assertIn("但服务未就绪", self.source)

    def test_stop_lifecycle_still_present(self):
        # 用完必关的契约不变（仅针对自家启动实例）
        self.assertIn("stop_llm_server", self.source)
        self.assertIn("trap", self.source)

    def test_windows_venv_layout(self):
        # Windows venv 布局: .venv/Scripts/python.exe（WSL 时代 .venv/bin/python3 退役）
        self.assertIn(".venv/Scripts/python.exe", self.source)
        self.assertNotIn(".venv/bin/python3", self.source)


if __name__ == "__main__":
    unittest.main()
