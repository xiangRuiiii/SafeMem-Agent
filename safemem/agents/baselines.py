from __future__ import annotations

from safemem.agents.base_agent import BaseAgent
from safemem.models import AgentResult, Episode
from safemem.policy.checker import check_action
from safemem.policy.policy_store import PolicyStore


class NoPolicyAgent(BaseAgent):
    name = "no_policy"

    def decide(self, episode: Episode) -> AgentResult:
        return self.result(episode, "allow", policy_source_used="none", notes="No policy context was provided.")


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
            policy_source_used="assembled_policy",
            notes="Decision from compressed policy text.",
        )


class AllPolicyCleanAgent(BaseAgent):
    name = "all_policy_clean"

    def decide(self, episode: Episode) -> AgentResult:
        policies = list(episode.canonical_policy_registry)
        decision, policy_ids = check_action(episode.candidate_action, policies)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            policy_context=[policy.to_dict() for policy in policies],
            policy_source_used="canonical_policy_registry",
            notes="All canonical policies were replayed.",
        )


class AllPolicyNoisyAgent(BaseAgent):
    name = "all_policy_noisy"

    def decide(self, episode: Episode) -> AgentResult:
        policies = PolicyStore.from_episode(episode).all()
        decision, policy_ids = check_action(episode.candidate_action, policies)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            policy_context=[policy.to_dict() for policy in policies],
            policy_source_used="noisy_policy_pool",
            notes="All noisy candidate policies were replayed.",
        )


class CarriedPolicyAgent(BaseAgent):
    name = "carried_policy"

    def decide(self, episode: Episode) -> AgentResult:
        policies = list(episode.carried_policy)
        decision, policy_ids = check_action(episode.candidate_action, policies)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            policy_context=[policy.to_dict() for policy in policies],
            policy_source_used="carried_policy",
            notes="Exact replay of carried active policies plus preflight.",
        )


class OracleMinimalAgent(BaseAgent):
    name = "oracle_minimal"

    def decide(self, episode: Episode) -> AgentResult:
        ground_truth = episode.ground_truth_policies
        by_id = {policy.policy_id: policy for policy in ground_truth}
        required_ids = episode.required_policy_ids()
        policies = [by_id[policy_id] for policy_id in required_ids if policy_id in by_id]
        decision, policy_ids = check_action(episode.candidate_action, policies)
        return self.result(
            episode,
            decision,
            policy_ids=policy_ids,
            context_policy_ids=[policy.policy_id for policy in policies],
            policy_context=[policy.to_dict() for policy in policies],
            policy_source_used="ground_truth_policies",
            notes="Oracle uses only ground_truth_policies.",
        )


AllPolicyAgent = AllPolicyCleanAgent
ExactReplayAgent = CarriedPolicyAgent


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)
