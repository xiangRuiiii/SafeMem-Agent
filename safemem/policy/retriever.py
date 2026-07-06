from __future__ import annotations

from safemem.models import Action, Policy
from safemem.policy.matcher import (
    action_has_external_target,
    condition_matches,
    object_matches,
    severity_value,
    tool_matches,
)


class PolicyRetriever:
    def __init__(self, max_policies: int = 4, min_score: float = 3.0) -> None:
        self.max_policies = max_policies
        self.min_score = min_score

    def select(self, action: Action, policies: list[Policy]) -> list[Policy]:
        scored = [(self.score(policy, action), policy) for policy in policies]
        scored = [(score, policy) for score, policy in scored if score >= self.min_score]
        scored.sort(key=lambda item: (item[0], item[1].priority), reverse=True)
        return [policy for _, policy in scored[: self.max_policies]]

    def score(self, policy: Policy, action: Action) -> float:
        score = 0.0
        if tool_matches(policy, action):
            score += 3.0
        if object_matches(policy, action):
            score += 3.0
        if condition_matches(policy, action):
            score += 2.0
        if self._risk_matches(policy, action):
            score += 1.0
        score += 0.5 * severity_value(policy)
        if policy.source in {"system", "user"}:
            score += 0.5
        if not tool_matches(policy, action):
            score -= 7.0
        if not object_matches(policy, action):
            score -= 6.0
        return score

    def _risk_matches(self, policy: Policy, action: Action) -> bool:
        text = f"{policy.text} {policy.object} {policy.condition}".lower()
        if action.tool in {"send_email", "share_file", "share_calendar"}:
            return "external" in text or action_has_external_target(action)
        if action.tool in {"delete_file", "delete_email"}:
            return "delete" in text or "irreversible" in text
        return action.tool in text
