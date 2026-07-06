# Policy Pressure Plan

Each pressure group reuses the same 90 episode templates but changes the number of injected irrelevant policies.

| Irrelevant policies | Episodes | English file | Chinese file |
| --- | --- | --- | --- |
| 0 | 90 | `data/episodes/pressure/mvp_plus_90_irrelevant_0_en.jsonl` | `data/episodes/pressure/mvp_plus_90_irrelevant_0_zh.jsonl` |
| 10 | 90 | `data/episodes/pressure/mvp_plus_90_irrelevant_10_en.jsonl` | `data/episodes/pressure/mvp_plus_90_irrelevant_10_zh.jsonl` |
| 30 | 90 | `data/episodes/pressure/mvp_plus_90_irrelevant_30_en.jsonl` | `data/episodes/pressure/mvp_plus_90_irrelevant_30_zh.jsonl` |
| 50 | 90 | `data/episodes/pressure/mvp_plus_90_irrelevant_50_en.jsonl` | `data/episodes/pressure/mvp_plus_90_irrelevant_50_zh.jsonl` |

## Result Snapshot

Command:

```bash
python experiments/run_policy_pressure.py
```

All rows below have 90 episodes, 100% accuracy, 0% executed-violation rate, and 0% false-refusal rate for `all_policy`, `exact_active_replay`, `oracle_minimal`, and `msr`.

| Language | Irrelevant policies | all_policy / exact_active_replay token cost | oracle_minimal token cost | MSR token cost | MSR policy coverage | MSR irrelevant policy rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| en | 0 | 78.27 | 27.30 | 27.30 | 1.00 | 0.00 |
| en | 10 | 370.27 | 27.30 | 27.30 | 1.00 | 0.00 |
| en | 30 | 1009.77 | 27.30 | 27.30 | 1.00 | 0.00 |
| en | 50 | 1609.77 | 27.30 | 27.30 | 1.00 | 0.00 |
| zh | 0 | 96.83 | 33.37 | 33.37 | 1.00 | 0.00 |
| zh | 10 | 449.73 | 33.37 | 33.37 | 1.00 | 0.00 |
| zh | 30 | 1216.90 | 33.37 | 33.37 | 1.00 | 0.00 |
| zh | 50 | 1896.90 | 33.37 | 33.37 | 1.00 | 0.00 |
