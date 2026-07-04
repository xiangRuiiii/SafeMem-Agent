from __future__ import annotations

from safemem.models import Episode, Policy


class PolicyStore:
    def __init__(self, policies: list[Policy]) -> None:
        self.policies = list(policies)
        self.by_id = {policy.policy_id: policy for policy in self.policies}

    @classmethod
    def from_episode(cls, episode: Episode) -> "PolicyStore":
        return cls(episode.initial_policy)

    def all(self) -> list[Policy]:
        return list(self.policies)

    def get_many(self, policy_ids: list[str]) -> list[Policy]:
        return [self.by_id[policy_id] for policy_id in policy_ids if policy_id in self.by_id]
