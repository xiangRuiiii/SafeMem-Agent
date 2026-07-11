"""SafeMem 回归测试模块。"""

from __future__ import annotations

from safemem.agents.base_agent import BaseAgent
from safemem.models import AgentResult, Episode
from safemem.policy.checker import check_action
from safemem.policy.retriever import PolicyRetriever


class MsrAgent(BaseAgent):
    name = "msr_clean"
    policy_source = "canonical_policy_registry"

    def __init__(self, retriever: PolicyRetriever | None = None) -> None:
        self.retriever = retriever or PolicyRetriever()

    def decide(self, episode: Episode) -> AgentResult:
        policies = list(getattr(episode, self.policy_source))
        selected = self.retriever.select(episode.candidate_action, policies)
        decision, policy_ids = check_action(episode.candidate_action, selected)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            context_policy_ids=[policy.policy_id for policy in selected],
            policy_context=[policy.to_dict() for policy in selected],
            policy_source_used=self.policy_source,
            notes=f"Minimal sufficient policy retrieval from {self.policy_source} plus preflight.",
        )


class MsrNoisyAgent(MsrAgent):
    name = "msr_noisy"
    policy_source = "noisy_policy_pool"
