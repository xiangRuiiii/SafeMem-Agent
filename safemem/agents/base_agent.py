from __future__ import annotations

import json
from typing import Any

from safemem.models import AgentResult, Episode


class BaseAgent:
    name = "base"

    def decide(self, episode: Episode) -> AgentResult:
        raise NotImplementedError

    def result(
        self,
        episode: Episode,
        decision: str,
        policy_ids: list[str] | None = None,
        policy_context: Any = None,
        notes: str = "",
    ) -> AgentResult:
        return AgentResult(
            episode_id=episode.episode_id,
            agent=self.name,
            decision=decision,
            policy_ids=policy_ids or [],
            policy_token_cost=count_tokens(policy_context),
            notes=notes,
        )


def count_tokens(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False)
    return len(text.replace("\n", " ").split())
