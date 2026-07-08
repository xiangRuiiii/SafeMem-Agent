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
            "hybrid_msr_clean",
            "hybrid_msr_noisy",
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

    def test_hybrid_msr_uses_expected_sources(self) -> None:
        episode = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")[0]
        clean_context = policy_context_for_method(episode, "hybrid_msr_clean")
        noisy_context = policy_context_for_method(episode, "hybrid_msr_noisy")

        self.assertEqual(clean_context.source, "canonical_policy_registry")
        self.assertEqual(noisy_context.source, "noisy_policy_pool")
        self.assertLessEqual(len(clean_context.policies), 4)
        self.assertLessEqual(len(noisy_context.policies), 4)


if __name__ == "__main__":
    unittest.main()
