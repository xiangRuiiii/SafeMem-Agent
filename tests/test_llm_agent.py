from __future__ import annotations

import json
import unittest
from pathlib import Path

from safemem.agents.llm_agent import LlmPolicyAgent, build_llm_messages, policy_context_for_method
from safemem.data import load_episodes
from safemem.eval.judge import judge_result
from safemem.llm_client import LlmResponse

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmResponse:
        self.messages = messages
        return LlmResponse(
            text=json.dumps(
                {
                    "decision": "ask_confirmation",
                    "reason": "Policy requires confirmation.",
                    "policy_ids_used": ["p_email_contract_confirm"],
                    "confidence": 0.8,
                }
            ),
            raw={},
            model=model,
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
        )


class LlmAgentTest(unittest.TestCase):
    def test_llm_agent_does_not_prompt_with_answer_fields(self) -> None:
        episode = next(ep for ep in load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl") if ep.required_policy_ids())
        client = FakeClient()
        agent = LlmPolicyAgent("msr_clean", client, "fake-model")

        result = judge_result(episode, agent.decide(episode))
        prompt = json.dumps(client.messages, ensure_ascii=False)

        forbidden = [
            "required_policy_ids",
            "oracle_minimal_policy_ids",
            "expected_decision",
            "allowed_decisions",
            "forbidden_decisions",
            "ground_truth_policies",
            "labels",
        ]
        for field in forbidden:
            self.assertNotIn(field, prompt)

        self.assertEqual(result.agent, "llm_msr_clean")
        self.assertEqual(result.agent_group, "clean 检索恢复")
        self.assertEqual(result.policy_source_used, "canonical_policy_registry")
        self.assertEqual(result.llm_model, "fake-model")
        self.assertEqual(result.llm_total_tokens, 120)

    def test_no_policy_prompt_has_empty_policy_context(self) -> None:
        episode = load_episodes(ROOT / "data" / "episodes" / "mvp_plus_90_en.jsonl")[0]
        context = policy_context_for_method(episode, "no_policy")
        messages = build_llm_messages(episode, context)
        user_payload = json.loads(messages[1]["content"])

        self.assertEqual(context.source, "none")
        self.assertEqual(user_payload["policy_context"], [])
        self.assertIn("candidate_action", user_payload)
        self.assertIn("task_goal", user_payload)


if __name__ == "__main__":
    unittest.main()
