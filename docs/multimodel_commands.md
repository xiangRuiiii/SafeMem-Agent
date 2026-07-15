# Multi-Model Core Evaluation

This protocol tests whether policy-carriage conclusions survive a change of decision model. It freezes the English 300-episode benchmark, the seven core methods, prompt format, and temperature. Only the final decision-model profile changes.

## 1. Configure local profiles

Copy the tracked template to the ignored local file and fill in only the keys and model identifiers you intend to use:

```powershell
Copy-Item config\llm.example.json config\llm.local.json
```

The first round profiles are `deepseek`, `qwen`, `kimi`, `glm`, `gpt`, `claude`, and `gemini`. Do not commit `config/llm.local.json`.

`glm` uses the configured OpenAI-compatible gateway and its advertised `glm-5.2` model. The profile sends `store=false` and `thinking.type=disabled` to keep the decision protocol and cost comparable to the other models. Record the gateway URL, date, and advertised model identifier in the final experiment log; do not describe this run as a direct Zhipu official API result.

## 2. Fixed seven-method matrix

Every model must run this exact list:

```text
no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,oracle_minimal
```

First produce a no-API prompt preview for each profile. The local `qwen` profile uses the Beijing Model Studio OpenAI-compatible endpoint and `qwen3.6-plus` by default.

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,oracle_minimal `
  --profile qwen `
  --tag multi_300_qwen_core
```

Then run each configured profile independently. The following command runs Qwen:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,oracle_minimal `
  --profile qwen `
  --temperature 0 `
  --max-tokens 300 `
  --tag multi_300_qwen_core `
  --run `
  --resume
```

`qwen3.6-plus` supports structured output through the compatible API, so keep JSON mode enabled. If the endpoint returns a response-format error, append `--no-json-mode`; the parser still normalizes the returned decision. Record that exception in the experiment log.

### Kimi K2.6 (non-thinking)

The `kimi` profile must set `request_options.thinking.type` to `disabled` and list `temperature` in `omit_request_fields`. Kimi K2.6 enables thinking by default and does not accept a configurable temperature. The tracked template already shows both fields.

```powershell
python scripts\run_llm_resume.py --max-restarts 12 --restart-delay 30 -- `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,oracle_minimal `
  --profile kimi `
  --max-tokens 300 `
  --tag multi_300_kimi_core `
  --run `
  --resume
```

Do not pass `--temperature` for Kimi. If its endpoint rejects OpenAI-style JSON mode, append `--no-json-mode` and record that protocol difference.

### GLM, GPT, Claude, and Gemini

The tracked local template contains ready-to-fill profiles. The default models are gateway-provided `glm-5.2` (thinking disabled), `gpt-5.4-mini` (low reasoning), `claude-haiku-4-5`, and `gemini-3.5-flash` (low thinking). Run one profile at a time with a distinct tag; the recovery wrapper resumes only that tag.

```powershell
python scripts\run_llm_resume.py --max-restarts 12 --restart-delay 30 -- `
  --episodes data\episodes\mvp_plus_300_en.jsonl `
  --methods no_policy,carried_policy,all_policy_clean,msr_clean,all_policy_noisy,msr_noisy,oracle_minimal `
  --profile glm `
  --temperature 0 `
  --max-tokens 300 `
  --tag multi_300_glm_core `
  --run `
  --resume
```

For the other profiles, replace both `--profile glm` and its tag consistently: `gpt` / `multi_300_gpt54mini_core`, `claude` / `multi_300_claude_haiku45_core`, or `gemini` / `multi_300_gemini_core`. Both `gpt` and `claude` use the configured OpenAI-compatible gateway; their advertised models are `gpt-5.4-mini` and `claude-haiku-4-5`. Keep the same 300 episodes and seven methods for all model comparisons.

### Legacy gateway profile

The primary `gpt` profile now maps the gateway fields directly: `baseURL` to `base_url`, `apiKey` to `api_key`, and the advertised model identifier to `model`. `gpt_proxy` remains only as a backward-compatible alias for an interrupted run; do not use it for new experiments.

For paper reporting, record the gateway URL, date, advertised model ID, and the exact profile JSON. Do not describe a gateway run as an official OpenAI API result unless the provider and model identity can be independently verified.

### Gateway model guard

For a gateway-routed model, use `--require-returned-model MODEL_ID`. The runner checks the model ID returned by every response and stops before writing a mismatched result. The Haiku rerun must use `--require-returned-model claude-haiku-4-5`.

## 3. Validate and compare the completed runs

Only run this after every profile has all 300 episodes for all seven methods. It rejects incomplete runs and cross-profile episode-grid mismatches.

```powershell
python experiments\compare_models.py `
  --inputs outputs\logs\multi_300_deepseek_core_llm_results.jsonl,outputs\logs\multi_300_qwen_core_llm_results.jsonl,outputs\logs\multi_300_kimi_core_llm_results.jsonl,outputs\logs\multi_300_gpt_core_llm_results.jsonl,outputs\logs\multi_300_claude_core_llm_results.jsonl,outputs\logs\multi_300_gemini_core_llm_results.jsonl `
  --profiles deepseek,qwen,kimi,gpt,claude,gemini `
  --methods llm_no_policy,llm_carried_policy,llm_all_policy_clean,llm_msr_clean,llm_all_policy_noisy,llm_msr_noisy,llm_oracle_minimal `
  --reference llm_msr_noisy `
  --expected-episodes 300 `
  --bootstrap-samples 2000 `
  --tag multimodel_300_core
```

Outputs:

```text
outputs/tables/multimodel_300_core_model_summary.csv
outputs/tables/multimodel_300_core_paired_deltas.csv
```

The paired-delta table reports each method against `llm_msr_noisy` on identical episodes. For safety rates, a negative delta is an improvement; for accuracy and task-success, a positive delta is an improvement.
