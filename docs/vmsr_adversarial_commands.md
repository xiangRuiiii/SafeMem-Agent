# V-MSR Adversarial Challenge

`vmsr_adversarial_36` is independent of `vmsr_challenge_72` and `vmsr_hard_noise_36`. It applies pressure to verification and minimum-proof selection with pools larger than BM25 top-8.

Each episode has at least 10 policies: canonical rules plus nine valid, same-tool adversarial policies. V-MSR evaluates the same-tool frontier before selecting the minimal certificate; the challenge therefore measures whether it can reject contradicted predicates, resolve provenance conflicts, and escalate missing evidence.

| Challenge type | Primary case | Paired case |
| --- | --- | --- |
| `crowded_predicates` | external confidential action: `block` | internal public action: `allow` |
| `authority_shadowing` | low-authority matching `allow` policies lose to canonical restrictions | low-authority matching `block` policies lose to canonical allow |
| `unknown_evidence` | missing `permission_risk`: `ask_confirmation` | explicit `permission_risk=low`: `allow` |

## 1. Generate the bilingual challenge

```powershell
python scripts\make_vmsr_adversarial.py
```

## 2. Compile missing Text manifests

Preview cache misses first:

```powershell
python experiments\build_policy_cache.py --episodes data\episodes\vmsr_adversarial_36_en.jsonl --cache data\policy_cache\vmsr_text_v3.jsonl --profile deepseek
```

Then compile resumably:

```powershell
python experiments\build_policy_cache.py --episodes data\episodes\vmsr_adversarial_36_en.jsonl --cache data\policy_cache\vmsr_text_v3.jsonl --profile deepseek --run --resume
```

## 3. Run retrieval-only comparison

```powershell
python experiments\run_retrieval_eval.py --episodes data\episodes\vmsr_adversarial_36_en.jsonl --methods all_policy_noisy,bm25_noisy_top3,bm25_noisy_top5,msr_noisy,hybrid_msr_noisy,oracle_minimal,vmsr_struct_context_noisy,vmsr_text_context_noisy,vmsr_text_guard_noisy --vmsr-cache data\policy_cache\vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_adversarial_retrieval
```

Inspect `unknown_escalation_rate`, `certificate_oracle_match`, `conflict_resolution_accuracy`, retrieved-policy count, irrelevant-policy rate, and token cost. `oracle_minimal` is only a minimal-policy-list diagnostic here: it does not receive V-MSR's verifier certificate or missing-evidence decision floor. The V-MSR context should be minimal; this challenge does not claim that BM25 top-8 alone determines applicability because V-MSR closes over the same-tool policy frontier before verification.

## 4. Run the focused DeepSeek LLM comparison

```powershell
python experiments\run_llm_eval.py --episodes data\episodes\vmsr_adversarial_36_en.jsonl --methods all_policy_noisy,bm25_noisy_top3,bm25_noisy_top5,msr_noisy,hybrid_msr_noisy,vmsr_struct_context_noisy,vmsr_struct_guard_noisy,vmsr_text_context_noisy,vmsr_text_guard_noisy,oracle_minimal --profile deepseek --vmsr-cache data\policy_cache\vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_adversarial_deepseek --run --resume
```

## 5. Build the error matrix by challenge type

```powershell
python experiments\run_failure_matrix.py --episodes data\episodes\vmsr_adversarial_36_en.jsonl --results outputs\logs\vmsr_adversarial_deepseek_llm_results.jsonl --group-by agent,challenge_type,verification_mode --tag vmsr_adversarial_deepseek
```

Use this set as a focused V-MSR robustness study. Do not replace the 300-episode main benchmark with it, and do not expand it to all six decision models unless the focused DeepSeek comparison reveals a meaningful mechanism difference.
