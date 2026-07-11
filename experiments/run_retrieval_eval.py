"""SafeMem 回归测试模块。"""

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
from safemem.llm_client import configured_embedding_model, make_embedding_client
from safemem.models import Episode
from safemem.policy.dense import DenseRetriever
from safemem.policy.vmsr import certificate_is_internally_valid

"""
retrieval-only 实验入口，支持 retrieval_all、msr_ablation、hybrid_ablation
"""

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
    vmsr_candidate_retriever = build_vmsr_candidate_retriever(args)

    rows = []
    for episode in episodes:
        for method in methods:
            context = policy_context_for_method(
                episode,
                method,
                vmsr_cache_path=resolve_path(args.vmsr_cache),
                vmsr_compiler_model=args.vmsr_compiler_model,
                vmsr_candidate_retriever=vmsr_candidate_retriever,
            )
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
        choices=["retrieval_top3", "retrieval_all", "hybrid", "msr_ablation", "hybrid_ablation", "ablation_all", "vmsr"],
        help="Named retrieval method set. Overrides --methods when set.",
    )
    parser.add_argument("--episode-ids", default="", help="Optional comma-separated episode IDs to run.")
    parser.add_argument("--limit", type=int, default=0, help="Optional number of episodes from the start of the file.")
    parser.add_argument("--vmsr-cache", default="data/policy_cache/vmsr_text_v3.jsonl")
    parser.add_argument("--vmsr-compiler-model", default="")
    parser.add_argument("--vmsr-retrieval", choices=["bm25", "dense"], default="bm25")
    parser.add_argument("--embedding-profile", default="")
    parser.add_argument("--embedding-model", default="")
    parser.add_argument("--embedding-config", default="")
    parser.add_argument("--embedding-timeout", type=float, default=60.0)
    parser.add_argument("--run-dense", action="store_true", help="Allow real embedding API calls when --vmsr-retrieval dense.")
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
    if name == "msr_ablation":
        methods = []
        for source in ("clean", "noisy"):
            for mode in ("tool_only", "tool_object", "no_condition", "no_penalty", "full"):
                methods.append(f"msr_{mode}_{source}")
        methods.extend(["msr_clean", "msr_noisy", "oracle_minimal"])
        return methods
    if name == "hybrid_ablation":
        methods = []
        for source in ("clean", "noisy"):
            for mode in ("recall_only", "filter_only", "no_penalty", "full"):
                methods.append(f"hybrid_{mode}_{source}")
            methods.append(f"hybrid_msr_{source}")
        methods.extend(["embedding_clean_top5", "embedding_noisy_top5", "msr_clean", "msr_noisy", "oracle_minimal"])
        return methods
    if name == "ablation_all":
        return methods_for_set("msr_ablation") + methods_for_set("hybrid_ablation")
    if name == "vmsr":
        methods = []
        for representation in ("struct", "text"):
            for mode in ("context", "guard"):
                for source in ("clean", "noisy"):
                    methods.append(f"vmsr_{representation}_{mode}_{source}")
        return methods
    raise SystemExit(f"Unsupported method set: {name}")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def build_vmsr_candidate_retriever(args: argparse.Namespace) -> DenseRetriever | None:
    """Dense 检索是唯一会联网的 retrieval-only 分支，必须由用户显式放行。"""

    if args.vmsr_retrieval == "bm25":
        return None
    if not args.run_dense:
        raise SystemExit("Dense V-MSR requires --run-dense because it calls the embedding API.")
    profile = args.embedding_profile
    model = configured_embedding_model(args.embedding_model, profile=profile, config_path=args.embedding_config)
    if not model:
        raise SystemExit("Dense V-MSR requires --embedding-model or embedding_model in the selected profile.")
    client = make_embedding_client(profile=profile, config_path=args.embedding_config, timeout=args.embedding_timeout)
    return DenseRetriever(client, model, top_k=8)


def retrieval_row(episode: Episode, method: str, context: Any) -> dict[str, Any]:
    retrieved = set(context.policy_ids)
    required = set(episode.required_policy_ids())
    policy_payload = context.prompt_payload()
    return {
        "episode_id": episode.episode_id,
        "domain": episode.domain,
        "policy_state": episode.policy_carriage_state,
        "case_type": "safe" if episode.is_safe_case else "risky",
        "challenge_type": episode.challenge_type,
        "verification_mode": "guard" if context.guard else ("context" if context.certificate else ""),
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
        "certificate_policy_ids": list((context.certificate or {}).get("policy_ids", [])),
        "certificate_decision": (context.certificate or {}).get("decision_floor", ""),
        "certificate_internal_validity": _certificate_internal_validity(context),
        "certificate_validity": _certificate_validity_from_context(episode, context),
        "certificate_minimality": (context.certificate or {}).get("minimal"),
        "certificate_oracle_match": _certificate_oracle_match(episode, context),
        "decision_stability": (context.certificate or {}).get("decision_stable"),
        "unknown_escalated": (context.certificate or {}).get("unknown_escalated"),
        "conflict_resolved": _conflict_resolution_accuracy(episode, context),
    }


def top_k_for_method(method: str) -> str:
    if method.startswith("vmsr_"):
        return "bm25_top8+verify"
    for family in ("bm25", "embedding", "hash_vector"):
        spec = parse_topk_method(method, family)
        if spec:
            return str(spec[1])
    if method.startswith("hybrid_msr_"):
        return "recall5+filter"
    if method.startswith("hybrid_recall_only_"):
        return "recall5"
    if method.startswith("hybrid_"):
        return "recall5+ablation"
    if method.startswith("msr_") and method not in {"msr_clean", "msr_noisy"}:
        return "adaptive_ablation"
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
        "certificate_internal_validity": avg_optional(row["certificate_internal_validity"] for row in rows),
        "certificate_validity": avg_optional(row["certificate_validity"] for row in rows),
        "certificate_minimality": avg_optional(row["certificate_minimality"] for row in rows),
        "certificate_oracle_match": avg_optional(row["certificate_oracle_match"] for row in rows),
        "decision_stability": avg_optional(row["decision_stability"] for row in rows),
        "unknown_escalation_rate": avg_optional(row["unknown_escalated"] for row in rows),
        "conflict_resolution_accuracy": avg_optional(row["conflict_resolved"] for row in rows),
    }


def avg_optional(values: Any) -> float | str:
    items = [value for value in values if value is not None]
    if not items:
        return "NA"
    return round(sum(float(item) for item in items) / len(items), 4)


def _certificate_internal_validity(context: Any) -> bool | None:
    certificate = context.certificate or {}
    if not certificate:
        return None
    return certificate_is_internally_valid(certificate)


def _certificate_validity_from_context(episode: Episode, context: Any) -> bool | None:
    required = set(episode.certificate_policy_ids)
    if not required:
        return None
    return required <= set(context.policy_ids)


def _certificate_oracle_match(episode: Episode, context: Any) -> bool | None:
    expected = set(episode.certificate_policy_ids)
    if not expected:
        return None
    return set(context.policy_ids) == expected


def _conflict_resolution_accuracy(episode: Episode, context: Any) -> bool | None:
    if not episode.conflict_policy_ids:
        return None
    selected = set(context.policy_ids)
    expected = set(episode.certificate_policy_ids)
    return expected <= selected and not bool(selected & set(episode.conflict_policy_ids))


if __name__ == "__main__":
    main()
