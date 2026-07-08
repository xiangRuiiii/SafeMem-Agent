# SafeMem-Agent

SafeMem-Agent is the working repository for SafeMemBench-Action.

The project studies whether policy carriage failures in long tool-using LLM
agent tasks become action-level safety failures. It also provides a lightweight
method, Minimal Sufficient Policy Retrieval, to retrieve only the policies needed
for the candidate tool action before execution.

## Current Scope

- Deterministic tool simulators for email, file, and calendar tasks.
- Episode data format for action-level safety cases.
- Baseline agents for no policy, summary policy, all-policy replay, and exact
  replay with preflight.
- A first MSR agent with simple policy scoring and preflight checks.
- Metrics for violation, false refusal, task success, decision accuracy, and
  policy token cost.

## Layout

```text
data/
  episodes/          Sample and future benchmark episodes.
  policies/          Shared policy files.
  annotations/       Human checks and data quality notes.
safemem/
  agents/            Baseline and MSR agents.
  eval/              Judging and metric code.
  policy/            Policy store, matching, retrieval, and preflight checks.
  tools/             Deterministic tool simulators.
experiments/         Runnable experiment entrypoints.
outputs/             Generated logs, tables, and figures.
docs/                Project notes.
tests/               Basic regression tests.
```

## Quick Start

Run the baseline and MSR smoke experiment:

```bash
python experiments/run_baselines.py
```

Run the basic tests:

```bash
python -m unittest
```

Preview the seven-method LLM suite without calling an API:

```bash
python experiments/run_llm_eval.py --episodes data/episodes/mvp_plus_90_en.jsonl --tag llm_en_90
```

See `docs/llm_eval.md` for the API runner and recommended 90-episode order.

The scripts use only the Python standard library.
