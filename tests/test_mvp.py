"""SafeMem 回归测试模块。"""

from __future__ import annotations

import copy
import unittest
from collections import Counter
from pathlib import Path

from safemem.agents.baselines import (
    AllPolicyCleanAgent,
    AllPolicyNoisyAgent,
    CarriedPolicyAgent,
    OracleMinimalAgent,
)
from safemem.agents.msr_agent import MsrAgent, MsrNoisyAgent
from safemem.data import load_episodes
from safemem.eval.judge import judge_result

ROOT = Path(__file__).resolve().parents[1]


class MvpTest(unittest.TestCase):
    def test_sample_data_loads(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "sample.jsonl")
        self.assertGreaterEqual(len(episodes), 6)

    def test_msr_finds_email_policy(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "sample.jsonl")
        episode = next(item for item in episodes if item.episode_id == "email_contract_preserved_001")
        result = judge_result(episode, MsrAgent().decide(episode))
        self.assertEqual(result.decision, "ask_confirmation")
        self.assertIn("p_email_contract_confirm", result.policy_ids)
        self.assertFalse(result.violation)

    def test_bilingual_mvp_pairs_align(self) -> None:
        en = load_episodes(ROOT / "data" / "episodes" / "mvp_en.jsonl")
        zh = load_episodes(ROOT / "data" / "episodes" / "mvp_zh.jsonl")
        self.assertEqual(len(en), 30)
        self.assertEqual(len(zh), 30)
        self.assertEqual([item.episode_id for item in en], [item.episode_id for item in zh])
        self.assertEqual(Counter(item.domain for item in en), {"email": 10, "file": 10, "calendar": 10})
        self.assertEqual(
            Counter(item.policy_carriage_state for item in en),
            {
                "policy_preserved": 6,
                "policy_absent": 6,
                "policy_weakened": 6,
                "policy_misbound": 6,
                "policy_over_included": 6,
            },
        )

    def test_all_policy_clean_context_covers_required_policies(self) -> None:
        paths = [
            ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl",
            ROOT / "data" / "episodes" / "mvp_plus_90_zh.jsonl",
        ]
        for path in paths:
            for episode in load_episodes(path):
                required_ids = set(episode.required_policy_ids())
                if not required_ids:
                    continue
                result = judge_result(episode, AllPolicyCleanAgent().decide(episode))
                canonical_ids = {policy.policy_id for policy in episode.canonical_policy_registry}
                self.assertTrue(required_ids <= canonical_ids, episode.episode_id)
                self.assertTrue(required_ids <= set(result.context_policy_ids), episode.episode_id)
                self.assertEqual(result.policy_coverage, 1.0, episode.episode_id)
                self.assertEqual(result.policy_source_used, "canonical_policy_registry")

    def test_all_policy_noisy_context_covers_required_policies(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        for episode in episodes:
            required_ids = set(episode.required_policy_ids())
            if not required_ids:
                continue
            result = judge_result(episode, AllPolicyNoisyAgent().decide(episode))
            noisy_ids = {policy.policy_id for policy in episode.noisy_policy_pool}
            self.assertTrue(required_ids <= noisy_ids, episode.episode_id)
            self.assertTrue(required_ids <= set(result.context_policy_ids), episode.episode_id)
            self.assertEqual(result.policy_coverage, 1.0, episode.episode_id)
            self.assertEqual(result.policy_source_used, "noisy_policy_pool")

    def test_carried_policy_agent_uses_carried_policy_only(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        self.assertTrue(any(len(ep.noisy_policy_pool) != len(ep.carried_policy) for ep in episodes))
        for episode in episodes:
            result = judge_result(episode, CarriedPolicyAgent().decide(episode))
            carried_ids = {policy.policy_id for policy in episode.carried_policy}
            self.assertEqual(set(result.context_policy_ids), carried_ids, episode.episode_id)
            self.assertFalse(set(episode.irrelevant_policy_ids) & carried_ids, episode.episode_id)
            self.assertEqual(result.policy_source_used, "carried_policy")

    def test_all_policy_clean_and_carried_policy_are_distinct(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        episode = next(
            ep for ep in episodes
            if ep.policy_carriage_state == "policy_absent" and ep.required_policy_ids()
        )
        all_policy = judge_result(episode, AllPolicyCleanAgent().decide(episode))
        carried = judge_result(episode, CarriedPolicyAgent().decide(episode))
        self.assertNotEqual(all_policy.context_policy_ids, carried.context_policy_ids, episode.episode_id)
        self.assertEqual(all_policy.policy_coverage, 1.0, episode.episode_id)
        self.assertEqual(carried.policy_coverage, 0.0, episode.episode_id)
        self.assertGreater(all_policy.policy_token_cost, carried.policy_token_cost, episode.episode_id)

    def test_mvp_plus_template_schema(self) -> None:
        paths = [
            ROOT / "data" / "episodes" / "mvp_plus_template_en.jsonl",
            ROOT / "data" / "episodes" / "mvp_plus_template_zh.jsonl",
        ]
        for path in paths:
            episodes = load_episodes(path)
            self.assertEqual(len(episodes), 2)
            self.assertEqual([episode.policy_pool_size for episode in episodes], [26, 24])
            self.assertEqual(len(episodes[0].required_policy_ids()), 3)
            self.assertEqual(episodes[0].is_safe_case, False)
            self.assertEqual(episodes[1].required_policy_ids(), [])
            self.assertEqual(episodes[1].is_safe_case, True)

    def test_msr_template_policy_metrics(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_template_en.jsonl")
        risky = episodes[0]
        result = judge_result(risky, MsrAgent().decide(risky))
        self.assertGreaterEqual(result.policy_coverage, 0.66)
        self.assertLess(result.retrieved_policy_count, risky.policy_pool_size)

        safe = episodes[1]
        safe_result = judge_result(safe, MsrAgent().decide(safe))
        self.assertIsNone(safe_result.policy_coverage)

    def test_mvp_plus_90_distribution(self) -> None:
        en = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        zh = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_zh.jsonl")
        self.assertEqual(len(en), 90)
        self.assertEqual(len(zh), 90)
        self.assertEqual([episode.episode_id for episode in en], [episode.episode_id for episode in zh])
        self.assertEqual(Counter(episode.domain for episode in en), {"email": 30, "file": 30, "calendar": 30})
        self.assertEqual(
            Counter(episode.policy_carriage_state for episode in en),
            {
                "policy_preserved": 18,
                "policy_absent": 18,
                "policy_weakened": 18,
                "policy_misbound": 18,
                "policy_over_included": 18,
            },
        )
        self.assertEqual(Counter(episode.is_safe_case for episode in en), {False: 54, True: 36})
        self.assertTrue(all(episode.policy_pool_size >= 30 for episode in en))

    def test_canonical_registry_keeps_original_policy_text(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        for episode in episodes:
            self.assertTrue(episode.canonical_policy_registry, episode.episode_id)
            self.assertTrue(all(policy.text for policy in episode.canonical_policy_registry), episode.episode_id)
            self.assertTrue(all(policy.text for policy in episode.ground_truth_policies), episode.episode_id)

    def test_required_policies_remain_in_clean_and_noisy_pools(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        for episode in episodes:
            required_ids = set(episode.required_policy_ids())
            noisy_ids = {policy.policy_id for policy in episode.noisy_policy_pool}
            canonical_ids = {policy.policy_id for policy in episode.canonical_policy_registry}
            self.assertTrue(required_ids <= canonical_ids, episode.episode_id)
            self.assertTrue(required_ids <= noisy_ids, episode.episode_id)
            self.assertFalse(required_ids & set(episode.corrupted_policy_ids), episode.episode_id)

    def test_private_roadmap_actions_mark_confidential_sensitivity(self) -> None:
        target_ids = {
            "file_008_absent_share_private_roadmap",
            "file_015_weakened_share_private_roadmap",
            "file_022_misbound_share_private_roadmap",
        }
        for path in [
            ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl",
            ROOT / "data" / "episodes" / "mvp_plus_90_zh.jsonl",
        ]:
            episodes = {episode.episode_id: episode for episode in load_episodes(path)}
            for episode_id in target_ids:
                arguments = episodes[episode_id].candidate_action.arguments
                self.assertEqual(arguments.get("file_sensitivity"), "confidential", episode_id)

    def test_msr_clean_reads_only_canonical_registry(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        episode = copy.deepcopy(next(ep for ep in episodes if ep.required_policy_ids()))
        self.assertTrue(episode.canonical_policy_registry)
        self.assertTrue(episode.noisy_policy_pool)
        self.assertTrue(episode.ground_truth_policies)
        episode.canonical_policy_registry = []
        result = judge_result(episode, MsrAgent().decide(episode))
        self.assertEqual(result.context_policy_ids, [], episode.episode_id)
        self.assertEqual(result.policy_coverage, 0.0, episode.episode_id)
        self.assertEqual(result.policy_source_used, "canonical_policy_registry")

    def test_msr_noisy_reads_noisy_policy_pool(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        episode = copy.deepcopy(next(ep for ep in episodes if ep.required_policy_ids()))
        episode.canonical_policy_registry = []
        result = judge_result(episode, MsrNoisyAgent().decide(episode))
        self.assertNotEqual(result.context_policy_ids, [], episode.episode_id)
        self.assertEqual(result.policy_source_used, "noisy_policy_pool")

    def test_msr_clean_ignores_over_included_carried_policy(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        over_included_safe = [
            ep for ep in episodes
            if ep.policy_carriage_state == "policy_over_included" and ep.is_safe_case
        ]
        self.assertTrue(over_included_safe, "Expected over_included safe cases")
        for episode in over_included_safe:
            result = judge_result(episode, MsrAgent().decide(episode))
            self.assertEqual(result.decision, "allow", episode.episode_id)
            self.assertFalse(result.false_refusal, episode.episode_id)

    def test_policy_pressure_groups(self) -> None:
        for count in [0, 10, 30, 50]:
            episodes = load_episodes(
                ROOT / "data" / "episodes" / "pressure" / f"mvp_plus_90_irrelevant_{count}_en.jsonl"
            )
            self.assertEqual(len(episodes), 90)
            for episode in episodes:
                self.assertEqual(episode.policy_pool_size, len(episode.noisy_policy_pool), episode.episode_id)
                self.assertGreaterEqual(
                    len(episode.canonical_policy_registry),
                    len(episode.initial_policy),
                    episode.episode_id,
                )
                self.assertEqual(len(episode.irrelevant_policy_ids), count, episode.episode_id)
                self.assertTrue(episode.canonical_policy_registry, episode.episode_id)
                required_ids = set(episode.required_policy_ids())
                noisy_ids = {policy.policy_id for policy in episode.noisy_policy_pool}
                canonical_ids = {policy.policy_id for policy in episode.canonical_policy_registry}
                self.assertTrue(required_ids <= noisy_ids, episode.episode_id)
                self.assertTrue(required_ids <= canonical_ids, episode.episode_id)
                self.assertEqual(
                    episode.policy_pool_corrupted,
                    episode.policy_carriage_state != "policy_preserved",
                    episode.episode_id,
                )

    def test_oracle_minimal_uses_ground_truth_policies(self) -> None:
        episodes = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
        for episode in episodes:
            result = judge_result(episode, OracleMinimalAgent().decide(episode))
            self.assertEqual(result.decision, episode.expected_decision, episode.episode_id)
            required_ids = episode.required_policy_ids()
            if required_ids:
                self.assertEqual(set(result.context_policy_ids), set(required_ids), episode.episode_id)
                self.assertEqual(result.policy_coverage, 1.0, episode.episode_id)


if __name__ == "__main__":
    unittest.main()
