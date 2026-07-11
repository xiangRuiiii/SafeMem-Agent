"""汇总多模型 LLM 结果，并对同一 episode 网格做可复现的配对差值统计。"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.data import read_jsonl, write_csv


METRICS: dict[str, Callable[[dict[str, Any]], int]] = {
    "accuracy": lambda row: int(bool(row.get("correct"))),
    "executed_violation_rate": lambda row: int(bool(row.get("violation"))),
    "false_refusal_rate": lambda row: int(bool(row.get("false_refusal"))),
    "task_success_rate": lambda row: int(bool(row.get("task_success"))),
}


def main() -> None:
    args = parse_args()
    paths = [resolve_path(value) for value in split_values(args.inputs)]
    profiles = split_values(args.profiles)
    if len(paths) != len(profiles):
        raise SystemExit("--inputs and --profiles must contain the same number of comma-separated values.")

    methods = split_values(args.methods)
    groups = {profile: load_rows(path, profile, methods) for path, profile in zip(paths, profiles)}
    selected_methods = validate_grids(groups, methods, args.expected_episodes)
    summary = build_summary(groups, selected_methods)
    deltas = build_paired_deltas(
        groups,
        selected_methods,
        args.reference,
        args.bootstrap_samples,
        args.seed,
    )

    write_csv(ROOT / "outputs" / "tables" / f"{args.tag}_model_summary.csv", summary)
    write_csv(ROOT / "outputs" / "tables" / f"{args.tag}_paired_deltas.csv", deltas)
    print(f"profiles={len(groups)} methods={len(selected_methods)} episodes={args.expected_episodes or 'inferred'}")
    for row in summary:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare matched SafeMem LLM results across model profiles.")
    parser.add_argument("--inputs", required=True, help="Comma-separated JSONL result logs from run_llm_eval.py.")
    parser.add_argument("--profiles", required=True, help="Comma-separated profile names matching --inputs order.")
    parser.add_argument("--methods", required=True, help="Comma-separated AgentResult agent names to compare.")
    parser.add_argument("--reference", default="llm_msr_noisy", help="Reference agent for paired deltas.")
    parser.add_argument("--expected-episodes", type=int, default=0, help="Require this many episodes for every profile/method.")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--tag", default="multimodel")
    return parser.parse_args()


def split_values(value: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one comma-separated value is required.")
    return values


def load_rows(path: Path, profile: str, methods: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing result log for profile {profile}: {path}")
    allowed = set(methods)
    rows = [dict(row, model_profile=profile) for row in read_jsonl(path) if row.get("agent") in allowed]
    if not rows:
        raise RuntimeError(f"No requested methods found for profile {profile}: {path}")
    return rows


def validate_grids(
    groups: dict[str, list[dict[str, Any]]],
    requested_methods: list[str],
    expected_episodes: int,
) -> list[str]:
    """确保每个 profile 都包含同一批 episode 与方法，避免不完整运行污染比较。"""

    expected_methods = set(requested_methods)
    reference_grid: set[tuple[str, str]] | None = None
    for profile, rows in groups.items():
        index: dict[tuple[str, str], dict[str, Any]] = {}
        by_method: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            key = (str(row.get("episode_id", "")), str(row.get("agent", "")))
            if not all(key):
                raise RuntimeError(f"Profile {profile} has a result without episode_id or agent.")
            if key in index:
                raise RuntimeError(f"Profile {profile} has a duplicate result: {key}")
            index[key] = row
            by_method[key[1]].add(key[0])

        missing = expected_methods - set(by_method)
        if missing:
            raise RuntimeError(f"Profile {profile} is missing methods: {sorted(missing)}")
        episode_sets = [by_method[method] for method in requested_methods]
        if any(episode_ids != episode_sets[0] for episode_ids in episode_sets[1:]):
            raise RuntimeError(f"Profile {profile} has different episode sets across methods.")
        if expected_episodes and len(episode_sets[0]) != expected_episodes:
            raise RuntimeError(
                f"Profile {profile} has {len(episode_sets[0])} episodes per method, expected {expected_episodes}."
            )

        grid = set(index)
        if reference_grid is None:
            reference_grid = grid
        elif grid != reference_grid:
            raise RuntimeError(f"Profile {profile} does not share the same episode-method grid as the first profile.")
    return requested_methods


def build_summary(groups: dict[str, list[dict[str, Any]]], methods: list[str]) -> list[dict[str, Any]]:
    output = []
    for profile, rows in groups.items():
        by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_method[str(row["agent"])].append(row)
        for method in methods:
            items = by_method[method]
            total = len(items)
            output.append(
                {
                    "model_profile": profile,
                    "llm_model": single_value(items, "llm_model"),
                    "agent": method,
                    "agent_group": single_value(items, "agent_group"),
                    "episodes": total,
                    **{name: rate(metric(item) for item in items) for name, metric in METRICS.items()},
                    "ask_confirmation_rate": rate(item.get("decision") == "ask_confirmation" for item in items),
                    "avg_policy_token_cost": average(item.get("policy_token_cost", 0) for item in items),
                    "avg_llm_total_tokens": average(item.get("llm_total_tokens", 0) for item in items),
                }
            )
    return output


def build_paired_deltas(
    groups: dict[str, list[dict[str, Any]]],
    methods: list[str],
    reference: str,
    bootstrap_samples: int,
    seed: int,
) -> list[dict[str, Any]]:
    if reference not in methods:
        raise ValueError(f"Reference {reference!r} must appear in --methods.")
    output = []
    for profile, rows in groups.items():
        by_method = index_by_method(rows)
        reference_rows = by_method[reference]
        for method in methods:
            if method == reference:
                continue
            candidate_rows = by_method[method]
            episode_ids = sorted(reference_rows)
            differences = {
                metric_name: [metric(candidate_rows[episode_id]) - metric(reference_rows[episode_id]) for episode_id in episode_ids]
                for metric_name, metric in METRICS.items()
            }
            row: dict[str, Any] = {
                "model_profile": profile,
                "llm_model": single_value(list(candidate_rows.values()), "llm_model"),
                "agent": method,
                "reference_agent": reference,
                "episodes": len(episode_ids),
            }
            for metric_name, values in differences.items():
                point, low, high = bootstrap_mean_ci(values, bootstrap_samples, stable_seed(seed, profile, method, metric_name))
                row[f"{metric_name}_delta"] = point
                row[f"{metric_name}_delta_ci_low"] = low
                row[f"{metric_name}_delta_ci_high"] = high
            output.append(row)
    return output


def index_by_method(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    indexed: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        indexed[str(row["agent"])][str(row["episode_id"])] = row
    return indexed


def bootstrap_mean_ci(values: list[int], samples: int, seed: int) -> tuple[float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0)
    point = round(sum(values) / len(values), 4)
    if samples <= 0 or len(values) == 1:
        return (point, point, point)
    rng = random.Random(seed)
    size = len(values)
    estimates = sorted(sum(values[rng.randrange(size)] for _ in range(size)) / size for _ in range(samples))
    low = estimates[int((len(estimates) - 1) * 0.025)]
    high = estimates[int((len(estimates) - 1) * 0.975)]
    return (point, round(low, 4), round(high, 4))


def stable_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return seed + int(digest[:8], 16)


def single_value(rows: list[dict[str, Any]], key: str) -> str:
    values = sorted({str(row.get(key, "")) for row in rows if row.get(key, "")})
    return values[0] if len(values) == 1 else ";".join(values)


def average(values: Any) -> float:
    items = [float(value or 0) for value in values]
    return round(sum(items) / len(items), 2) if items else 0.0


def rate(values: Any) -> float:
    items = list(values)
    return round(sum(bool(item) for item in items) / len(items), 4) if items else 0.0


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
