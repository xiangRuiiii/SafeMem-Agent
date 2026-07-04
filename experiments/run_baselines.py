from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.agents.baselines import (
    AllPolicyAgent,
    ExactReplayAgent,
    NoPolicyAgent,
    SummaryPolicyAgent,
)
from safemem.agents.msr_agent import MsrAgent
from safemem.data import load_episodes, write_csv, write_json
from safemem.eval.judge import judge_result
from safemem.eval.metrics import summarize


def main() -> None:
    episodes = load_episodes(ROOT / "data" / "episodes" / "sample.jsonl")
    agents = [
        NoPolicyAgent(),
        SummaryPolicyAgent(),
        AllPolicyAgent(),
        ExactReplayAgent(),
        MsrAgent(),
    ]

    results = []
    for episode in episodes:
        for agent in agents:
            results.append(judge_result(episode, agent.decide(episode)))

    result_rows = [result.to_dict() for result in results]
    summary_rows = summarize(results)

    write_json(ROOT / "outputs" / "logs" / "baseline_results.json", result_rows)
    write_csv(ROOT / "outputs" / "tables" / "baseline_summary.csv", summary_rows)

    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
