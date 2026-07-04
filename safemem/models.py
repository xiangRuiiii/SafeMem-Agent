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
    long_context: list[str]
    policy_carriage_state: str
    assembled_policy: list[str]
    risky_request: str
    candidate_action: Action
    expected_decision: Decision
    unsafe_if_executed: bool
    labels: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        return cls(
            episode_id=data["episode_id"],
            domain=data["domain"],
            task_goal=data.get("task_goal", ""),
            initial_policy=[Policy.from_dict(item) for item in data.get("initial_policy", [])],
            long_context=list(data.get("long_context", [])),
            policy_carriage_state=data.get("policy_carriage_state", ""),
            assembled_policy=list(data.get("assembled_policy", [])),
            risky_request=data.get("risky_request", ""),
            candidate_action=Action.from_dict(data["candidate_action"]),
            expected_decision=data.get("expected_decision", "allow"),
            unsafe_if_executed=bool(data.get("unsafe_if_executed", False)),
            labels=dict(data.get("labels", {})),
        )

    def required_policy_ids(self) -> list[str]:
        return list(self.labels.get("required_policy_ids", []))


@dataclass
class AgentResult:
    episode_id: str
    agent: str
    decision: Decision
    policy_ids: list[str] = field(default_factory=list)
    policy_token_cost: int = 0
    notes: str = ""
    executed: bool = False
    violation: bool = False
    false_refusal: bool = False
    task_success: bool = False
    correct: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "agent": self.agent,
            "decision": self.decision,
            "policy_ids": self.policy_ids,
            "policy_token_cost": self.policy_token_cost,
            "notes": self.notes,
            "executed": self.executed,
            "violation": self.violation,
            "false_refusal": self.false_refusal,
            "task_success": self.task_success,
            "correct": self.correct,
        }
