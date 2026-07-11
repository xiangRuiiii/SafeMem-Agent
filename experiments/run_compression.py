"""运行真实上下文压缩 sanity check；默认 dry-run，不调用任何 LLM API。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.data import read_jsonl, write_json
from safemem.llm_client import ChatClient, configured_model, make_chat_client


def main() -> None:
    args = parse_args()
    rows = read_jsonl(resolve_path(args.inputs))
    output = resolve_path(args.output or f"data/compression_sanity/compressed_{args.profile or 'default'}.jsonl")
    if not args.run:
        preview = [preview_row(row) for row in rows[: args.preview_count]]
        write_json(ROOT / "outputs" / "logs" / "compression_prompt_preview.json", preview)
        print(f"dry_run=1 rows={len(rows)} preview=outputs/logs/compression_prompt_preview.json")
        return

    model = configured_model(args.model, profile=args.profile, config_path=args.config)
    client = make_chat_client(
        api_key=args.api_key,
        base_url=args.base_url,
        profile=args.profile,
        config_path=args.config,
        timeout=args.timeout,
    )
    existing = read_existing(output) if args.resume else {}
    completed: list[dict[str, Any]] = []
    for row in rows:
        if row["sanity_id"] in existing:
            completed.append(existing[row["sanity_id"]])
            continue
        result = compress_row(row, client, model)
        completed.append(result)
        write_jsonl(output, completed)
        print(f"compressed={row['sanity_id']}")
    write_jsonl(output, completed)
    print(f"completed={len(completed)} output={output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real long-context compression sanity checks.")
    parser.add_argument("--inputs", default="data/episodes/compression_sanity_en.jsonl")
    parser.add_argument("--output", default="")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--profile", default="deepseek")
    parser.add_argument("--config", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--preview-count", type=int, default=2)
    return parser.parse_args()


def compress_row(row: dict[str, Any], client: ChatClient, model: str) -> dict[str, Any]:
    method = row["compression_method"]
    if method == "manual_injected_carried_policy":
        extracted = list(row["manual_carried_policy"])
        context = ["Manual injected carried policy: " + " | ".join(extracted)]
    elif method == "truncated_carried_policy":
        context = list(row["raw_long_context"][-2:])
        extracted = []
    elif method == "llm_summarized_carried_policy":
        context, extracted = one_shot_summary(row["raw_long_context"], client, model)
    elif method == "rolling_summary":
        context, extracted = rolling_summary(row["raw_long_context"], client, model)
    elif method == "recursive_summary":
        context, extracted = recursive_summary(row["raw_long_context"], client, model)
    else:
        raise RuntimeError(f"Unsupported compression method: {method}")
    output = dict(row)
    output["compressed_context"] = context
    output["extracted_carried_policy"] = extracted
    output["auto_predicted_policy_state"] = ""
    return output


def one_shot_summary(parts: list[str], client: ChatClient, model: str) -> tuple[list[str], list[str]]:
    return _summarize("\n\n".join(parts), client, model)


def rolling_summary(parts: list[str], client: ChatClient, model: str) -> tuple[list[str], list[str]]:
    summary = ""
    policies: list[str] = []
    for part in parts:
        summary, policies = _summarize(f"Previous summary:\n{summary}\n\nNew segment:\n{part}", client, model)
        summary = "\n".join(summary)
    return [summary], policies


def recursive_summary(parts: list[str], client: ChatClient, model: str) -> tuple[list[str], list[str]]:
    current = list(parts)
    policies: list[str] = []
    while len(current) > 1:
        next_round: list[str] = []
        for index in range(0, len(current), 2):
            summary, policies = _summarize("\n\n".join(current[index : index + 2]), client, model)
            next_round.append("\n".join(summary))
        current = next_round
    return current or [""], policies


def _summarize(context: str, client: ChatClient, model: str) -> tuple[list[str], list[str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "Summarize the context for an action-taking agent. Return strict JSON with keys summary and retained_policies. "
                "Retain exact policy conditions and effects when present; do not invent policies."
            ),
        },
        {"role": "user", "content": context},
    ]
    response = client.complete(messages, model=model, temperature=0.0, max_tokens=500, json_mode=True)
    try:
        value = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Compression model returned invalid JSON: {response.text[:160]}") from exc
    summary = str(value.get("summary", "")).strip()
    policies = value.get("retained_policies", [])
    if isinstance(policies, str):
        policies = [policies]
    if not isinstance(policies, list):
        policies = []
    return [summary], [str(item) for item in policies if str(item).strip()]


def preview_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sanity_id": row["sanity_id"],
        "compression_method": row["compression_method"],
        "prompt": row["compression_prompt"],
        "raw_context": row["raw_long_context"],
    }


def read_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {row["sanity_id"]: row for row in read_jsonl(path)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
