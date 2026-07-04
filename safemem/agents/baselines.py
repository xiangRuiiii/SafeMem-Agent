from __future__ import annotations

from safemem.agents.base_agent import BaseAgent
from safemem.models import AgentResult, Episode
from safemem.policy.checker import check_action


class NoPolicyAgent(BaseAgent):
    name = "no_policy"

    def decide(self, episode: Episode) -> AgentResult:
        return self.result(episode, "allow", notes="No policy context was provided.")


class SummaryPolicyAgent(BaseAgent):
    name = "summary_policy"

    def decide(self, episode: Episode) -> AgentResult:
        text = " ".join(episode.assembled_policy).lower()
        if not text:
            decision = "allow"
        elif _has_any(text, ["confirm", "confirmation", "approval", "确认", "批准", "同意"]):
            decision = "ask_confirmation"
        elif _has_any(text, ["do not", "never", "forbid", "prohibit", "禁止", "不得", "不允许"]):
            decision = "block"
        else:
            decision = "allow"
        return self.result(
            episode,
            decision,
            policy_context=episode.assembled_policy,
            notes="Decision from compressed policy text.",
        )


class AllPolicyAgent(BaseAgent):
    name = "all_policy"

    def decide(self, episode: Episode) -> AgentResult:
        decision, policy_ids = check_action(episode.candidate_action, episode.initial_policy)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            policy_context=[policy.to_dict() for policy in episode.initial_policy],
            notes="All active policies were replayed.",
        )


class ExactReplayAgent(BaseAgent):
    name = "exact_replay"

    def decide(self, episode: Episode) -> AgentResult:
        decision, policy_ids = check_action(episode.candidate_action, episode.initial_policy)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            policy_context=[policy.to_dict() for policy in episode.initial_policy],
            notes="Exact active policy replay plus preflight.",
        )


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)
