from __future__ import annotations

from safemem.agents.base_agent import BaseAgent
from safemem.models import AgentResult, Episode
from safemem.policy.checker import check_action
from safemem.policy.retriever import PolicyRetriever


class MsrAgent(BaseAgent):
    name = "msr"

    def __init__(self, retriever: PolicyRetriever | None = None) -> None:
        self.retriever = retriever or PolicyRetriever()

    def decide(self, episode: Episode) -> AgentResult:
        policies = episode.policy_pool
        selected = self.retriever.select(episode.candidate_action, policies)
        decision, policy_ids = check_action(episode.candidate_action, selected)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            context_policy_ids=[policy.policy_id for policy in selected],
            policy_context=[policy.to_dict() for policy in selected],
            notes="Minimal sufficient policy retrieval from carried policy_pool plus preflight.",
        )
