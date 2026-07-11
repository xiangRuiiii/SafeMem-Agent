"""SafeMem 回归测试模块。"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from experiments.run_failure_matrix import build_matrix, classify_error
from safemem.agents.llm_agent import LLM_METHOD_GROUPS, policy_context_for_method
from safemem.data import load_episodes, read_jsonl
from safemem.models import AgentResult
from safemem.policy.matcher import policy_applies

ROOT = Path(__file__).resolve().parents[1]


class NextStageTest(unittest.TestCase):
    def test_mvp_plus_300_distribution(self) -> None:
        en = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_en.jsonl")
        zh = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_zh.jsonl")
        self.assertEqual(len(en), 300)
        self.assertEqual(len(zh), 300)
        self.assertEqual([episode.episode_id for episode in en], [episode.episode_id for episode in zh])
        self.assertEqual(
            Counter(episode.domain for episode in en),
            {"email": 50, "file": 50, "calendar": 50, "slack": 50, "database": 50, "browser": 50},
        )
        for domain in {episode.domain for episode in en}:
            items = [episode for episode in en if episode.domain == domain]
            self.assertEqual(
                Counter(episode.policy_carriage_state for episode in items),
                {
                    "policy_preserved": 10,
                    "policy_absent": 10,
                    "policy_weakened": 10,
                    "policy_misbound": 10,
                    "policy_over_included": 10,
                },
            )
        self.assertEqual(Counter(episode.is_safe_case for episode in en), {False: 180, True: 120})

    def test_mvp_plus_300_required_policies_in_clean_and_noisy_pool(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_en.jsonl")
        for episode in episodes:
            required = set(episode.required_policy_ids())
            clean_ids = {policy.policy_id for policy in episode.canonical_policy_registry}
            noisy_ids = {policy.policy_id for policy in episode.noisy_policy_pool}
            self.assertTrue(required <= clean_ids, episode.episode_id)
            self.assertTrue(required <= noisy_ids, episode.episode_id)

    def test_new_domain_required_policies_apply_to_risky_actions(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_en.jsonl")
        for episode in episodes:
            if episode.domain not in {"slack", "database", "browser"} or episode.is_safe_case:
                continue
            by_id = {policy.policy_id: policy for policy in episode.ground_truth_policies}
            for policy_id in episode.required_policy_ids():
                self.assertTrue(policy_applies(by_id[policy_id], episode.candidate_action), episode.episode_id)

    def test_msr_and_hybrid_ablation_methods_registered(self) -> None:
        expected = {
            "msr_tool_only_clean",
            "msr_tool_object_noisy",
            "msr_no_condition_clean",
            "msr_no_penalty_noisy",
            "msr_full_clean",
            "hybrid_recall_only_clean",
            "hybrid_filter_only_noisy",
            "hybrid_no_penalty_clean",
            "hybrid_full_noisy",
        }
        self.assertTrue(expected <= set(LLM_METHOD_GROUPS))

    def test_ablation_context_sources_are_stable(self) -> None:
        episode = next(
            item
            for item in load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_en.jsonl")
            if item.domain == "slack" and not item.is_safe_case
        )
        cases = {
            "msr_tool_only_clean": "canonical_policy_registry",
            "msr_full_noisy": "noisy_policy_pool",
            "hybrid_recall_only_clean": "canonical_policy_registry",
            "hybrid_full_noisy": "noisy_policy_pool",
        }
        for method, source in cases.items():
            context = policy_context_for_method(episode, method)
            self.assertEqual(context.source, source)
            self.assertLessEqual(len(context.policies), 5)

    def test_compression_sanity_schema(self) -> None:
        rows = read_jsonl(ROOT / "data" / "episodes" / "compression_sanity_en.jsonl")
        self.assertEqual(len(rows), 40)
        methods = Counter(row["compression_method"] for row in rows)
        self.assertEqual(set(methods.values()), {8})
        valid_states = {
            "policy_preserved",
            "policy_absent",
            "policy_weakened",
            "policy_misbound",
            "policy_over_included",
        }
        for row in rows:
            self.assertTrue(row["raw_long_context"])
            # episodes 文件是待运行输入模板；压缩产物与人工标签由独立输出文件在后续阶段补齐。
            self.assertIn("compressed_context", row)
            self.assertIsInstance(row["compressed_context"], list)
            self.assertIn("extracted_carried_policy", row)
            self.assertIsInstance(row["extracted_carried_policy"], list)
            self.assertIn(row["human_labeled_policy_state"], valid_states | {""})

    def test_failure_matrix_buckets(self) -> None:
        episode = next(
            item
            for item in load_episodes(ROOT / "data" / "episodes" / "mvp_plus_300_en.jsonl")
            if not item.is_safe_case and item.expected_decision == "block"
        )
        self.assertEqual(classify_error(episode, AgentResult(episode.episode_id, "fake", "allow")), "unsafe_allow")
        self.assertEqual(
            classify_error(episode, AgentResult(episode.episode_id, "fake", "ask_confirmation")),
            "under_blocked_confirmation",
        )
        rows = [
            AgentResult(episode.episode_id, "fake", "allow").to_dict(),
            AgentResult(episode.episode_id, "fake", "block").to_dict(),
        ]
        matrix = build_matrix({episode.episode_id: episode}, rows, ["agent", "policy_state"])
        self.assertEqual(matrix[0]["episodes"], 2)
        self.assertEqual(matrix[0]["unsafe_allow"], 1)
        self.assertEqual(matrix[0]["correct"], 1)


if __name__ == "__main__":
    unittest.main()
