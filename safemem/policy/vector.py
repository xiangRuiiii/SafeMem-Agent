from __future__ import annotations

import hashlib
import math
from collections import defaultdict

from safemem.models import Action, Policy
from safemem.policy.text import build_action_embedding_text, build_policy_embedding_text, tokenize


SYNONYMS = {
    "external": ["outside", "noncompany", "thirdparty"],
    "outside": ["external", "noncompany", "thirdparty"],
    "recipient": ["target", "attendee"],
    "confidential": ["sensitive", "private"],
    "sensitive": ["confidential", "private"],
    "private": ["confidential", "sensitive"],
    "block": ["deny", "forbid", "prohibit"],
    "confirmation": ["confirm", "approval"],
    "confirm": ["confirmation", "approval"],
    "share": ["send", "transfer"],
    "delete": ["remove"],
}


class VectorRetriever:
    def __init__(self, top_k: int = 3, dimensions: int = 512) -> None:
        self.top_k = top_k
        self.dimensions = dimensions

    def select(self, action: Action, policies: list[Policy]) -> list[Policy]:
        if not policies or self.top_k <= 0:
            return []

        query_vector = self._vectorize(build_action_embedding_text(action))
        scored = []
        for policy in policies:
            doc_vector = self._vectorize(build_policy_embedding_text(policy))
            score = cosine(query_vector, doc_vector)
            scored.append((score, policy.priority, policy.policy_id, policy))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [policy for _, _, _, policy in scored[: self.top_k]]

    def _vectorize(self, text: str) -> dict[int, float]:
        values: dict[int, float] = defaultdict(float)
        for token in expand_tokens(tokenize(text)):
            index = stable_index(token, self.dimensions)
            values[index] += 1.0
        norm = math.sqrt(sum(value * value for value in values.values()))
        if norm == 0:
            return dict(values)
        return {index: value / norm for index, value in values.items()}


def expand_tokens(tokens: list[str]) -> list[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, []))
    return expanded


def stable_index(token: str, dimensions: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") % dimensions


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())
