"""覆盖 Verification-Guided MSR 的三值验证、冲突解析和执行门控。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safemem.models import Action, Policy
from safemem.models import Episode
from safemem.agents.llm_agent import build_llm_messages, policy_context_for_method
from safemem.policy.compile import ManifestStore
from safemem.policy.dense import DenseRetriever
from safemem.policy.facts import extract_facts, fact_value
from safemem.policy.guard import apply_guard
from safemem.policy.verify import PolicyRule
from safemem.policy.vmsr import VerificationGuidedMsr


def policy(
    policy_id: str,
    *,
    object_name: str = "external_recipient",
    condition: str = "recipient_domain != company_domain",
    effect: str = "ask_confirmation",
    authority: int = 3,
    priority: int = 1,
) -> Policy:
    return Policy(
        policy_id=policy_id,
        text=f"Policy {policy_id}",
        tool="send_email",
        object=object_name,
        condition=condition,
        effect=effect,  # type: ignore[arg-type]
        issuer="organization",
        authority=authority,
        priority=priority,
    )


class VerificationGuidedMsrTest(unittest.TestCase):
    """所有核心测试直接调用 Action + Policy API，避免 episode 标注泄露。"""

    def test_composite_certificate_keeps_distinct_obligations(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        confirm = policy("confirm")
        block = policy("block", object_name="sensitive_data", condition="sensitivity == 'confidential'", effect="block", authority=4)
        result = VerificationGuidedMsr("struct").select(action, [confirm, block])
        self.assertEqual(result.decision, "block")
        self.assertEqual({item.policy_id for item in result.policies}, {"confirm", "block"})
        self.assertTrue(result.selection.minimal)
        self.assertTrue(result.selection.stable)

    def test_unknown_condition_escalates_to_confirmation(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com"})
        confirm = policy("confirm")
        block = policy("block", object_name="sensitive_data", condition="sensitivity == 'confidential'", effect="block", authority=4)
        result = VerificationGuidedMsr("struct").select(action, [confirm, block])
        self.assertEqual(result.decision, "ask_confirmation")
        self.assertTrue(result.selection.unknown_escalated)
        self.assertFalse(result.selection.stable)
        self.assertEqual(result.selection.unknown_policy_ids, ["block"])
        evidence = {item["policy_id"]: item["status"] for item in result.certificate()["evidence"]}
        self.assertEqual(evidence["block"], "unknown")

    def test_unknown_policy_never_downgrades_known_block(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        known_block = policy(
            "known_block", object_name="sensitive_data", condition="sensitivity == 'confidential'",
            effect="block", authority=4,
        )
        unknown_confirm = policy(
            "unknown_confirm", object_name="any", condition="contains_secret == true",
            effect="ask_confirmation", authority=3,
        )
        result = VerificationGuidedMsr("struct").select(action, [known_block, unknown_confirm])
        self.assertEqual(result.decision, "block")
        self.assertTrue(result.selection.unknown_escalated)
        self.assertFalse(result.selection.stable)

    def test_normalized_facts_work_across_target_types(self) -> None:
        email = extract_facts(
            Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        )
        browser = extract_facts(
            Action("submit_form", {"site_domain": "company.com", "sensitivity": "public"})
        )
        file_action = extract_facts(
            Action("share_file", {"path": "/protected/contract.pdf", "attachments": ["contract.pdf"], "bulk": True})
        )
        self.assertIs(fact_value(email, "target_external"), True)
        self.assertEqual(fact_value(email, "data_sensitivity"), "confidential")
        self.assertIs(fact_value(browser, "target_external"), False)
        self.assertEqual(fact_value(browser, "data_sensitivity"), "public")
        self.assertEqual(fact_value(file_action, "path_scope"), "protected")
        self.assertEqual(fact_value(file_action, "attachment_kind"), "contract")
        self.assertIs(fact_value(file_action, "operation_bulk"), True)

    def test_specific_authoritative_allow_resolves_broad_memory_block(self) -> None:
        action = Action("send_email", {"recipient": "alice@company.com", "sensitivity": "public"})
        broad_block = policy("memory_block", object_name="any", condition="", effect="block", authority=1)
        internal_allow = policy(
            "internal_allow",
            object_name="any",
            condition="recipient_domain == company_domain and sensitivity == 'public'",
            effect="allow",
            authority=4,
        )
        result = VerificationGuidedMsr("struct").select(action, [broad_block, internal_allow])
        self.assertEqual(result.decision, "allow")
        self.assertEqual([item.policy_id for item in result.policies], ["internal_allow"])
        self.assertTrue(result.selection.conflict_resolved)

    def test_duplicate_obligation_keeps_authoritative_policy(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        canonical = policy(
            "canonical", object_name="sensitive_data", condition="sensitivity == 'confidential'",
            effect="block", authority=4,
        )
        duplicate = policy(
            "duplicate", object_name="sensitive_data", condition="sensitivity == 'confidential'",
            effect="block", authority=1,
        )
        result = VerificationGuidedMsr("struct").select(action, [canonical, duplicate])
        self.assertEqual([item.policy_id for item in result.policies], ["canonical"])
        self.assertEqual(result.selection.excluded_reasons["duplicate"], "duplicate_of:canonical")

    def test_guard_only_raises_permissive_decisions(self) -> None:
        self.assertEqual(apply_guard("allow", "ask_confirmation"), ("ask_confirmation", True))
        self.assertEqual(apply_guard("block", "ask_confirmation"), ("block", False))
        self.assertEqual(apply_guard("revise", "block"), ("revise", False))

    def test_text_mode_ignores_policy_structured_fields(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        raw = Policy(
            policy_id="p_raw",
            text="Block confidential external email.",
            tool="wrong_tool",
            object="wrong_object",
            condition="wrong == true",
            effect="allow",
            issuer="system",
            authority=4,
        )
        rule = PolicyRule(
            policy_id="p_raw",
            text=raw.text,
            tool="send_email",
            object="any",
            condition="data_sensitivity == 'confidential'",
            effect="block",
            severity="critical",
            priority=1,
            issuer="system",
            authority=4,
            version=1,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.jsonl"
            store = ManifestStore(path, "compiler-model")
            store.add(raw, "compiler-model", rule)
            store.save()
            result = VerificationGuidedMsr("text", manifest_store=ManifestStore(path, "compiler-model")).select(action, [raw])
        self.assertEqual(result.decision, "block")

    def test_text_fact_predicates_keep_composite_obligations(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        external = Policy("external", "Ask before external email.", issuer="organization", authority=3)
        sensitive = Policy("sensitive", "Block confidential email.", issuer="system", authority=4)
        rules = [
            PolicyRule(
                "external", external.text, "send_email", "any", "target_external == true",
                "ask_confirmation", "high", 0, "organization", 3, 1,
            ),
            PolicyRule(
                "sensitive", sensitive.text, "send_email", "any", "data_sensitivity == 'confidential'",
                "block", "critical", 0, "system", 4, 1,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.jsonl"
            store = ManifestStore(path, "compiler-model")
            for raw, rule in zip((external, sensitive), rules):
                store.add(raw, "compiler-model", rule)
            store.save()
            result = VerificationGuidedMsr(
                "text", manifest_store=ManifestStore(path, "compiler-model")
            ).select(action, [external, sensitive])
        self.assertEqual(result.decision, "block")
        self.assertEqual({item.policy_id for item in result.policies}, {"external", "sensitive"})

    def test_text_prompt_hides_structured_fields_ids_and_labels(self) -> None:
        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        raw = Policy(
            policy_id="p_semantic_confidential_block",
            text="Block confidential external email.",
            tool="hidden_wrong_tool",
            object="hidden_wrong_object",
            condition="hidden == true",
            effect="allow",
            issuer="system",
            authority=4,
        )
        episode = Episode(
            episode_id="memory_only",
            domain="email",
            task_goal="Send an email.",
            initial_policy=[],
            source_policies=[],
            clean_irrelevant_policies=[],
            corruption_artifacts=[],
            canonical_policy_registry=[raw],
            noisy_policy_pool=[raw],
            carried_policy=[],
            ground_truth_policies=[],
            long_context=[],
            policy_carriage_state="policy_preserved",
            assembled_policy=[],
            risky_request="Send it.",
            candidate_action=action,
            expected_decision="block",
            unsafe_if_executed=True,
            labels={"hidden_answer": "must_not_appear"},
            required_policy_ids_value=["must_not_appear"],
        )
        rule = PolicyRule(
            policy_id=raw.policy_id,
            text=raw.text,
            tool="send_email",
            object="sensitive_data",
            condition="sensitivity == 'confidential'",
            effect="block",
            severity="critical",
            priority=1,
            issuer="system",
            authority=4,
            version=1,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.jsonl"
            store = ManifestStore(path, "compiler-model")
            store.add(raw, "compiler-model", rule)
            store.save()
            context = policy_context_for_method(
                episode,
                "vmsr_text_context_noisy",
                vmsr_cache_path=path,
                vmsr_compiler_model="compiler-model",
            )
            prompt = build_llm_messages(episode, context)[1]["content"]
        for forbidden in ("p_semantic_confidential_block", "hidden_wrong_tool", "hidden_wrong_object", "must_not_appear"):
            self.assertNotIn(forbidden, prompt)

    def test_dense_retriever_can_be_injected_without_changing_vmsr_api(self) -> None:
        class FakeEmbeddingClient:
            def embed(self, texts, *, model):
                return [[1.0, 0.0]] + [[1.0, 0.0] for _ in texts[1:]]

        action = Action("send_email", {"recipient": "partner@example.com", "sensitivity": "confidential"})
        block = policy("block", object_name="sensitive_data", condition="sensitivity == 'confidential'", effect="block", authority=4)
        dense = DenseRetriever(FakeEmbeddingClient(), "fake", top_k=8)
        result = VerificationGuidedMsr("struct", candidate_retriever=dense).select(action, [block])
        self.assertEqual(result.decision, "block")


if __name__ == "__main__":
    unittest.main()
