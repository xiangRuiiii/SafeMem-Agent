"""SafeMem 回归测试模块。"""

from __future__ import annotations

import math
from collections import Counter

from safemem.models import Action, Policy
from safemem.policy.text import build_action_query, build_policy_doc, tokenize


class BM25Retriever:
    def __init__(self, top_k: int = 3, k1: float = 1.5, b: float = 0.75) -> None:
        self.top_k = top_k
        self.k1 = k1
        self.b = b

    def select(self, action: Action, policies: list[Policy]) -> list[Policy]:
        if not policies or self.top_k <= 0:
            return []

        query_tokens = tokenize(build_action_query(action))
        doc_tokens = [tokenize(build_policy_doc(policy)) for policy in policies]
        doc_counts = [Counter(tokens) for tokens in doc_tokens]
        doc_freq = Counter(token for tokens in doc_tokens for token in set(tokens))
        avg_len = sum(len(tokens) for tokens in doc_tokens) / len(doc_tokens)

        scored = []
        for policy, counts, length in zip(policies, doc_counts, [len(tokens) for tokens in doc_tokens]):
            score = self._score(query_tokens, counts, doc_freq, length, avg_len, len(policies))
            scored.append((score, policy.priority, policy.policy_id, policy))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [policy for _, _, _, policy in scored[: self.top_k]]

    def _score(
        self,
        query_tokens: list[str],
        counts: Counter[str],
        doc_freq: Counter[str],
        doc_len: int,
        avg_len: float,
        total_docs: int,
    ) -> float:
        score = 0.0
        for token in query_tokens:
            freq = counts.get(token, 0)
            if freq == 0:
                continue
            df = doc_freq.get(token, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denom = freq + self.k1 * (1 - self.b + self.b * doc_len / max(avg_len, 1e-9))
            score += idf * freq * (self.k1 + 1) / denom
        return score
