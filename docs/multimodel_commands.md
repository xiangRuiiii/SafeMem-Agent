# Multi-Model Core Evaluation

This protocol tests whether the policy-carriage and V-MSR conclusions survive a change of decision model. It freezes the English 300-episode benchmark, the method list, prompt format, temperature, and the V-MSR Text compiler manifest. Only the final decision-model profile changes.

## 1. Configure local profiles

Copy the tracked template to the ignored local file and fill in only the keys and model identifiers you intend to use:

```powershell
Copy-Item config\llm.example.json config\llm.local.json
```

The first round profiles are `deepseek`, `qwen`, `kimi`, `gpt`, `claude`, and `gemini`. Do not commit `config/llm.local.json`.

## 2. Freeze the V-MSR Text compiler cache

Compile Text rules once with the fixed compiler profile. Do not rebuild this cache separately for each decision model.

```powershell
python experiments\build_policy_cache.py `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --cache data\policy_cache\vmsr_text_v3.jsonl `
  --profile deepseek `
  --run `
  --resume
```

Record the compiler model name shown by this command. The examples below use `deepseek-chat`; replace it only if your manifest was compiled with a different model.

## 3. Fixed eight-method matrix

Every model must run this exact list:

```text
no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,vmsr_text_guard_noisy,oracle_minimal
```

First produce a no-API prompt preview for each profile. For example:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,vmsr_text_guard_noisy,oracle_minimal `
  --profile qwen `
  --vmsr-cache data\policy_cache\vmsr_text_v3.jsonl `
  --vmsr-compiler-model deepseek-chat `
  --tag multi_300_qwen_vmsr_v3
```

Then run each configured profile independently. The following is the DeepSeek command; change `--profile` and `--tag` for `qwen`, `kimi`, `gpt`, `claude`, and `gemini`.

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,vmsr_text_guard_noisy,oracle_minimal `
  --profile deepseek `
  --temperature 0 `
  --max-tokens 300 `
  --vmsr-cache data\policy_cache\vmsr_text_v3.jsonl `
  --vmsr-compiler-model deepseek-chat `
  --tag multi_300_deepseek_vmsr_v3 `
  --run `
  --resume
```

If a provider rejects JSON-mode response formatting, append `--no-json-mode`; the parser still normalizes the returned decision. Keep this exception in the experiment log.

## 4. Validate and compare the completed runs

Only run this after every profile has all 300 episodes for all eight methods. It rejects incomplete runs and cross-profile episode-grid mismatches.

```powershell
python experiments\compare_models.py `
  --inputs outputs\logs\multi_300_deepseek_vmsr_v3_llm_results.jsonl,outputs\logs\multi_300_qwen_vmsr_v3_llm_results.jsonl,outputs\logs\multi_300_kimi_vmsr_v3_llm_results.jsonl,outputs\logs\multi_300_gpt_vmsr_v3_llm_results.jsonl,outputs\logs\multi_300_claude_vmsr_v3_llm_results.jsonl,outputs\logs\multi_300_gemini_vmsr_v3_llm_results.jsonl `
  --profiles deepseek,qwen,kimi,gpt,claude,gemini `
  --methods llm_no_policy,llm_carried_policy,llm_all_policy_clean,llm_msr_clean,llm_all_policy_noisy,llm_msr_noisy,llm_vmsr_text_guard_noisy,llm_oracle_minimal `
  --reference llm_msr_noisy `
  --expected-episodes 300 `
  --bootstrap-samples 2000 `
  --tag multimodel_300_vmsr
```

Outputs:

```text
outputs/tables/multimodel_300_vmsr_model_summary.csv
outputs/tables/multimodel_300_vmsr_paired_deltas.csv
```

The paired-delta table reports each method against `llm_msr_noisy` on identical episodes. For safety rates, a negative delta is an improvement; for accuracy and task-success, a positive delta is an improvement.
