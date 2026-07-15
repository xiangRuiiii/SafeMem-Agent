"""LLM 评测重试、检查点修复与恢复入口的离线测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.run_llm_eval import call_with_retries, is_retryable_error, load_existing_results, require_returned_model
from safemem.models import AgentResult


class LlmResumeTest(unittest.TestCase):
    def test_retry_only_retries_transient_error(self) -> None:
        """连接错误应指数退避后成功，配置错误不应重复调用。"""

        attempts = 0
        delays: list[float] = []

        def eventually_succeeds() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("LLM API request failed: connection reset")
            return "ok"

        value = call_with_retries(
            eventually_succeeds,
            max_retries=3,
            retry_delay=1.0,
            retry_max_delay=10.0,
            label="test",
            sleep=delays.append,
        )
        self.assertEqual(value, "ok")
        self.assertEqual(attempts, 3)
        self.assertEqual(delays, [1.0, 2.0])
        self.assertFalse(is_retryable_error(RuntimeError("LLM API HTTP 400: invalid request")))
        self.assertTrue(is_retryable_error(RuntimeError("LLM API HTTP 429: rate limited")))

    def test_final_partial_checkpoint_is_repaired(self) -> None:
        """只有最后半条 JSONL 会被裁剪，已完成结果仍能恢复。"""

        result = AgentResult("episode_1", "llm_no_policy", "allow")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_bytes(
                (json.dumps(result.to_dict(), ensure_ascii=False) + "\n{").encode("utf-8")
            )
            restored = load_existing_results(path)

            self.assertIn(("episode_1", "llm_no_policy"), restored)
            self.assertEqual(path.read_text(encoding="utf-8"), json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    def test_model_guard_rejects_gateway_model_switch(self) -> None:
        """网关返回不同模型时不能把结果混入当前 tag。"""

        result = AgentResult("episode", "llm_no_policy", "allow", llm_model="claude-sonnet-4-6")
        with self.assertRaisesRegex(RuntimeError, "expected 'claude-haiku-4-5'"):
            require_returned_model(result, "claude-haiku-4-5")


if __name__ == "__main__":
    unittest.main()
