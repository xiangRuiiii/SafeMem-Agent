"""验证 V-MSR 挑战集在内存中的构造分布，不读取生成后的 JSONL。"""

from __future__ import annotations

import unittest
from collections import Counter

from scripts.make_vmsr_episodes import CHALLENGE_TYPES, DOMAIN_CONFIGS, build_episodes, validate


class VmsrGeneratorTest(unittest.TestCase):
    """生成器必须在写盘前保证双语 72 条数据的结构完整。"""

    def test_distribution_and_bilingual_alignment(self) -> None:
        english = build_episodes("en")
        chinese = build_episodes("zh")
        validate(english, chinese)
        self.assertEqual(Counter(item["domain"] for item in english), {name: 12 for name in DOMAIN_CONFIGS})
        self.assertEqual(Counter(item["challenge_type"] for item in english), {name: 12 for name in CHALLENGE_TYPES})
        self.assertEqual(Counter(item["is_safe_case"] for item in english), {False: 36, True: 36})

        risky = {
            (item["domain"], item["challenge_type"]): item
            for item in english
            if not item["is_safe_case"]
        }
        for domain in DOMAIN_CONFIGS:
            paraphrased = risky[(domain, "paraphrased_hard_negative")]
            self.assertEqual(paraphrased["candidate_action"]["arguments"]["sensitivity"], "public")
            for challenge in ("authority_conflict", "minimal_proof"):
                self.assertEqual(
                    set(risky[(domain, challenge)]["certificate_policy_ids"]),
                    {"external_confirm", "sensitive_block"},
                )
        self.assertEqual(
            risky[("file", "evidence_resolution")]["candidate_action"]["arguments"]["path"],
            "/workspace/project_plan.md",
        )


if __name__ == "__main__":
    unittest.main()
