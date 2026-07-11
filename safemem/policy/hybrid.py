"""SafeMem 回归测试模块。"""

from __future__ import annotations

from safemem.models import Action, Policy
from safemem.policy.retriever import PolicyRetriever
from safemem.policy.vector import VectorRetriever


class HybridMsrRetriever:
    def __init__(
        self,
        recall_k: int = 5,
        max_policies: int = 4,
        min_score: float = 3.0,
        over_inclusion_penalty: float = 8.0,
        use_filter: bool = True,
        use_penalty: bool = True,
    ) -> None:
        self.recall_k = recall_k
        self.max_policies = max_policies
        self.min_score = min_score
        self.over_inclusion_penalty = over_inclusion_penalty
        self.use_filter = use_filter
        self.use_penalty = use_penalty
        self.vector = VectorRetriever(top_k=recall_k)
        self.msr = PolicyRetriever(max_policies=max_policies, min_score=min_score)

    def select(self, action: Action, policies: list[Policy]) -> list[Policy]:
        recalled = self.vector.select(action, policies)
        if not self.use_filter:
            return recalled[: self.max_policies]
        scored = []
        for policy in recalled:
            score = self.msr.score(policy, action)
            if self.use_penalty:
                score -= self.over_inclusion_score(policy)
            if score >= self.min_score:
                scored.append((score, policy.priority, policy.policy_id, policy))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [policy for _, _, _, policy in scored[: self.max_policies]]

    def over_inclusion_score(self, policy: Policy) -> float:
        score = 0.0
        object_value = policy.object.lower().strip()
        condition_value = policy.condition.lower().strip()
        text = policy.text.lower()

        if policy.source == "memory":
            score += self.over_inclusion_penalty * 0.5
        if object_value in {"", "any", "*"}:
            score += self.over_inclusion_penalty * 0.35
        if condition_value in {"", "any", "*"}:
            score += self.over_inclusion_penalty * 0.35
        if _looks_over_inclusive(text):
            score += self.over_inclusion_penalty * 0.25
        return score


def _looks_over_inclusive(text: str) -> bool:
    markers = [
        "never ",
        "do not perform any",
        "any file",
        "any email",
        "any calendar",
        "不得",
        "任何",
    ]
    return any(marker in text for marker in markers)
