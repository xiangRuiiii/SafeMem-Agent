"""SafeMem 回归测试模块。"""

from __future__ import annotations

from safemem.models import Action, Decision, Policy
from safemem.policy.matcher import policy_applies

DECISION_RANK = {
    "allow": 0,
    "revise": 1,
    "ask_confirmation": 2,
    "block": 3,
}


def check_action(action: Action, policies: list[Policy]) -> tuple[Decision, list[str]]:
    matched = [policy for policy in policies if policy_applies(policy, action)]
    if not matched:
        return "allow", []

    decision: Decision = "allow"
    for policy in matched:
        if DECISION_RANK[policy.effect] > DECISION_RANK[decision]:
            decision = policy.effect
    return decision, [policy.policy_id for policy in matched]
