from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from safemem.agents.baselines import AllPolicyAgent
from safemem.agents.msr_agent import MsrAgent
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

    def test_all_policy_matches_mvp_labels(self) -> None:
        paths = [
            ROOT / "data" / "episodes" / "mvp_en.jsonl",
            ROOT / "data" / "episodes" / "mvp_zh.jsonl",
        ]
        for path in paths:
            for episode in load_episodes(path):
                result = judge_result(episode, AllPolicyAgent().decide(episode))
                self.assertEqual(result.decision, episode.expected_decision, episode.episode_id)

    def test_mvp_plus_template_schema(self) -> None:
        paths = [
            ROOT / "data" / "episodes" / "mvp_plus_template_en.jsonl",
            ROOT / "data" / "episodes" / "mvp_plus_template_zh.jsonl",
        ]
        for path in paths:
            episodes = load_episodes(path)
            self.assertEqual(len(episodes), 2)
            self.assertEqual([episode.policy_pool_size for episode in episodes], [23, 23])
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


if __name__ == "__main__":
    unittest.main()
