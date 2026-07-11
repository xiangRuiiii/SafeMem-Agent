"""把 V-MSR 证明结论作为动作执行前的最低安全门槛。"""

from __future__ import annotations

from safemem.models import Decision
from safemem.policy.select import DECISION_RANK


def apply_guard(llm_decision: Decision, certificate_decision: Decision) -> tuple[Decision, bool]:
    """只提升过于宽松的执行决定；`revise` 表示不执行，因此保留。"""

    if llm_decision == "revise":
        return llm_decision, False
    if DECISION_RANK[llm_decision] >= DECISION_RANK[certificate_decision]:
        return llm_decision, False
    return certificate_decision, True
