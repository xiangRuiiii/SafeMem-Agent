# LLM Evaluation Plan

This runner tests LLM action-level decisions on the 90 MVP+ episodes without changing the deterministic baselines.

## Policy Sources

The LLM receives only:

- `task_goal`
- `candidate_action`
- `policy_context`
- optional `long_context`, only when `--include-long-context` is set

The LLM prompt must not contain answer fields such as `required_policy_ids`, `expected_decision`, `allowed_decisions`, `forbidden_decisions`, `labels`, or `ground_truth_policies`.

Supported LLM methods:

| agent | policy context | group |
| --- | --- | --- |
| `llm_no_policy` | none | failure baseline |
| `llm_carried_policy` | `carried_policy` | failure impact |
| `llm_all_policy_clean` | full `canonical_policy_registry` | clean 上界成本 |
| `llm_msr_clean` | `canonical_policy_registry` + MSR | clean 检索恢复 |
| `llm_all_policy_noisy` | full `noisy_policy_pool` | noisy 全量对照 |
| `llm_msr_noisy` | `noisy_policy_pool` + MSR | noisy 检索恢复 |
| `llm_oracle_minimal` | `ground_truth_policies` | oracle 最小策略列表诊断 |

## Dry Run First

Dry run is the default and does not call the API:

```powershell
cd D:\coder\SafeMem
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_90_en.jsonl --tag llm_en_90
```

This writes:

```text
outputs/logs/llm_en_90_prompt_preview.json
```

## Run With API

Use an OpenAI-compatible endpoint. The preferred local config is ignored by git:

```text
config/llm.local.json
```

Example schema is tracked in:

```text
config/llm.example.json
```

You can also override config values with environment variables:

```powershell
$env:SAFEMEM_LLM_API_KEY="YOUR_KEY"
$env:SAFEMEM_LLM_BASE_URL="https://api.openai.com/v1"
$env:SAFEMEM_LLM_MODEL="YOUR_MODEL"
```

Full seven-method pass:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag llm_en_90_full `
  --profile deepseek `
  --run `
  --resume
```

Core four-method pass:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag llm_en_90_core `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean `
  --profile deepseek `
  --run `
  --resume
```

Then inspect:

```powershell
Get-Content outputs\tables\llm_en_90_core_llm_summary.csv
Get-Content outputs\tables\llm_en_90_core_llm_by_state.csv
Get-Content outputs\tables\llm_en_90_core_llm_by_case.csv
```

Run selected episodes only:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag llm_en_roadmap_fix `
  --methods msr_clean `
  --episode-ids file_008_absent_share_private_roadmap,file_015_weakened_share_private_roadmap,file_022_misbound_share_private_roadmap `
  --profile deepseek `
  --run `
  --resume
```

## Suggested Order

1. Dry-run prompt preview on English 90 episodes.
2. Run English 90 episodes with four core methods.
3. Add Chinese 90 episodes after the English prompt format is stable.
4. Add noisy ablations: `all_policy_noisy,msr_noisy`.
5. Use `oracle_minimal` only as a minimal-policy-list diagnostic, not as a deployable method. It is not a certificate oracle on missing-evidence cases because it does not receive V-MSR's verifier-produced decision floor.
