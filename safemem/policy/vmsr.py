"""Verification-Guided MSR：用动作证据构造最小、稳定的策略安全证明。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from safemem.models import Action, Decision, Policy
from safemem.policy.bm25 import BM25Retriever
from safemem.policy.compile import ManifestStore
from safemem.policy.select import PolicySelection, select_minimal
from safemem.policy.verify import PolicyCheck, PolicyRule, verify_policy


Representation = Literal["struct", "text"]


@dataclass
class VmsrResult:
    """提供给 LLM 上下文和执行 Guard 的紧凑证明结果。"""

    policies: list[Policy]
    decision: Decision
    selection: PolicySelection
    candidate_policy_ids: list[str]

    def certificate(self) -> dict[str, object]:
        return {
            "decision_floor": self.decision,
            "policy_ids": [policy.policy_id for policy in self.policies],
            "unresolved_policy_ids": self.selection.unresolved_policy_ids,
            "unknown_policy_ids": self.selection.unknown_policy_ids,
            "unknown_escalated": self.selection.unknown_escalated,
            "decision_stable": self.selection.stable,
            "minimal": self.selection.minimal,
            "conflict_resolved": self.selection.conflict_resolved,
            "excluded_policy_reasons": self.selection.excluded_reasons,
            "evidence": [
                {
                    "policy_id": item.rule.policy_id,
                    "status": item.status,
                    "bindings": item.bindings,
                }
                for item in self.selection.checks
                if item.rule.policy_id in (
                    {policy.policy_id for policy in self.policies}
                    | set(self.selection.unknown_policy_ids)
                    | set(self.selection.unresolved_policy_ids)
                )
            ],
        }


def certificate_is_internally_valid(certificate: dict[str, object]) -> bool:
    """检查证书自身是否完整表达 entailed、unknown 与冲突状态，不使用隐藏答案。"""

    if certificate.get("unresolved_policy_ids"):
        return False
    evidence = {
        str(item.get("policy_id", "")): str(item.get("status", ""))
        for item in certificate.get("evidence", [])  # type: ignore[union-attr]
        if isinstance(item, dict)
    }
    selected = {str(item) for item in certificate.get("policy_ids", [])}  # type: ignore[arg-type]
    unknown = {str(item) for item in certificate.get("unknown_policy_ids", [])}  # type: ignore[arg-type]
    if any(evidence.get(policy_id) != "entailed" for policy_id in selected):
        return False
    if certificate.get("unknown_escalated"):
        return (
            bool(unknown)
            and certificate.get("decision_floor") in {"ask_confirmation", "block"}
            and all(evidence.get(policy_id) == "unknown" for policy_id in unknown)
        )
    return not unknown


class VerificationGuidedMsr:
    """核心 API 只接收 Action 与 Policy 列表，因此无法读取 episode 答案字段。"""

    def __init__(
        self,
        representation: Representation,
        *,
        manifest_store: ManifestStore | None = None,
        candidate_limit: int = 8,
        candidate_retriever: object | None = None,
    ) -> None:
        if representation == "text" and manifest_store is None:
            raise ValueError("V-MSR text mode requires a prebuilt ManifestStore.")
        self.representation = representation
        self.manifest_store = manifest_store
        # 未配置 dense endpoint 时保持 BM25 默认，避免评估过程出现隐式网络调用。
        self.retriever = candidate_retriever or BM25Retriever(top_k=candidate_limit)

    def select(self, action: Action, policies: list[Policy]) -> VmsrResult:
        """从文本高召回开始，再对同工具策略做验证闭包以检查决策稳定性。"""

        candidates = self.retriever.select(action, policies)
        rules = {policy.policy_id: self._rule_for(policy) for policy in policies}
        # 只把候选文本送入 LLM；这里扩展同工具闭包仅消耗本地计算，用于防止遗漏冲突策略。
        candidate_ids = {policy.policy_id for policy in candidates}
        action_tool = action.tool
        frontier = [
            policy
            for policy in policies
            if policy.policy_id in candidate_ids or not rules[policy.policy_id].tool or rules[policy.policy_id].tool == action_tool
        ]
        checks = [verify_policy(rules[policy.policy_id], action) for policy in frontier]
        selection = select_minimal(checks)
        by_id = {policy.policy_id: policy for policy in policies}
        selected = [by_id[rule.policy_id] for rule in selection.policies if rule.policy_id in by_id]
        return VmsrResult(selected, selection.decision, selection, [policy.policy_id for policy in candidates])

    def _rule_for(self, policy: Policy) -> PolicyRule:
        if self.representation == "struct":
            return PolicyRule.from_policy(policy)
        assert self.manifest_store is not None
        return self.manifest_store.rule_for(policy)
