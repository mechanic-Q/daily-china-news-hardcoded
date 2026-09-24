"""bench_kvmem_degrade.py 单测：KVMEM_CHAT_TURN 日志解析 + 劣化判定（issue #58 T4）。

~30 轮劣化红线（KVMem 启动指南红线#1）：rc1 实例连续 ~30 轮请求后解码从
50-86 t/s 劣化到 4 t/s（长上下文 H3 场景实测）。判定阈值: 连续 3 轮 < 30 t/s。
"""

import unittest

from bench_kvmem_degrade import (
    DETERIORATE_CONSECUTIVE,
    DETERIORATE_TPS,
    judge_deterioration,
    parse_chat_turns,
    valid_probe_turns,
)


SAMPLE_LOG = """\
2026-09-24 03:00:01 info: server listening on http://127.0.0.1:27182
KVMEM_CHAT_TURN n_prompt=23 n_gen=256 prefill_ms=683.40 gen_ms=2561.03 wall_ms=3244.42 gen_toks=99.96
KVMEM_CHAT_TURN n_prompt=171 n_gen=128 prefill_ms=608.83 gen_ms=1306.73 wall_ms=1915.55 gen_toks=97.95
KVMEM_CHAT_TURN n_prompt=71 n_gen=1 prefill_ms=496.85 gen_ms=43.42 wall_ms=540.27 gen_toks=23.03
KVMEM_GEN_WALL n=128 ms=1291.12 toks=99.14
"""


class TestParseChatTurns(unittest.TestCase):
    def test_parses_turn_fields_in_order(self):
        turns = parse_chat_turns(SAMPLE_LOG)
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[0]["seq"], 1)
        self.assertEqual(turns[0]["n_prompt"], 23)
        self.assertEqual(turns[0]["n_gen"], 256)
        self.assertAlmostEqual(turns[0]["tps"], 99.96, places=2)
        self.assertEqual(turns[2]["seq"], 3)
        self.assertAlmostEqual(turns[2]["tps"], 23.03, places=2)

    def test_ignores_non_chat_lines(self):
        turns = parse_chat_turns("KVMEM_GEN_WALL n=128 ms=1 toks=1\n garbage\n")
        self.assertEqual(turns, [])

    def test_empty_log(self):
        self.assertEqual(parse_chat_turns(""), [])


class TestValidProbeTurns(unittest.TestCase):
    def test_filters_single_token_artifacts(self):
        turns = parse_chat_turns(SAMPLE_LOG)
        valid = valid_probe_turns(turns)
        # n_gen=1 的短调用 (23 t/s) 是 MTP 固定开销伪影, 不入曲线
        self.assertEqual(len(valid), 2)
        self.assertTrue(all(t["n_gen"] >= 8 for t in valid))


class TestJudgeDeterioration(unittest.TestCase):
    def test_healthy_curve_passes(self):
        turns = [{"seq": i, "n_gen": 128, "tps": 90.0 - i * 0.1}
                 for i in range(1, 31)]
        verdict = judge_deterioration(turns)
        self.assertFalse(verdict["deteriorated"])
        self.assertEqual(verdict["min_tps"], 87.0)
        self.assertEqual(verdict["n_valid"], 30)

    def test_thirty_turn_cliff_detected(self):
        # 前 28 轮 85-90 t/s, 第 29/30/31 轮坠到 4-6 t/s → 连续 3 轮 < 30
        tps_list = [88.0] * 28 + [5.0, 4.2, 6.1]
        turns = [{"seq": i, "n_gen": 128, "tps": t}
                 for i, t in enumerate(tps_list, 1)]
        verdict = judge_deterioration(turns)
        self.assertTrue(verdict["deteriorated"])
        self.assertEqual(verdict["first_bad_seq"], 29)
        self.assertAlmostEqual(verdict["min_tps"], 4.2, places=1)

    def test_isolated_slow_call_not_deterioration(self):
        # 单轮慢调用 (受系统抖动影响) 不触发: 连续 <3 轮
        tps_list = [88.0] * 10 + [25.0] + [88.0] * 5
        turns = [{"seq": i, "n_gen": 128, "tps": t}
                 for i, t in enumerate(tps_list, 1)]
        verdict = judge_deterioration(turns)
        self.assertFalse(verdict["deteriorated"])

    def test_single_token_turns_excluded_from_judgement(self):
        # n_gen=1 伪影即使 tps=23 也不参与判定
        turns = [{"seq": 1, "n_gen": 1, "tps": 23.0},
                 {"seq": 2, "n_gen": 128, "tps": 90.0}]
        verdict = judge_deterioration(turns)
        self.assertFalse(verdict["deteriorated"])
        self.assertEqual(verdict["n_valid"], 1)

    def test_insufficient_data(self):
        turns = [{"seq": 1, "n_gen": 128, "tps": 90.0}]
        verdict = judge_deterioration(turns, min_turns=30)
        self.assertFalse(verdict["deteriorated"])
        self.assertTrue(verdict["insufficient"])


if __name__ == "__main__":
    unittest.main()
