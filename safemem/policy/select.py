"""从已验证策略中解析冲突并构造最小、稳定的安全证明集合。"""

from __future__ import annotations

from dataclasses import dataclass, field

from safemem.models import Decision
from safemem.policy.verify import PolicyCheck, PolicyRule


DECISION_RANK: dict[str, int] = {
    "allow": 0,
    "revise": 1,
    "ask_confirmation": 2,
    "block": 3,
}


@dataclass
class PolicySelection:
    """V-MSR 输出的最小策略集合及可审计验证状态。"""

    policies: list[PolicyRule]
    decision: Decision
    checks: list[PolicyCheck]
    unresolved_policy_ids: list[str] = field(default_factory=list)
    unknown_policy_ids: list[str] = field(default_factory=list)
    excluded_reasons: dict[str, str] = field(default_factory=dict)
    minimal: bool = True
    stable: bool = True
    unknown_escalated: bool = False
    conflict_resolved: bool | None = None


def select_minimal(checks: list[PolicyCheck]) -> PolicySelection:
    """先消解可证明的冲突，再以留一法删除不影响结论的冗余策略。"""

    active = [item for item in checks if item.status == "entailed"]
    unknown = [item for item in checks if item.status == "unknown" and item.rule.effect != "allow"]
    winners, unresolved, excluded = _resolve_conflicts(active)

    if unresolved:
        # 同权威冲突不能靠“更保守”偷偷解决，必须交给人或上层确认。
        selected = _minimal_rules(winners, "ask_confirmation")
        return PolicySelection(
            policies=selected,
            decision="ask_confirmation",
            checks=checks,
            unresolved_policy_ids=sorted(unresolved),
            excluded_reasons=excluded,
            minimal=_is_minimal(selected, "ask_confirmation"),
            stable=False,
            conflict_resolved=False,
        )

    base_decision = _decision_for(winners)
    if unknown:
        # 缺少动作证据时，任何潜在限制策略都将执行下限提升为确认。
        unknown_decision = (
            base_decision
            if DECISION_RANK.get(base_decision, 0) >= DECISION_RANK["ask_confirmation"]
            else "ask_confirmation"
        )
        selected = _minimal_rules(winners, unknown_decision)
        return PolicySelection(
            policies=selected,
            decision=unknown_decision,
            checks=checks,
            unknown_policy_ids=sorted(item.rule.policy_id for item in unknown),
            excluded_reasons=excluded,
            minimal=_is_minimal(selected, "ask_confirmation"),
            stable=False,
            unknown_escalated=True,
            conflict_resolved=True if active else None,
        )

    selected = _minimal_rules(winners, base_decision)
    return PolicySelection(
        policies=selected,
        decision=base_decision,
        checks=checks,
        excluded_reasons=excluded,
        minimal=_is_minimal(selected, base_decision),
        stable=True,
        conflict_resolved=True if active else None,
    )


def _resolve_conflicts(active: list[PolicyCheck]) -> tuple[list[PolicyRule], set[str], dict[str, str]]:
    rules = [item.rule for item in active]
    removed: set[str] = set()
    unresolved: set[str] = set()
    excluded: dict[str, str] = {}
    for index, left in enumerate(rules):
        for right in rules[index + 1 :]:
            if left.policy_id in removed or right.policy_id in removed:
                continue
            if left.effect == right.effect:
                # 相同义务的重复策略先按可信 provenance 去重，避免最小化阶段留下低权威副本。
                if _same_obligation(left, right):
                    if _dominates(left, right):
                        removed.add(right.policy_id)
                        excluded[right.policy_id] = f"duplicate_of:{left.policy_id}"
                    elif _dominates(right, left):
                        removed.add(left.policy_id)
                        excluded[left.policy_id] = f"duplicate_of:{right.policy_id}"
                continue
            if not _may_conflict(left, right):
                continue
            if _dominates(left, right):
                removed.add(right.policy_id)
                excluded[right.policy_id] = f"dominated_by:{left.policy_id}"
            elif _dominates(right, left):
                removed.add(left.policy_id)
                excluded[left.policy_id] = f"dominated_by:{right.policy_id}"
            else:
                unresolved.update({left.policy_id, right.policy_id})
    winners = [rule for rule in rules if rule.policy_id not in removed]
    return winners, unresolved, excluded


def _may_conflict(left: PolicyRule, right: PolicyRule) -> bool:
    """只比较作用域重叠的相反效果；不同安全义务应共同保留在证明中。"""

    # 两个不同的非空限制条件代表复合义务；空条件或 allow 才可能与另一条规则真正冲突。
    if (
        "allow" not in {left.effect, right.effect}
        and left.condition
        and right.condition
        and left.condition != right.condition
    ):
        return False
    if "any" in {left.object, right.object} or "*" in {left.object, right.object}:
        return True
    return left.object == right.object and left.condition == right.condition


def _same_obligation(left: PolicyRule, right: PolicyRule) -> bool:
    return (left.tool, left.object, left.condition) == (right.tool, right.object, right.condition)


def _dominates(left: PolicyRule, right: PolicyRule) -> bool:
    """按照 authority、具体性、版本和 priority 判断一条策略是否可覆盖冲突项。"""

    if right.policy_id in left.supersedes:
        return True
    if left.policy_id in right.supersedes:
        return False
    left_key = (left.authority, _specificity(left), left.version, left.priority)
    right_key = (right.authority, _specificity(right), right.version, right.priority)
    return left_key > right_key


def _specificity(rule: PolicyRule) -> int:
    score = 0
    if rule.tool and rule.tool not in {"any", "*"}:
        score += 1
    if rule.object and rule.object not in {"any", "*"}:
        score += 1
    if rule.condition:
        score += len([part for part in rule.condition.split(" and ") if part.strip()])
    return score


def _minimal_rules(rules: list[PolicyRule], decision: Decision) -> list[PolicyRule]:
    selected = list(rules)
    index = 0
    while index < len(selected):
        trial = selected[:index] + selected[index + 1 :]
        # 不同对象/条件代表不同安全义务；即使最终都是 block，也不能随意丢失证明覆盖。
        if _decision_for(trial) == decision and _obligations(trial) == _obligations(selected):
            selected = trial
            continue
        index += 1
    return selected


def _is_minimal(rules: list[PolicyRule], decision: Decision) -> bool:
    return all(
        _decision_for(rules[:index] + rules[index + 1 :]) != decision
        or _obligations(rules[:index] + rules[index + 1 :]) != _obligations(rules)
        for index in range(len(rules))
    )


def _obligations(rules: list[PolicyRule]) -> set[tuple[str, str]]:
    return {(rule.object, rule.condition) for rule in rules if rule.object or rule.condition}


def _decision_for(rules: list[PolicyRule]) -> Decision:
    if not rules:
        return "allow"
    best = max(rules, key=lambda item: DECISION_RANK.get(item.effect, 1))
    return best.effect if best.effect in DECISION_RANK else "ask_confirmation"  # type: ignore[return-value]
