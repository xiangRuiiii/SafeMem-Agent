from __future__ import annotations

import json
import re
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
        context_policy_ids: list[str] | None = None,
        policy_context: Any = None,
        policy_source_used: str = "",
        notes: str = "",
    ) -> AgentResult:
        if context_policy_ids is None:
            context_policy_ids = infer_policy_ids(policy_context)
        return AgentResult(
            episode_id=episode.episode_id,
            agent=self.name,
            decision=decision,
            policy_ids=policy_ids or [],
            context_policy_ids=context_policy_ids,
            policy_source_used=policy_source_used,
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
    return estimate_tokens(text)


def infer_policy_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    ids: list[str] = []
    for item in value:
        if isinstance(item, dict) and item.get("policy_id"):
            ids.append(str(item["policy_id"]))
    return ids


def estimate_tokens(text: str) -> int:
    cjk_chars = sum(1 for char in text if _is_cjk(char))
    latin_words = re.findall(r"[A-Za-z0-9_./@'-]+", text)
    return cjk_chars + len(latin_words)


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
    )
