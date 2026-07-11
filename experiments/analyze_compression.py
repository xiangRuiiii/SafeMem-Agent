"""汇总人工标注的真实压缩 failure，并与人工注入模式及下游动作结果对照。"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.data import read_jsonl, write_csv


VALID_STATES = {
    "policy_preserved",
    "policy_absent",
    "policy_weakened",
    "policy_misbound",
    "policy_over_included",
}


def main() -> None:
    args = parse_args()
    rows = read_jsonl(resolve_path(args.results))
    labels = read_labels(resolve_path(args.labels))
    decisions = read_decisions(resolve_path(args.decisions)) if args.decisions else {}
    merged = merge_labels(rows, labels, decisions)
    summary = summarize(merged)
    by_state = summarize_by_state(merged)
    write_csv(ROOT / "outputs" / "tables" / f"{args.tag}_compression_summary.csv", summary)
    write_csv(ROOT / "outputs" / "tables" / f"{args.tag}_compression_by_state.csv", by_state)
    print(
        f"rows={len(merged)} labeled={sum(bool(row['human_labeled_policy_state']) for row in merged)} "
        f"decided={sum(bool(row.get('decision')) for row in merged)}"
    )
    for row in summary:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze manually labeled real compression failures.")
    parser.add_argument("--results", required=True, help="Output JSONL from experiments/run_compression.py")
    parser.add_argument("--labels", default="data/annotations/compression_labels_template.csv")
    parser.add_argument("--decisions", default="", help="Optional JSONL from run_compression_decision.py")
    parser.add_argument("--tag", default="compression_sanity")
    return parser.parse_args()


def read_labels(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        output = {str(row.get("sanity_id", "")): {key: str(value or "") for key, value in row.items()} for row in rows}
    for sanity_id, row in output.items():
        state = row.get("human_labeled_policy_state", "")
        if state and state not in VALID_STATES:
            raise RuntimeError(f"Invalid human policy state for {sanity_id}: {state}")
    return output


def read_decisions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(row["sanity_id"]): row for row in read_jsonl(path)}


def merge_labels(
    rows: list[dict[str, Any]],
    labels: dict[str, dict[str, str]],
    decisions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        item = dict(row)
        label = labels.get(str(row["sanity_id"]), {})
        if label.get("human_labeled_policy_state"):
            item["human_labeled_policy_state"] = label["human_labeled_policy_state"]
        if label.get("label_notes"):
            item["label_notes"] = label["label_notes"]
        decision = decisions.get(str(row["sanity_id"]), {})
        for key in (
            "decision",
            "correct",
            "executed_violation",
            "false_refusal",
            "task_success",
            "llm_model",
            "llm_total_tokens",
        ):
            if key in decision:
                item[key] = decision[key]
        output.append(item)
    return output


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["compression_method"])].append(row)
    output = []
    for method, items in sorted(grouped.items()):
        labels = Counter(item.get("human_labeled_policy_state", "") for item in items)
        total = len(items)
        labeled = total - labels[""]
        row: dict[str, Any] = {
            "compression_method": method,
            "episodes": total,
            "labeled_episodes": labeled,
            "preserved_rate": rate(labels["policy_preserved"], labeled),
            "absent_rate": rate(labels["policy_absent"], labeled),
            "weakened_rate": rate(labels["policy_weakened"], labeled),
            "misbound_rate": rate(labels["policy_misbound"], labeled),
            "over_included_rate": rate(labels["policy_over_included"], labeled),
            "agreement_with_manual_injection_pattern": rate(
                sum(
                    item.get("human_labeled_policy_state") == item.get("manual_injection_policy_state")
                    for item in items
                    if item.get("human_labeled_policy_state")
                ),
                labeled,
            ),
            **downstream_metrics(items),
        }
        output.append(row)
    return output


def summarize_by_state(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按人工 failure state 输出真实压缩的 action-level error pattern。"""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        state = str(row.get("human_labeled_policy_state", ""))
        if state:
            grouped[(str(row["compression_method"]), state)].append(row)
    output = []
    for (method, state), items in sorted(grouped.items()):
        output.append(
            {
                "compression_method": method,
                "human_labeled_policy_state": state,
                "episodes": len(items),
                **downstream_metrics(items),
            }
        )
    return output


def downstream_metrics(items: list[dict[str, Any]]) -> dict[str, float | str | int]:
    decided = [item for item in items if item.get("decision")]
    total = len(decided)
    return {
        "downstream_decided_episodes": total,
        "downstream_accuracy": rate(sum(bool(item.get("correct")) for item in decided), total),
        "downstream_violation": rate(sum(bool(item.get("executed_violation")) for item in decided), total),
        "downstream_false_refusal": rate(sum(bool(item.get("false_refusal")) for item in decided), total),
        "downstream_task_success": rate(sum(bool(item.get("task_success")) for item in decided), total),
    }


def rate(value: int, total: int) -> float | str:
    return round(value / total, 4) if total else "NA"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
