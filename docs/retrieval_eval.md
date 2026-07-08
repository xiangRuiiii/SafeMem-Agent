# Retrieval Baselines

This experiment compares MSR with lexical and vector retrieval baselines before sending policies to the LLM.

## Methods

| method | source | top-k | meaning |
| --- | --- | --- | --- |
| `bm25_clean_top1/3/5` | `canonical_policy_registry` | 1/3/5 | lexical retrieval from the clean policy registry |
| `bm25_noisy_top1/3/5` | `noisy_policy_pool` | 1/3/5 | lexical retrieval from the noisy policy pool |
| `embedding_clean_top1/3/5` | `canonical_policy_registry` | 1/3/5 | local vector retrieval from the clean policy registry |
| `embedding_noisy_top1/3/5` | `noisy_policy_pool` | 1/3/5 | local vector retrieval from the noisy policy pool |
| `msr_clean` | `canonical_policy_registry` | adaptive | action-applicability retrieval |
| `msr_noisy` | `noisy_policy_pool` | adaptive | action-applicability retrieval from noisy pool |
| `oracle_minimal` | `ground_truth_policies` | minimal | oracle upper bound |

The current embedding baseline is a deterministic local hash-vector retriever with metadata-rich action and policy texts. It does not call an embedding API.

## Retrieval-Only

First run retrieval quality without LLM calls:

```powershell
cd D:\coder\SafeMem

python experiments\run_retrieval_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag retrieval_en_90_top3 `
  --method-set retrieval_top3
```

Inspect:

```powershell
Get-Content outputs\tables\retrieval_en_90_top3_retrieval_summary.csv
Get-Content outputs\tables\retrieval_en_90_top3_retrieval_by_state.csv
```

Run all top-k values:

```powershell
python experiments\run_retrieval_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag retrieval_en_90_all `
  --method-set retrieval_all
```

## LLM Decision With Retrieval

First run only top-3 retrieval baselines:

```powershell
python experiments\run_llm_eval.py `
  --episodes data\episodes\mvp_plus_90_en.jsonl `
  --tag llm_en_90_retrieval_top3 `
  --method-set retrieval_top3 `
  --profile deepseek `
  --run `
  --resume
```

Then inspect:

```powershell
Get-Content outputs\tables\llm_en_90_retrieval_top3_llm_summary.csv
Get-Content outputs\tables\llm_en_90_retrieval_top3_llm_by_state.csv
Get-Content outputs\tables\llm_en_90_retrieval_top3_llm_by_case.csv
```

The paper contrast is:

```text
BM25 and embedding retrieval select similar policies.
MSR selects action-applicable policies.
```
