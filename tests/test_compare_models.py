"""验证多模型结果的网格一致性、汇总指标与配对 bootstrap 差值。"""

from __future__ import annotations

import unittest

from experiments.compare_models import build_paired_deltas, build_summary, validate_grids


def result(profile: str, episode_id: str, agent: str, *, correct: bool, violation: bool = False) -> dict:
    return {
        "model_profile": profile,
        "episode_id": episode_id,
        "agent": agent,
        "agent_group": "test",
        "decision": "allow",
        "correct": correct,
        "violation": violation,
        "false_refusal": False,
        "task_success": correct and not violation,
        "policy_token_cost": 10,
        "llm_total_tokens": 100,
        "llm_model": f"{profile}-model",
    }


class CompareModelsTest(unittest.TestCase):
    """只有完全配对的多模型结果才能进入跨模型统计。"""

    def test_summary_and_paired_delta(self) -> None:
        groups = {
            "model_a": [
                result("model_a", "e1", "llm_msr_noisy", correct=True),
                result("model_a", "e2", "llm_msr_noisy", correct=False, violation=True),
                result("model_a", "e1", "llm_vmsr_text_guard_noisy", correct=True),
                result("model_a", "e2", "llm_vmsr_text_guard_noisy", correct=True),
            ],
            "model_b": [
                result("model_b", "e1", "llm_msr_noisy", correct=False, violation=True),
                result("model_b", "e2", "llm_msr_noisy", correct=True),
                result("model_b", "e1", "llm_vmsr_text_guard_noisy", correct=True),
                result("model_b", "e2", "llm_vmsr_text_guard_noisy", correct=True),
            ],
        }
        methods = ["llm_msr_noisy", "llm_vmsr_text_guard_noisy"]
        validate_grids(groups, methods, expected_episodes=2)
        summary = build_summary(groups, methods)
        vmsr_a = next(row for row in summary if row["model_profile"] == "model_a" and row["agent"] == methods[1])
        self.assertEqual(vmsr_a["accuracy"], 1.0)

        deltas = build_paired_deltas(groups, methods, methods[0], bootstrap_samples=20, seed=7)
        delta_a = next(row for row in deltas if row["model_profile"] == "model_a")
        self.assertEqual(delta_a["accuracy_delta"], 0.5)
        self.assertEqual(delta_a["executed_violation_rate_delta"], -0.5)

    def test_mismatched_episode_grid_is_rejected(self) -> None:
        groups = {
            "model_a": [
                result("model_a", "e1", "llm_msr_noisy", correct=True),
                result("model_a", "e2", "llm_vmsr_text_guard_noisy", correct=True),
            ]
        }
        with self.assertRaisesRegex(RuntimeError, "different episode sets"):
            validate_grids(groups, ["llm_msr_noisy", "llm_vmsr_text_guard_noisy"], expected_episodes=0)


if __name__ == "__main__":
    unittest.main()
