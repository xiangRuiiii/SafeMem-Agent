"""验证 hard-noise 挑战集的双语分布与结构化 V-MSR 选择边界。"""

from __future__ import annotations

import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

from safemem.models import Episode
from safemem.policy.vmsr import VerificationGuidedMsr
from scripts.make_vmsr_hard_noise import HARD_NOISE_TYPES, build_episodes, validate


ROOT = Path(__file__).resolve().parents[1]


class HardNoiseTest(unittest.TestCase):
    """所有 hard negative 必须同工具可见，但不能进入正确的最小证明。"""

    def test_distribution_and_bilingual_alignment(self) -> None:
        english = build_episodes("en")
        chinese = build_episodes("zh")
        validate(english, chinese)
        self.assertEqual(Counter(item["domain"] for item in english), {
            "email": 6, "file": 6, "calendar": 6, "slack": 6, "database": 6, "browser": 6,
        })
        self.assertEqual(Counter(item["challenge_type"] for item in english), {kind: 12 for kind in HARD_NOISE_TYPES})

    def test_struct_verifier_rejects_every_hard_negative(self) -> None:
        engine = VerificationGuidedMsr("struct")
        for raw in build_episodes("en"):
            episode = Episode.from_dict(raw)
            result = engine.select(episode.candidate_action, list(episode.noisy_policy_pool))
            selected = {policy.policy_id for policy in result.policies}
            self.assertEqual(selected, set(episode.certificate_policy_ids), episode.episode_id)
            self.assertFalse(selected & set(raw["hard_negative_policy_ids"]), episode.episode_id)

    def test_generator_script_is_importable_when_run_directly(self) -> None:
        """直接执行脚本仅验证启动路径，不生成或读取挑战集文件。"""

        command = [sys.executable, "-c", "import runpy; runpy.run_path('scripts/make_vmsr_hard_noise.py', run_name='not_main')"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
