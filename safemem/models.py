"""SafeMem 回归测试模块。"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Literal

Decision = Literal["allow", "block", "ask_confirmation", "revise"]


@dataclass
class Policy:
    """一条可追溯的策略记录，兼容自然语言策略和结构化策略。"""

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
    issuer: str = ""
    authority: int = 0
    version: int = 1
    supersedes: list[str] = field(default_factory=list)
    active: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Policy":
        source = data.get("source", "user")
        return cls(
            policy_id=data["policy_id"],
            text=data.get("text") or data.get("evidence", ""),
            source=source,
            scope=data.get("scope", ""),
            actor=data.get("actor", "agent"),
            tool=data.get("tool", data.get("action", "")),
            action=data.get("action", data.get("tool", "")),
            object=data.get("object", ""),
            condition=data.get("condition", ""),
            effect=data.get("effect", "allow"),
            severity=data.get("severity", "low"),
            priority=int(data.get("priority", 0)),
            issuer=data.get("issuer", source),
            authority=int(data.get("authority", _default_authority(source))),
            version=int(data.get("version", 1)),
            supersedes=[str(item) for item in data.get("supersedes", [])],
            active=bool(data.get("active", True)),
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
            "issuer": self.issuer,
            "authority": self.authority,
            "version": self.version,
            "supersedes": self.supersedes,
            "active": self.active,
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
    """一次动作安全评估所需的输入、策略池和离线评测标注。"""

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
    challenge_type: str = ""
    certificate_policy_ids: list[str] = field(default_factory=list)
    conflict_policy_ids: list[str] = field(default_factory=list)
    risk_evidence_keys: list[str] = field(default_factory=list)

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
            challenge_type=data.get("challenge_type", ""),
            certificate_policy_ids=list(data.get("certificate_policy_ids", [])),
            conflict_policy_ids=list(data.get("conflict_policy_ids", [])),
            risk_evidence_keys=list(data.get("risk_evidence_keys", [])),
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


def _default_authority(source: str) -> int:
    """为旧数据提供稳定的来源权威默认值，避免破坏已有 episode。"""

    return {
        "system": 4,
        "organization": 3,
        "user": 2,
        "memory": 1,
    }.get(source.lower(), 1)


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
    """记录 Agent 决策、策略上下文和 V-MSR 验证证据。"""

    episode_id: str
    agent: str
    decision: Decision
    agent_group: str = ""
    policy_ids: list[str] = field(default_factory=list)
    context_policy_ids: list[str] = field(default_factory=list)
    policy_source_used: str = ""
    policy_token_cost: int = 0
    llm_model: str = ""
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_total_tokens: int = 0
    notes: str = ""
    executed: bool = False
    violation: bool = False
    false_refusal: bool = False
    task_success: bool = False
    correct: bool = False
    policy_coverage: float | None = None
    irrelevant_policy_rate: float = 0.0
    retrieved_policy_count: int = 0
    verification_mode: str = ""
    certificate_policy_ids: list[str] = field(default_factory=list)
    certificate_decision: str = ""
    certificate_internal_validity: bool | None = None
    certificate_validity: bool | None = None
    certificate_minimality: bool | None = None
    certificate_oracle_match: bool | None = None
    decision_stability: bool | None = None
    unknown_escalated: bool = False
    conflict_resolved: bool | None = None
    guard_override: bool = False
    verification_trace: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentResult":
        names = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in names}
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "agent": self.agent,
            "agent_group": self.agent_group,
            "decision": self.decision,
            "policy_ids": self.policy_ids,
            "context_policy_ids": self.context_policy_ids,
            "policy_source_used": self.policy_source_used,
            "policy_token_cost": self.policy_token_cost,
            "llm_model": self.llm_model,
            "llm_prompt_tokens": self.llm_prompt_tokens,
            "llm_completion_tokens": self.llm_completion_tokens,
            "llm_total_tokens": self.llm_total_tokens,
            "notes": self.notes,
            "executed": self.executed,
            "violation": self.violation,
            "false_refusal": self.false_refusal,
            "task_success": self.task_success,
            "correct": self.correct,
            "policy_coverage": self.policy_coverage,
            "irrelevant_policy_rate": self.irrelevant_policy_rate,
            "retrieved_policy_count": self.retrieved_policy_count,
            "verification_mode": self.verification_mode,
            "certificate_policy_ids": self.certificate_policy_ids,
            "certificate_decision": self.certificate_decision,
            "certificate_internal_validity": self.certificate_internal_validity,
            "certificate_validity": self.certificate_validity,
            "certificate_minimality": self.certificate_minimality,
            "certificate_oracle_match": self.certificate_oracle_match,
            "decision_stability": self.decision_stability,
            "unknown_escalated": self.unknown_escalated,
            "conflict_resolved": self.conflict_resolved,
            "guard_override": self.guard_override,
            "verification_trace": self.verification_trace,
        }
