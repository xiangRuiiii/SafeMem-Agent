from __future__ import annotations

import unittest
from pathlib import Path

from safemem.agents.llm_agent import LLM_METHOD_GROUPS, policy_context_for_method
from safemem.data import load_episodes

ROOT = Path(__file__).resolve().parents[1]


class RetrievalTest(unittest.TestCase):
    def test_retrieval_methods_are_registered(self) -> None:
        expected = {
            "bm25_clean_top1",
            "bm25_clean_top3",
            "bm25_clean_top5",
            "bm25_noisy_top3",
            "embedding_clean_top3",
            "embedding_noisy_top3",
        }
        self.assertTrue(expected <= set(LLM_METHOD_GROUPS))

    def test_bm25_and_embedding_return_topk_contexts(self) -> None:
        episode = next(
            item
            for item in load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")
            if item.episode_id == "file_008_absent_share_private_roadmap"
        )
        bm25_context = policy_context_for_method(episode, "bm25_clean_top3")
        embedding_context = policy_context_for_method(episode, "embedding_clean_top3")

        self.assertEqual(bm25_context.source, "canonical_policy_registry")
        self.assertEqual(embedding_context.source, "canonical_policy_registry")
        self.assertEqual(len(bm25_context.policies), 3)
        self.assertEqual(len(embedding_context.policies), 3)
        self.assertTrue(all(policy.policy_id for policy in bm25_context.policies))
        self.assertTrue(all(policy.policy_id for policy in embedding_context.policies))

    def test_noisy_retrieval_uses_noisy_pool(self) -> None:
        episode = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")[0]
        bm25_context = policy_context_for_method(episode, "bm25_noisy_top5")
        embedding_context = policy_context_for_method(episode, "embedding_noisy_top5")

        self.assertEqual(bm25_context.source, "noisy_policy_pool")
        self.assertEqual(embedding_context.source, "noisy_policy_pool")
        self.assertEqual(len(bm25_context.policies), 5)
        self.assertEqual(len(embedding_context.policies), 5)


if __name__ == "__main__":
    unittest.main()
