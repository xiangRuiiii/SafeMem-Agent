"""SafeMem 回归测试模块。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

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
from safemem.policy.dense import DenseRetriever
from safemem.data import load_episodes, write_csv, write_json
from safemem.eval.judge import judge_result
from safemem.eval.metrics import summarize, summarize_by_case, summarize_by_state
from safemem.llm_client import configured_embedding_model, configured_model, make_chat_client, make_embedding_client
from safemem.models import AgentResult

"""
扩展 LLM 实验入口，支持 MSR 消融、Hybrid-MSR 消融、多 provider client。默认还是 dry-run，不加 --run 不会调 API。
"""

DEFAULT_METHODS = ",".join(LLM_FULL_METHODS)
T = TypeVar("T")


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
        if args.vmsr_retrieval == "dense":
            raise SystemExit("Dense V-MSR preview would call an embedding API; use --vmsr-retrieval bm25 for dry-run.")
        write_prompt_preview(output_tag, episodes, methods, args)
        print(f"dry_run=1 episodes={len(episodes)} methods={len(methods)} planned_calls={len(episodes) * len(methods)}")
        print(f"prompt_preview=outputs/logs/{output_tag}_prompt_preview.json")
        print("add --run only when you want to call the LLM API")
        return

    model = configured_model(args.model, profile=args.profile, config_path=args.config)
    client = make_chat_client(
        api_key=args.api_key,
        base_url=args.base_url,
        profile=args.profile,
        config_path=args.config,
        timeout=args.timeout,
    )
    results_path = ROOT / "outputs" / "logs" / f"{output_tag}_llm_results.jsonl"
    failures_path = ROOT / "outputs" / "logs" / f"{output_tag}_llm_failures.jsonl"
    results = load_existing_results(results_path) if args.resume else {}
    vmsr_candidate_retriever = build_vmsr_candidate_retriever(args)

    agents = [
        LlmPolicyAgent(
            method,
            client,
            model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            json_mode=not args.no_json_mode,
            include_long_context=args.include_long_context,
            vmsr_cache_path=resolve_path(args.vmsr_cache),
            vmsr_compiler_model=args.vmsr_compiler_model,
            vmsr_candidate_retriever=vmsr_candidate_retriever,
        )
        for method in methods
    ]

    for episode in episodes:
        for agent in agents:
            key = result_key(episode.episode_id, agent.name)
            if key in results:
                continue
            try:
                result = call_with_retries(
                    lambda: judge_result(episode, agent.decide(episode)),
                    max_retries=args.max_retries,
                    retry_delay=args.retry_delay,
                    retry_max_delay=args.retry_max_delay,
                    label=f"{episode.episode_id} {agent.name}",
                )
                require_returned_model(result, args.require_returned_model)
            except Exception as exc:
                append_failure(
                    failures_path,
                    episode_id=episode.episode_id,
                    agent=agent.name,
                    error=exc,
                    attempts=args.max_retries + 1 if is_retryable_error(exc) else 1,
                )
                print(f"failed {episode.episode_id} {agent.name}: {exc}", file=sys.stderr)
                # 75 表示可重试的临时错误，供外层恢复脚本决定是否重启。
                raise SystemExit(75 if is_retryable_error(exc) else 2) from exc
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
        choices=[
            "base",
            "retrieval_top3",
            "retrieval_all",
            "hybrid",
            "msr_ablation",
            "hybrid_ablation",
            "ablation_all",
            "vmsr",
            "comparison_all",
        ],
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
    parser.add_argument(
        "--require-returned-model",
        default="",
        help="Require an exact response model ID; a gateway model switch stops the run before the result is written.",
    )
    parser.add_argument("--max-retries", type=int, default=5, help="单个临时 API 错误的最大重试次数。")
    parser.add_argument("--retry-delay", type=float, default=3.0, help="首次重试等待秒数。")
    parser.add_argument("--retry-max-delay", type=float, default=60.0, help="指数退避的最大等待秒数。")
    parser.add_argument("--no-json-mode", action="store_true", help="Disable response_format json_object for providers that reject it.")
    parser.add_argument("--include-long-context", action="store_true", help="Include long_context in the LLM prompt.")
    parser.add_argument(
        "--vmsr-cache",
        default="data/policy_cache/vmsr_text_v3.jsonl",
        help="Precompiled V-MSR text manifest; text mode fails clearly when it is missing.",
    )
    parser.add_argument(
        "--vmsr-compiler-model",
        default="",
        help="Compiler model recorded in the V-MSR manifest cache key.",
    )
    parser.add_argument("--vmsr-retrieval", choices=["bm25", "dense"], default="bm25")
    parser.add_argument("--embedding-profile", default="", help="Profile for the optional Dense Embedding endpoint.")
    parser.add_argument("--embedding-model", default="", help="Embedding model from the selected profile.")
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
    if name == "msr_ablation":
        methods = []
        for source in ("clean", "noisy"):
            for mode in ("tool_only", "tool_object", "no_condition", "no_penalty", "full"):
                methods.append(f"msr_{mode}_{source}")
        return methods
    if name == "hybrid_ablation":
        methods = []
        for source in ("clean", "noisy"):
            for mode in ("recall_only", "filter_only", "no_penalty", "full"):
                methods.append(f"hybrid_{mode}_{source}")
            methods.append(f"hybrid_msr_{source}")
        return methods
    if name == "ablation_all":
        return methods_for_set("msr_ablation") + methods_for_set("hybrid_ablation")
    if name == "vmsr":
        return [method for method in LLM_COMPARISON_METHODS if method.startswith("vmsr_")]
    if name == "comparison_all":
        return list(LLM_COMPARISON_METHODS)
    raise SystemExit(f"Unsupported method set: {name}")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def build_vmsr_candidate_retriever(args: argparse.Namespace) -> DenseRetriever | None:
    """仅在用户显式选择 dense 且已进入 --run 时创建真实 embedding 检索器。"""

    if args.vmsr_retrieval == "bm25":
        return None
    profile = args.embedding_profile or args.profile
    model = configured_embedding_model(args.embedding_model, profile=profile, config_path=args.config)
    if not model:
        raise SystemExit("Dense V-MSR requires --embedding-model or embedding_model in the selected profile.")
    client = make_embedding_client(profile=profile, config_path=args.config, timeout=args.timeout)
    return DenseRetriever(client, model, top_k=8)


def write_prompt_preview(
    tag: str,
    episodes: list,
    methods: list[str],
    args: argparse.Namespace,
) -> None:
    rows = []
    for episode in episodes[: args.preview_count]:
        for method in methods:
            context = policy_context_for_method(
                episode,
                method,
                vmsr_cache_path=resolve_path(args.vmsr_cache),
                vmsr_compiler_model=args.vmsr_compiler_model,
            )
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
    """加载检查点，并只修复进程中断留下的最后一条不完整 JSONL。"""

    results: dict[tuple[str, str], AgentResult] = {}
    if not path.exists():
        return results
    lines = path.read_bytes().splitlines(keepends=True)
    nonempty_indexes = [index for index, line in enumerate(lines) if line.strip()]
    last_nonempty = nonempty_indexes[-1] if nonempty_indexes else -1
    offset = 0
    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped:
            offset += len(raw_line)
            continue
        try:
            result = AgentResult.from_dict(json.loads(stripped.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            if index != last_nonempty:
                raise RuntimeError(f"Corrupted result log before final record: {path}") from exc
            # 仅截去最后半条记录，已完成检查点仍可供 --resume 使用。
            with path.open("r+b") as handle:
                handle.truncate(offset)
            print(f"repaired_partial_checkpoint={path.name}", file=sys.stderr)
            break
        results[result_key(result.episode_id, result.agent)] = result
        offset += len(raw_line)
    return results


def append_result(path: Path, result: AgentResult) -> None:
    append_jsonl(path, result.to_dict())


def append_failure(path: Path, *, episode_id: str, agent: str, error: Exception, attempts: int) -> None:
    """记录失败请求，便于区分临时网络问题和配置错误。"""

    append_jsonl(
        path,
        {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "episode_id": episode_id,
            "agent": agent,
            "attempts": attempts,
            "retryable": is_retryable_error(error),
            "error_type": type(error).__name__,
            "error": str(error),
        },
    )


def append_jsonl(path: Path, row: dict) -> None:
    """每次写入后主动落盘，避免断电或终止进程丢失已完成结果。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def call_with_retries(
    action: Callable[[], T],
    *,
    max_retries: int,
    retry_delay: float,
    retry_max_delay: float,
    label: str,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """只对网络、限流和服务端错误执行有上限的指数退避重试。"""

    if max_retries < 0 or retry_delay < 0 or retry_max_delay < 0:
        raise ValueError("Retry values must be non-negative.")
    for attempt in range(max_retries + 1):
        try:
            return action()
        except Exception as exc:
            if not is_retryable_error(exc) or attempt == max_retries:
                raise
            delay = min(retry_delay * (2**attempt), retry_max_delay)
            print(
                f"retry {label} attempt={attempt + 1}/{max_retries} wait_seconds={delay:.1f}: {exc}",
                file=sys.stderr,
            )
            sleep(delay)
    raise RuntimeError("Retry loop ended unexpectedly.")


def is_retryable_error(error: Exception) -> bool:
    """仅把连接中断、限流和服务端故障视为可安全重试的错误。"""

    message = str(error).lower()
    if "request failed" in message or "timed out" in message or "connection reset" in message:
        return True
    match = re.search(r"http\s+(\d{3})", message)
    return bool(match and int(match.group(1)) in {408, 409, 425, 429, 500, 502, 503, 504})


def require_returned_model(result: AgentResult, expected_model: str) -> None:
    """阻止中转站静默替换模型，避免一个实验 tag 混入多个模型。"""

    expected = expected_model.strip()
    if expected and result.llm_model != expected:
        raise RuntimeError(
            f"Provider returned model {result.llm_model!r}, expected {expected!r}. "
            "Stop this run and verify the gateway model routing."
        )


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
