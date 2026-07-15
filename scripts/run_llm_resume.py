"""在 LLM 评测进程异常退出后，以 --resume 自动恢复未完成的检查点。"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    args = parse_args()
    runner_args = list(args.runner_args)
    if runner_args[:1] == ["--"]:
        runner_args = runner_args[1:]
    if "--run" not in runner_args:
        raise SystemExit("run_llm_resume.py requires --run in the forwarded runner arguments.")
    if "--resume" not in runner_args:
        runner_args.append("--resume")

    command = [sys.executable, str(ROOT / "experiments" / "run_llm_eval.py"), *runner_args]
    for restart in range(args.max_restarts + 1):
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode == 0:
            return
        # 配置/参数错误与手动中断不应被自动循环放大。
        if completed.returncode in {2, 130, -2}:
            raise SystemExit(completed.returncode)
        if restart == args.max_restarts:
            raise SystemExit(completed.returncode)
        delay = min(args.restart_delay * (2**restart), args.restart_max_delay)
        print(
            f"runner_restart={restart + 1}/{args.max_restarts} wait_seconds={delay:.1f} exit_code={completed.returncode}",
            file=sys.stderr,
        )
        time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restart a resumable SafeMem LLM evaluation after transient failures.")
    parser.add_argument("--max-restarts", type=int, default=12, help="进程级临时故障的最大重启次数。")
    parser.add_argument("--restart-delay", type=float, default=30.0, help="首次重启等待秒数。")
    parser.add_argument("--restart-max-delay", type=float, default=300.0, help="进程重启退避的最大等待秒数。")
    parser.add_argument("runner_args", nargs=argparse.REMAINDER, help="传给 run_llm_eval.py 的参数，使用 -- 分隔。")
    args = parser.parse_args()
    if args.max_restarts < 0 or args.restart_delay < 0 or args.restart_max_delay < 0:
        parser.error("Restart values must be non-negative.")
    return args


if __name__ == "__main__":
    main()
