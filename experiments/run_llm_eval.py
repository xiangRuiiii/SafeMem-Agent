from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.agents.llm_agent import (
    LLM_COMPARISON_METHODS,
    LLM_FULL_METHODS,
    LLM_METHOD_GROUPS,
    SUPPORTED_LLM_METHODS,
    LlmPolicyAgent,
    build_llm_messages,
    policy_context_for_method,
)
from safemem.data import load_episodes, write_csv, write_json
from safemem.eval.judge import judge_result
from safemem.eval.metrics import summarize, summarize_by_case, summarize_by_state
from safemem.llm_client import OpenAICompatibleClient, configured_model
from safemem.models import AgentResult


DEFAULT_METHODS = ",".join(LLM_FULL_METHODS)


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
    output_tag = args.tag or f"{episode_path.stem}_llm"

    if not args.run:
        write_prompt_preview(output_tag, episodes, methods, args)
        print(f"dry_run=1 episodes={len(episodes)} methods={len(methods)} planned_calls={len(episodes) * len(methods)}")
        print(f"prompt_preview=outputs/logs/{output_tag}_prompt_preview.json")
        print("add --run only when you want to call the LLM API")
        return

    model = configured_model(args.model, profile=args.profile, config_path=args.config)
    client = OpenAICompatibleClient(
        api_key=args.api_key,
        base_url=args.base_url,
        profile=args.profile,
        config_path=args.config,
        timeout=args.timeout,
    )
    results_path = ROOT / "outputs" / "logs" / f"{output_tag}_llm_results.jsonl"
    results = load_existing_results(results_path) if args.resume else {}

    agents = [
        LlmPolicyAgent(
            method,
            client,
            model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            json_mode=not args.no_json_mode,
            include_long_context=args.include_long_context,
        )
        for method in methods
    ]

    for episode in episodes:
        for agent in agents:
            key = result_key(episode.episode_id, agent.name)
            if key in results:
                continue
            result = judge_result(episode, agent.decide(episode))
            results[key] = result
            append_result(results_path, result)
            print(f"{episode.episode_id} {agent.name} {result.decision}")

    ordered = ordered_results(episodes, agents, results)
    result_rows = [result.to_dict() for result in ordered]
    summary_rows = summarize(ordered)
    state_rows = summarize_by_state(ordered, episodes)
    case_rows = summarize_by_case(ordered, episodes)

    write_json(ROOT / "outputs" / "logs" / f"{output_tag}_llm_results.json", result_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_llm_summary.csv", summary_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_llm_by_state.csv", state_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_llm_by_case.csv", case_rows)

    for row in summary_rows:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenAI-compatible LLM decisions on SafeMem episodes.")
    parser.add_argument(
        "--episodes",
        default="data/episodes/mvp_plus_90_en.jsonl",
        help="Episode JSONL path, relative to repository root by default.",
    )
    parser.add_argument("--tag", default="", help="Output filename tag.")
    parser.add_argument("--methods", default=DEFAULT_METHODS, help=f"Comma-separated methods. Default: {DEFAULT_METHODS}")
    parser.add_argument(
        "--method-set",
        default="",
        choices=["base", "retrieval_top3", "retrieval_all", "hybrid", "comparison_all"],
        help="Named method set. Overrides --methods when set.",
    )
    parser.add_argument("--episode-ids", default="", help="Optional comma-separated episode IDs to run.")
    parser.add_argument("--limit", type=int, default=0, help="Optional number of episodes from the start of the file.")
    parser.add_argument("--run", action="store_true", help="Actually call the LLM API. Without this flag, only preview prompts.")
    parser.add_argument("--resume", action="store_true", help="Skip calls already present in the JSONL results log.")
    parser.add_argument("--profile", default="", help="Profile name from config/llm.local.json.")
    parser.add_argument("--config", default="", help="Optional local LLM config path. Default: config/llm.local.json.")
    parser.add_argument("--api-key", default="", help="API key. Prefer env SAFEMEM_LLM_API_KEY instead.")
    parser.add_argument("--base-url", default="", help="OpenAI-compatible base URL. Default: env or https://api.openai.com/v1.")
    parser.add_argument("--model", default="", help="Model name. Default: SAFEMEM_LLM_MODEL / LLM_MODEL.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--no-json-mode", action="store_true", help="Disable response_format json_object for providers that reject it.")
    parser.add_argument("--include-long-context", action="store_true", help="Include long_context in the LLM prompt.")
    parser.add_argument("--preview-count", type=int, default=1, help="Episodes to include in dry-run prompt preview.")
    return parser.parse_args()


def parse_methods(value: str) -> list[str]:
    methods = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [method for method in methods if method not in SUPPORTED_LLM_METHODS]
    if unknown:
        supported = ", ".join(sorted(SUPPORTED_LLM_METHODS))
        raise SystemExit(f"Unsupported methods: {unknown}. Supported: {supported}")
    return methods


def methods_for_set(name: str) -> list[str]:
    if name == "base":
        return list(LLM_FULL_METHODS)
    if name == "retrieval_top3":
        return [
            "bm25_clean_top3",
            "bm25_noisy_top3",
            "embedding_clean_top3",
            "embedding_noisy_top3",
        ]
    if name == "retrieval_all":
        return [method for method in LLM_COMPARISON_METHODS if method.startswith(("bm25_", "embedding_"))]
    if name == "hybrid":
        return [
            "embedding_noisy_top3",
            "msr_noisy",
            "hybrid_msr_noisy",
            "embedding_clean_top3",
            "msr_clean",
            "hybrid_msr_clean",
        ]
    if name == "comparison_all":
        return list(LLM_COMPARISON_METHODS)
    raise SystemExit(f"Unsupported method set: {name}")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def write_prompt_preview(
    tag: str,
    episodes: list,
    methods: list[str],
    args: argparse.Namespace,
) -> None:
    rows = []
    for episode in episodes[: args.preview_count]:
        for method in methods:
            context = policy_context_for_method(episode, method)
            messages = build_llm_messages(
                episode,
                context,
                include_long_context=args.include_long_context,
            )
            rows.append(
                {
                    "episode_id": episode.episode_id,
                    "method": method,
                    "agent_group": LLM_METHOD_GROUPS[method],
                    "policy_source_used": context.source,
                    "context_policy_ids": context.policy_ids,
                    "messages": messages,
                }
            )
    write_json(ROOT / "outputs" / "logs" / f"{tag}_prompt_preview.json", rows)


def load_existing_results(path: Path) -> dict[tuple[str, str], AgentResult]:
    results: dict[tuple[str, str], AgentResult] = {}
    if not path.exists():
        return results
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            result = AgentResult.from_dict(json.loads(line))
            results[result_key(result.episode_id, result.agent)] = result
    return results


def append_result(path: Path, result: AgentResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def ordered_results(
    episodes: list,
    agents: list[LlmPolicyAgent],
    results: dict[tuple[str, str], AgentResult],
) -> list[AgentResult]:
    ordered = []
    for episode in episodes:
        for agent in agents:
            result = results.get(result_key(episode.episode_id, agent.name))
            if result:
                ordered.append(result)
    return ordered


def result_key(episode_id: str, agent: str) -> tuple[str, str]:
    return (episode_id, agent)


if __name__ == "__main__":
    main()
