"""SafeMem 回归测试模块。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from safemem.agents.baselines import (
    AllPolicyCleanAgent,
    AllPolicyNoisyAgent,
    CarriedPolicyAgent,
    NoPolicyAgent,
    OracleMinimalAgent,
    SummaryPolicyAgent,
)
from safemem.agents.msr_agent import MsrAgent, MsrNoisyAgent
from safemem.data import load_episodes, write_csv, write_json
from safemem.eval.judge import judge_result
from safemem.eval.metrics import summarize, summarize_by_case, summarize_by_state


def main() -> None:
    args = parse_args()
    episode_path = Path(args.episodes)
    if not episode_path.is_absolute():
        episode_path = ROOT / episode_path
    output_tag = args.tag or episode_path.stem

    episodes = load_episodes(episode_path)
    agents = [
        NoPolicyAgent(),
        SummaryPolicyAgent(),
        CarriedPolicyAgent(),
        AllPolicyCleanAgent(),
        MsrAgent(),
        OracleMinimalAgent(),
        AllPolicyNoisyAgent(),
        MsrNoisyAgent(),
    ]

    results = []
    for episode in episodes:
        for agent in agents:
            results.append(judge_result(episode, agent.decide(episode)))

    result_rows = [result.to_dict() for result in results]
    summary_rows = summarize(results)
    state_rows = summarize_by_state(results, episodes)
    case_rows = summarize_by_case(results, episodes)

    write_json(ROOT / "outputs" / "logs" / f"{output_tag}_results.json", result_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_summary.csv", summary_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_by_state.csv", state_rows)
    write_csv(ROOT / "outputs" / "tables" / f"{output_tag}_by_case.csv", case_rows)

    for row in summary_rows:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline agents on an episode JSONL file.")
    parser.add_argument(
        "--episodes",
        default="data/episodes/sample.jsonl",
        help="Episode JSONL path, relative to the repository root by default.",
    )
    parser.add_argument("--tag", default="", help="Output filename tag.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
