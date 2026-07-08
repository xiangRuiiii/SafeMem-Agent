from __future__ import annotations

from collections import defaultdict

from safemem.models import AgentResult, Episode


def summarize(results: list[AgentResult]) -> list[dict[str, float | str | int]]:
    grouped: dict[str, list[AgentResult]] = defaultdict(list)
    for result in results:
        grouped[result.agent].append(result)

    return [_summary_row(agent, items) for agent, items in sorted(grouped.items())]


def summarize_by_state(
    results: list[AgentResult],
    episodes: list[Episode],
) -> list[dict[str, float | str | int]]:
    episode_by_id = {episode.episode_id: episode for episode in episodes}
    grouped: dict[tuple[str, str], list[AgentResult]] = defaultdict(list)
    for result in results:
        episode = episode_by_id[result.episode_id]
        grouped[(episode.policy_carriage_state, result.agent)].append(result)

    rows: list[dict[str, float | str | int]] = []
    for (state, agent), items in sorted(grouped.items()):
        row = _summary_row(agent, items)
        row = {"policy_state": state, **row}
        rows.append(row)
    return rows


def summarize_by_case(
    results: list[AgentResult],
    episodes: list[Episode],
) -> list[dict[str, float | str | int]]:
    episode_by_id = {episode.episode_id: episode for episode in episodes}
    grouped: dict[tuple[str, str], list[AgentResult]] = defaultdict(list)
    for result in results:
        episode = episode_by_id[result.episode_id]
        case_type = "safe" if episode.is_safe_case else "risky"
        grouped[(case_type, result.agent)].append(result)

    rows: list[dict[str, float | str | int]] = []
    for (case_type, agent), items in sorted(grouped.items()):
        row = _summary_row(agent, items)
        row = {"case_type": case_type, **row}
        rows.append(row)
    return rows


def _summary_row(agent: str, items: list[AgentResult]) -> dict[str, float | str | int]:
    total = len(items)
    return {
        "agent": agent,
        "agent_group": _agent_group(items),
        "episodes": total,
        "accuracy": _rate(item.correct for item in items),
        "executed_violation_rate": _rate(item.violation for item in items),
        "false_refusal_rate": _rate(item.false_refusal for item in items),
        "task_success_rate": _rate(item.task_success for item in items),
        "ask_confirmation_rate": _rate(item.decision == "ask_confirmation" for item in items),
        "avg_policy_token_cost": round(sum(item.policy_token_cost for item in items) / total, 2),
        "avg_llm_total_tokens": round(sum(item.llm_total_tokens for item in items) / total, 2),
        "avg_policy_coverage": _avg_optional(item.policy_coverage for item in items),
        "avg_irrelevant_policy_rate": round(sum(item.irrelevant_policy_rate for item in items) / total, 4),
        "avg_retrieved_policies": round(sum(item.retrieved_policy_count for item in items) / total, 2),
    }


def _rate(values: object) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(1 for item in items if item) / len(items), 4)


def _avg_optional(values: object) -> float | str:
    items = [item for item in values if item is not None]
    if not items:
        return "NA"
    return round(sum(items) / len(items), 4)


def _agent_group(items: list[AgentResult]) -> str:
    for item in items:
        if item.agent_group:
            return item.agent_group
    return ""
