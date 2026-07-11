"""真实 Dense Embedding 检索器，作为 Hash-vector 之外的可选实验对照。"""

from __future__ import annotations

import math

from safemem.llm_client import EmbeddingClient
from safemem.models import Action, Policy
from safemem.policy.text import build_action_embedding_text, build_policy_embedding_text


class DenseRetriever:
    """通过外部 embedding endpoint 计算语义相似度；调用方负责缓存与成本控制。"""

    def __init__(self, client: EmbeddingClient, model: str, top_k: int = 8) -> None:
        self.client = client
        self.model = model
        self.top_k = top_k

    def select(self, action: Action, policies: list[Policy]) -> list[Policy]:
        if not policies or self.top_k <= 0:
            return []
        texts = [build_action_embedding_text(action)] + [build_policy_embedding_text(policy) for policy in policies]
        vectors = self.client.embed(texts, model=self.model)
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding endpoint returned an unexpected vector count.")
        query, policy_vectors = vectors[0], vectors[1:]
        scored = [(_cosine(query, vector), policy.priority, policy.policy_id, policy) for policy, vector in zip(policies, policy_vectors)]
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [policy for _, _, _, policy in scored[: self.top_k]]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
