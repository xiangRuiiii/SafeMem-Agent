# Figure Source Data

These CSV files contain only completed, author-provided experiment summaries. They are copied from the corresponding generated tables under `outputs/tables/` so manuscript figures remain reproducible even though runtime outputs are ignored by Git.

No values are interpolated or simulated. The completed 300-episode DeepSeek, Qwen, Kimi and gateway-advertised GPT-5.4-mini core runs are copied exactly from their generated summary tables. Incomplete GLM/Claude runs, multilingual action evaluation, top-k curves and final ablations are intentionally absent from the benchmark-centered manuscript.

| File | Completed evidence |
|---|---|
| `main_results_300.csv` | Completed 300-episode English core comparison for DeepSeek, Qwen, Kimi and gateway-advertised GPT-5.4-mini |
| `carried_failure_by_state_300.csv` | Carried-policy failure states on the 300-episode DeepSeek run |
| `figure2_policy_error_matrix_deepseek.csv` | Exact mutually exclusive outcome counts for the Figure 2 DeepSeek failure-error matrix |
| `main_results_90.csv` | Seven-method English main run, 90 episodes |
| `carried_failure_by_state_90.csv` | Carried-policy results by policy state, 18 episodes per state |
| `vmsr_adversarial_retrieval_36.csv` | Retrieval-only adversarial comparison, 36 episodes |
| `vmsr_adversarial_llm_36.csv` | LLM decision comparison on the adversarial set |
| `vmsr_adversarial_errors_36.csv` | Challenge-specific failure-error matrix |
| `compression_sanity_40.csv` | Five compression methods, 8 seeds per method |
| `vmsr_challenge_72.csv` | Historical prototype evaluation; not used in the benchmark-centered manuscript |
