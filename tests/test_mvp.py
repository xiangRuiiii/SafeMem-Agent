from __future__ import annotations

import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
