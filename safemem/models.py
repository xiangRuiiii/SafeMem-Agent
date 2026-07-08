from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Decision = Literal["allow", "block", "ask_confirmation", "revise"]


@dataclass
class Policy:
    policy_id: str
    text: str
    source: str = "user"
    scope: str = ""
    actor: str = "agent"
    tool: str = ""
    action: str = ""
    object: str = ""
    condition: str = ""
    effect: Decision = "allow"
    severity: str = "low"
    priority: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Policy":
        return cls(
            policy_id=data["policy_id"],
            text=data.get("text") or data.get("evidence", ""),
            source=data.get("source", "user"),
            scope=data.get("scope", ""),
            actor=data.get("actor", "agent"),
            tool=data.get("tool", data.get("action", "")),
            action=data.get("action", data.get("tool", "")),
            object=data.get("object", ""),
            condition=data.get("condition", ""),
            effect=data.get("effect", "allow"),
            severity=data.get("severity", "low"),
            priority=int(data.get("priority", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "text": self.text,
            "source": self.source,
            "scope": self.scope,
            "actor": self.actor,
            "tool": self.tool,
            "action": self.action,
            "object": self.object,
            "condition": self.condition,
            "effect": self.effect,
            "severity": self.severity,
            "priority": self.priority,
        }


@dataclass
class Action:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        return cls(tool=data["tool"], arguments=dict(data.get("arguments", {})))

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "arguments": self.arguments}


@dataclass
class Episode:
    episode_id: str
    domain: str
    task_goal: str
    initial_policy: list[Policy]
    source_policies: list[Policy]
    clean_irrelevant_policies: list[Policy]
    corruption_artifacts: list[Policy]
    canonical_policy_registry: list[Policy]
    noisy_policy_pool: list[Policy]
    carried_policy: list[Policy]
    ground_truth_policies: list[Policy]
    long_context: list[str]
    policy_carriage_state: str
    assembled_policy: list[str]
    risky_request: str
    candidate_action: Action
    expected_decision: Decision
    unsafe_if_executed: bool
    labels: dict[str, Any] = field(default_factory=dict)
    required_policy_ids_value: list[str] = field(default_factory=list)
    irrelevant_policy_ids: list[str] = field(default_factory=list)
    policy_pool_size: int = 0
    policy_failure_type: str = ""
    is_safe_case: bool = False
    allowed_decisions: list[str] = field(default_factory=list)
    forbidden_decisions: list[str] = field(default_factory=list)
    risk_level: str = ""
    msr_policy_source: str = "canonical_policy_registry"
    policy_pool_corrupted: bool = False
    corrupted_policy_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        initial_policy = [Policy.from_dict(item) for item in data.get("initial_policy", [])]
        source_policies = _policies_from(data, "source_policies", initial_policy)
        clean_irrelevant_policies = _policies_from(data, "clean_irrelevant_policies", [])
        corruption_artifacts = _policies_from(data, "corruption_artifacts", [])
        canonical_policy_registry = _policies_from(
            data,
            "canonical_policy_registry",
            _policies_from(data, "policy_registry", source_policies + clean_irrelevant_policies),
        )
        noisy_policy_pool = _policies_from(
            data,
            "noisy_policy_pool",
            _policies_from(data, "policy_pool", canonical_policy_registry + corruption_artifacts),
        )
        carried_policy = [Policy.from_dict(item) for item in data.get("carried_policy", [])]
        if "carried_policy" not in data:
            carried_policy = _default_carried_policy(data, initial_policy, noisy_policy_pool)
        ground_truth_policies = [Policy.from_dict(item) for item in data.get("ground_truth_policies", [])]
        if "ground_truth_policies" not in data:
            ground_truth_policies = []
        required_policy_ids = list(
            data.get("required_policy_ids", data.get("labels", {}).get("required_policy_ids", []))
        )
        return cls(
            episode_id=data["episode_id"],
            domain=data["domain"],
            task_goal=data.get("task_goal", ""),
            initial_policy=initial_policy,
            source_policies=source_policies,
            clean_irrelevant_policies=clean_irrelevant_policies,
            corruption_artifacts=corruption_artifacts,
            canonical_policy_registry=canonical_policy_registry,
            noisy_policy_pool=noisy_policy_pool,
            carried_policy=carried_policy,
            ground_truth_policies=ground_truth_policies,
            long_context=list(data.get("long_context", [])),
            policy_carriage_state=data.get("policy_carriage_state", ""),
            assembled_policy=list(data.get("assembled_policy", [])),
            risky_request=data.get("risky_request", ""),
            candidate_action=Action.from_dict(data["candidate_action"]),
            expected_decision=data.get("expected_decision", "allow"),
            unsafe_if_executed=bool(data.get("unsafe_if_executed", False)),
            labels=dict(data.get("labels", {})),
            required_policy_ids_value=required_policy_ids,
            irrelevant_policy_ids=list(data.get("irrelevant_policy_ids", [])),
            policy_pool_size=int(data.get("noisy_policy_pool_size", data.get("policy_pool_size", len(noisy_policy_pool)))),
            policy_failure_type=data.get("policy_failure_type", data.get("labels", {}).get("policy_failure_type", "")),
            is_safe_case=bool(data.get("is_safe_case", not data.get("unsafe_if_executed", False))),
            allowed_decisions=list(data.get("allowed_decisions", [])),
            forbidden_decisions=list(data.get("forbidden_decisions", [])),
            risk_level=data.get("risk_level", ""),
            msr_policy_source=data.get("msr_policy_source", "canonical_policy_registry"),
            policy_pool_corrupted=bool(data.get("policy_pool_corrupted", False)),
            corrupted_policy_ids=list(data.get("corrupted_policy_ids", [])),
        )

    def required_policy_ids(self) -> list[str]:
        if self.required_policy_ids_value:
            return list(self.required_policy_ids_value)
        return list(self.labels.get("required_policy_ids", []))

    @property
    def policy_pool(self) -> list[Policy]:
        return self.noisy_policy_pool

    @property
    def policy_registry(self) -> list[Policy]:
        return self.canonical_policy_registry


def _policies_from(
    data: dict[str, Any],
    key: str,
    fallback: list[Policy],
) -> list[Policy]:
    if key not in data:
        return list(fallback)
    return [Policy.from_dict(item) for item in data.get(key, [])]


def _default_carried_policy(
    data: dict[str, Any],
    initial_policy: list[Policy],
    policy_pool: list[Policy],
) -> list[Policy]:
    state = data.get("policy_carriage_state", "")
    if state == "policy_preserved":
        return list(initial_policy)
    corrupted_ids = set(data.get("corrupted_policy_ids", []))
    if corrupted_ids:
        return [policy for policy in policy_pool if policy.policy_id in corrupted_ids]
    return []


@dataclass
class AgentResult:
    episode_id: str
    agent: str
    decision: Decision
    policy_ids: list[str] = field(default_factory=list)
    context_policy_ids: list[str] = field(default_factory=list)
    policy_source_used: str = ""
    policy_token_cost: int = 0
    notes: str = ""
    executed: bool = False
    violation: bool = False
    false_refusal: bool = False
    task_success: bool = False
    correct: bool = False
    policy_coverage: float | None = None
    irrelevant_policy_rate: float = 0.0
    retrieved_policy_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "agent": self.agent,
            "decision": self.decision,
            "policy_ids": self.policy_ids,
            "context_policy_ids": self.context_policy_ids,
            "policy_source_used": self.policy_source_used,
            "policy_token_cost": self.policy_token_cost,
            "notes": self.notes,
            "executed": self.executed,
            "violation": self.violation,
            "false_refusal": self.false_refusal,
            "task_success": self.task_success,
            "correct": self.correct,
            "policy_coverage": self.policy_coverage,
            "irrelevant_policy_rate": self.irrelevant_policy_rate,
            "retrieved_policy_count": self.retrieved_policy_count,
        }
