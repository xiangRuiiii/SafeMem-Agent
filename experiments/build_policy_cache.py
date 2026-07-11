"""显式构建 V-MSR-Text 策略 manifest 缓存；默认只预览，不调用 API。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.llm_client import configured_model, make_chat_client
from safemem.models import Policy
from safemem.policy.compile import ManifestStore, compile_policy, manifest_key


POLICY_FIELDS = ("canonical_policy_registry", "noisy_policy_pool")


def main() -> None:
    args = parse_args()
    model = configured_model(args.model, profile=args.profile, config_path=args.config)
    cache = ManifestStore(resolve_path(args.cache), model)
    policies = unique_policies([resolve_path(value) for value in split_paths(args.episodes)], model)
    missing = [policy for policy in policies if not cache.has(policy, model)]
    print(f"unique_policies={len(policies)} cache_misses={len(missing)} model={model}")
    if not args.run:
        print("dry_run=1; add --run to compile only the reported cache misses")
        print_cache_status(cache, policies)
        return

    client = make_chat_client(
        api_key=args.api_key,
        base_url=args.base_url,
        profile=args.profile,
        config_path=args.config,
        timeout=args.timeout,
    )
    for index, policy in enumerate(missing, start=1):
        rule = compile_policy(policy, client, model)
        cache.add(policy, model, rule)
        cache.save()
        print(
            f"compiled={index}/{len(missing)} policy_id={policy.policy_id} "
            f"key={manifest_key(policy, model)[:12]} status={rule.compiler_status}"
        )
    print_cache_status(cache, policies)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cached policy manifests for V-MSR text mode.")
    parser.add_argument(
        "--episodes",
        default="data/episodes/mvp_plus_300_en.jsonl,data/episodes/vmsr_challenge_72_en.jsonl",
        help="Comma-separated JSONL files; policies are streamed and deduplicated by text hash.",
    )
    parser.add_argument("--cache", default="data/policy_cache/vmsr_text_v3.jsonl")
    parser.add_argument("--run", action="store_true", help="Actually call the configured compiler model.")
    parser.add_argument("--resume", action="store_true", help="Compatibility flag; the existing cache is always reused.")
    parser.add_argument("--profile", default="deepseek")
    parser.add_argument("--config", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def unique_policies(paths: list[Path], model: str) -> list[Policy]:
    """流式扫描 JSONL，避免把大型 episode 文件整体加载到内存。"""

    seen: set[str] = set()
    output: list[Policy] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                for field in POLICY_FIELDS:
                    for raw_policy in row.get(field, []):
                        policy = Policy.from_dict(raw_policy)
                        key = manifest_key(policy, model)
                        if key not in seen:
                            seen.add(key)
                            output.append(policy)
    return output


def split_paths(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def print_cache_status(cache: ManifestStore, policies: list[Policy]) -> None:
    """输出 Text manifest 的有效性概览，方便在评估前发现编译退化。"""

    statuses = Counter()
    missing = 0
    for policy in policies:
        if not cache.has(policy, cache.model):
            missing += 1
            continue
        statuses[cache.rule_for(policy).compiler_status] += 1
    summary = ", ".join(f"{status}={count}" for status, count in sorted(statuses.items())) or "none"
    print(f"manifest_statuses: {summary}; missing={missing}")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
