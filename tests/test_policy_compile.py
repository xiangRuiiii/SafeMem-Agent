"""验证策略文本编译缓存的稳定键、缓存命中和无效输出处理。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safemem.llm_client import LlmResponse
from safemem.models import Policy
from safemem.policy.compile import (
    ManifestStore,
    MissingManifestError,
    build_compiler_messages,
    compile_predicates,
    compiled_rule_errors,
    compile_policy,
    infer_effect_from_text,
    manifest_key,
    normalize_effect,
)


class FakeClient:
    """用固定 JSON 模拟 compiler，不触发真实网络调用。"""

    def complete(self, *args, **kwargs):
        return LlmResponse(
            '{"kind":"safety_rule","tool":"send_email","predicates":[{"fact":"target_external","operator":"==","value":true}],"effect":"ask_confirmation","severity":"high"}',
            {},
        )


class ArchiveClient:
    """模拟把普通工作流动作错误放进 effect 的模型输出。"""

    def complete(self, *args, **kwargs):
        return LlmResponse(
            '{"kind":"non_safety","tool":"","predicates":[],"effect":"archive","severity":"low"}',
            {},
        )


class InvalidSchemaClient:
    """模拟模型使用领域名、未知对象和虚构条件字段的错误输出。"""

    def complete(self, *args, **kwargs):
        return LlmResponse(
            '{"kind":"safety_rule","tool":"email","predicates":[{"fact":"action","operator":"==","value":"review"}],"effect":"ask_confirmation","severity":"medium"}',
            {},
        )


class PolicyCompileTest(unittest.TestCase):
    """缓存键必须随模型或可信 provenance 改变，避免混用旧编译结果。"""

    def test_manifest_round_trip_and_missing_error(self) -> None:
        item = Policy("p1", "Ask before external email.", issuer="organization", authority=3)
        rule = compile_policy(item, FakeClient(), "compiler-a")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cache.jsonl"
            store = ManifestStore(path, "compiler-a")
            store.add(item, "compiler-a", rule)
            store.save()
            loaded = ManifestStore(path, "compiler-a")
            self.assertEqual(loaded.rule_for(item).tool, "send_email")
            with self.assertRaises(MissingManifestError):
                loaded.rule_for(Policy("p2", "Different policy", issuer="organization", authority=3))

    def test_manifest_rebinds_shared_semantics_to_current_policy_id(self) -> None:
        """同文同 provenance 的策略可以共用编译结果，但证书必须保留当前 policy ID。"""

        first = Policy("first", "Ask before external email.", priority=1, issuer="organization", authority=3)
        second = Policy("second", "Ask before external email.", priority=9, issuer="organization", authority=3)
        rule = compile_policy(first, FakeClient(), "compiler-a")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cache.jsonl"
            store = ManifestStore(path, "compiler-a")
            store.add(first, "compiler-a", rule)
            store.save()
            rebound = ManifestStore(path, "compiler-a").rule_for(second)
        self.assertEqual(rebound.policy_id, "second")
        self.assertEqual(rebound.text, second.text)
        self.assertEqual(rebound.priority, 9)

    def test_manifest_key_changes_with_model_and_provenance(self) -> None:
        item = Policy("p1", "Policy", issuer="organization", authority=3)
        changed = Policy("p1", "Policy", issuer="organization", authority=4)
        self.assertNotEqual(manifest_key(item, "a"), manifest_key(item, "b"))
        self.assertNotEqual(manifest_key(item, "a"), manifest_key(changed, "a"))

    def test_effect_aliases_match_the_decision_protocol(self) -> None:
        self.assertEqual(normalize_effect("confirm"), "ask_confirmation")
        self.assertEqual(normalize_effect("deny"), "block")
        self.assertEqual(normalize_effect("allow_execute"), "allow")
        self.assertEqual(normalize_effect("warn"), "ask_confirmation")
        self.assertEqual(normalize_effect("require_approval"), "ask_confirmation")
        self.assertEqual(normalize_effect("block_without_approval"), "block")

    def test_text_fallback_recovers_a_missing_effect(self) -> None:
        self.assertEqual(infer_effect_from_text("Ask for confirmation before sharing."), "ask_confirmation")
        self.assertEqual(infer_effect_from_text("Do not export credentials."), "block")
        self.assertEqual(infer_effect_from_text("Be careful with email actions."), "ask_confirmation")
        self.assertEqual(infer_effect_from_text("Require approval before sharing."), "ask_confirmation")

    def test_non_safety_effect_is_cached_but_inactive(self) -> None:
        item = Policy("noise", "Archive draft email after review.")
        rule = compile_policy(item, ArchiveClient(), "compiler-a")
        self.assertEqual(rule.effect, "ask_confirmation")
        self.assertFalse(rule.active)
        self.assertEqual(rule.compiler_status, "inactive_non_safety")

    def test_invalid_compiled_schema_is_cached_but_inactive(self) -> None:
        item = Policy("invalid", "Ask before sending an external email.")
        rule = compile_policy(item, InvalidSchemaClient(), "compiler-a")
        self.assertFalse(rule.active)
        self.assertEqual(rule.compiler_status, "inactive_invalid_schema:tool,predicates")

    def test_compiler_prompt_requires_public_action_ontology(self) -> None:
        item = Policy("p1", "Ask before sending an external email.")
        messages = build_compiler_messages(item, {"issuer": "organization", "authority": 3})
        prompt = messages[0]["content"]
        self.assertIn("send_email", prompt)
        self.assertIn("archive_channel", prompt)
        self.assertIn("email or slack is never a tool", prompt)
        self.assertIn("target_external", prompt)
        self.assertIn("data_sensitivity", prompt)
        self.assertIn("demonstrations", prompt)

    def test_predicates_compile_to_verifiable_conditions(self) -> None:
        condition, errors = compile_predicates(
            [
                {"fact": "target_external", "operator": "eq", "value": True},
                {"fact": "data_sensitivity", "operator": "==", "value": "confidential"},
            ]
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            condition,
            "target_external == true and data_sensitivity == 'confidential'",
        )
        self.assertEqual(compile_predicates([{"fact": "action", "operator": "==", "value": "send"}])[1], ["predicates"])

    def test_compiled_schema_accepts_supported_facts_only(self) -> None:
        self.assertEqual(
            compiled_rule_errors("send_email", "external_recipient", "recipient_domain != company_domain"),
            [],
        )
        self.assertEqual(compiled_rule_errors("read_schema", "any", ""), [])
        self.assertEqual(compiled_rule_errors("search_web", "any", ""), [])
        self.assertEqual(
            compiled_rule_errors("email", "channel", "action == 'review'"),
            ["tool", "object", "condition"],
        )


if __name__ == "__main__":
    unittest.main()
