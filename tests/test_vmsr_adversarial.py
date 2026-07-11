"""验证 V-MSR 多策略池对抗集的分布、证书边界与未知证据升级。"""

from __future__ import annotations

import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

from safemem.models import Episode
from safemem.policy.vmsr import VerificationGuidedMsr
from scripts.make_vmsr_adversarial import ADVERSARIAL_TYPES, build_episodes, validate


ROOT = Path(__file__).resolve().parents[1]


class AdversarialChallengeTest(unittest.TestCase):
    """结构化 V-MSR 必须只从动作与策略池恢复挑战集的最小证书。"""

    def test_distribution_and_pool_pressure(self) -> None:
        english = build_episodes("en")
        chinese = build_episodes("zh")
        validate(english, chinese)
        self.assertEqual(Counter(item["domain"] for item in english), {domain: 6 for domain in ("email", "file", "calendar", "slack", "database", "browser")})
        self.assertEqual(Counter(item["challenge_type"] for item in english), {kind: 12 for kind in ADVERSARIAL_TYPES})
        self.assertTrue(all(len(item["noisy_policy_pool"]) > 8 for item in english))
        self.assertTrue(all(len(item["adversarial_policy_ids"]) == 9 for item in english))

    def test_struct_verifier_selects_minimal_certificate_without_labels(self) -> None:
        engine = VerificationGuidedMsr("struct")
        for raw in build_episodes("en"):
            episode = Episode.from_dict(raw)
            result = engine.select(episode.candidate_action, list(episode.noisy_policy_pool))
            selected = {policy.policy_id for policy in result.policies}
            self.assertEqual(selected, set(episode.certificate_policy_ids), episode.episode_id)
            self.assertFalse(selected & set(raw["adversarial_policy_ids"]), episode.episode_id)
            self.assertEqual(result.decision, episode.expected_decision, episode.episode_id)
            self.assertEqual(len(result.candidate_policy_ids), 8, episode.episode_id)
            if raw["challenge_type"] == "unknown_evidence" and raw["expected_decision"] == "ask_confirmation":
                self.assertTrue(result.selection.unknown_escalated, episode.episode_id)
                self.assertFalse(result.selection.stable, episode.episode_id)
            else:
                self.assertFalse(result.selection.unknown_escalated, episode.episode_id)
            if raw["challenge_type"] == "authority_shadowing":
                self.assertTrue(result.selection.conflict_resolved, episode.episode_id)

    def test_generator_is_importable_when_run_directly(self) -> None:
        """直接启动路径只验证导入，不生成或读取对抗 episode 文件。"""

        command = [sys.executable, "-c", "import runpy; runpy.run_path('scripts/make_vmsr_adversarial.py', run_name='not_main')"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
