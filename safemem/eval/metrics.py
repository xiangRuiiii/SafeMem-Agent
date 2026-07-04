from __future__ import annotations

from collections import defaultdict

from safemem.models import AgentResult


def summarize(results: list[AgentResult]) -> list[dict[str, float | str | int]]:
    grouped: dict[str, list[AgentResult]] = defaultdict(list)
    for result in results:
        grouped[result.agent].append(result)

    rows: list[dict[str, float | str | int]] = []
    for agent, items in sorted(grouped.items()):
        total = len(items)
        rows.append(
            {
                "agent": agent,
                "episodes": total,
                "accuracy": _rate(item.correct for item in items),
                "executed_violation_rate": _rate(item.violation for item in items),
                "false_refusal_rate": _rate(item.false_refusal for item in items),
                "task_success_rate": _rate(item.task_success for item in items),
                "avg_policy_token_cost": round(
                    sum(item.policy_token_cost for item in items) / total,
                    2,
                ),
            }
        )
    return rows


def _rate(values: object) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(1 for item in items if item) / len(items), 4)
