from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.agents.base_agent import count_tokens
from safemem.agents.llm_agent import (
    LLM_METHOD_GROUPS,
    parse_topk_method,
    policy_context_for_method,
)
from safemem.data import load_episodes, write_csv, write_json
from safemem.models import Episode


DEFAULT_METHODS = [
    "bm25_clean_top3",
    "bm25_noisy_top3",
    "embedding_clean_top3",
    "embedding_noisy_top3",
    "msr_clean",
    "msr_noisy",
    "hybrid_msr_clean",
    "hybrid_msr_noisy",
    "oracle_minimal",
]


def main() -> None:
    args = parse_args()
    episode_path = resolve_path(args.episodes)
    episodes = load_episodes(episode_path)
    if args.episode_ids:
        selected_ids = {item.strip() for item in args.episode_ids.split(",") if item.strip()}
        episodes = [episode for episode in episodes if episode.episode_id in selected_ids]
    if args.limit:
        episodes = episodes[: args.limit]

    methods = methods_for_set(args.method_set) if args.method_set else parse_methods(args.methods)
    tag = args.tag or f"{episode_path.stem}_retrieval"

    rows = []
    for episode in episodes:
        for method in methods:
            context = policy_context_for_method(episode, method)
            rows.append(retrieval_row(episode, method, context))

    summary = summarize(rows)
    by_state = summarize_by_state(rows)

    write_json(ROOT / "outputs" / "logs" / f"{tag}_retrieval_results.json", rows)
    write_csv(ROOT / "outputs" / "tables" / f"{tag}_retrieval_summary.csv", summary)
    write_csv(ROOT / "outputs" / "tables" / f"{tag}_retrieval_by_state.csv", by_state)

    for row in summary:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrieval-only SafeMem policy selection experiments.")
    parser.add_argument(
        "--episodes",
        default="data/episodes/mvp_plus_90_en.jsonl",
        help="Episode JSONL path, relative to repository root by default.",
    )
    parser.add_argument("--tag", default="", help="Output filename tag.")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS), help="Comma-separated retrieval methods.")
    parser.add_argument(
        "--method-set",
        default="",
        choices=["retrieval_top3", "retrieval_all", "hybrid"],
        help="Named retrieval method set. Overrides --methods when set.",
    )
    parser.add_argument("--episode-ids", default="", help="Optional comma-separated episode IDs to run.")
    parser.add_argument("--limit", type=int, default=0, help="Optional number of episodes from the start of the file.")
    return parser.parse_args()


def parse_methods(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def methods_for_set(name: str) -> list[str]:
    if name == "retrieval_top3":
        return list(DEFAULT_METHODS)
    if name == "retrieval_all":
        methods: list[str] = []
        for family in ("bm25", "embedding"):
            for source in ("clean", "noisy"):
                for top_k in (1, 3, 5):
                    methods.append(f"{family}_{source}_top{top_k}")
        methods.extend(["msr_clean", "msr_noisy", "oracle_minimal"])
        return methods
    if name == "hybrid":
        return [
            "embedding_noisy_top3",
            "msr_noisy",
            "hybrid_msr_noisy",
            "embedding_clean_top3",
            "msr_clean",
            "hybrid_msr_clean",
            "oracle_minimal",
        ]
    raise SystemExit(f"Unsupported method set: {name}")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def retrieval_row(episode: Episode, method: str, context: Any) -> dict[str, Any]:
    retrieved = set(context.policy_ids)
    required = set(episode.required_policy_ids())
    policy_payload = context.prompt_payload()
    return {
        "episode_id": episode.episode_id,
        "domain": episode.domain,
        "policy_state": episode.policy_carriage_state,
        "case_type": "safe" if episode.is_safe_case else "risky",
        "method": method,
        "agent": f"llm_{method}",
        "agent_group": LLM_METHOD_GROUPS.get(method, ""),
        "source": context.source,
        "top_k": top_k_for_method(method),
        "policy_coverage": coverage(required, retrieved),
        "irrelevant_policy_rate": irrelevant_rate(required, retrieved),
        "retrieved_policy_count": len(retrieved),
        "policy_token_cost": count_tokens(policy_payload),
        "context_policy_ids": context.policy_ids,
        "required_policy_ids": episode.required_policy_ids(),
    }


def top_k_for_method(method: str) -> str:
    for family in ("bm25", "embedding"):
        spec = parse_topk_method(method, family)
        if spec:
            return str(spec[1])
    if method.startswith("hybrid_msr_"):
        return "recall5+filter"
    if method.startswith("msr_"):
        return "adaptive"
    if method == "oracle_minimal":
        return "minimal"
    return "all"


def coverage(required: set[str], retrieved: set[str]) -> float | None:
    if not required:
        return None
    return round(len(required & retrieved) / len(required), 4)


def irrelevant_rate(required: set[str], retrieved: set[str]) -> float:
    if not retrieved:
        return 0.0
    return round(len(retrieved - required) / len(retrieved), 4)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["method"]].append(row)
    return [summary_row(method, items) for method, items in sorted(grouped.items())]


def summarize_by_state(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["policy_state"], row["method"])].append(row)
    output = []
    for (state, method), items in sorted(grouped.items()):
        output.append({"policy_state": state, **summary_row(method, items)})
    return output


def summary_row(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "method": method,
        "agent": rows[0]["agent"],
        "agent_group": rows[0]["agent_group"],
        "source": rows[0]["source"],
        "top_k": rows[0]["top_k"],
        "episodes": total,
        "avg_policy_coverage": avg_optional(row["policy_coverage"] for row in rows),
        "avg_irrelevant_policy_rate": round(sum(row["irrelevant_policy_rate"] for row in rows) / total, 4),
        "avg_retrieved_policies": round(sum(row["retrieved_policy_count"] for row in rows) / total, 2),
        "avg_policy_token_cost": round(sum(row["policy_token_cost"] for row in rows) / total, 2),
    }


def avg_optional(values: Any) -> float | str:
    items = [value for value in values if value is not None]
    if not items:
        return "NA"
    return round(sum(items) / len(items), 4)


if __name__ == "__main__":
    main()
