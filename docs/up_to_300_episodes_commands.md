# Next-Stage Experiment Commands

All commands are meant to be run from the repository root.

## Generate Offline Data

```powershell
python scripts\make_mvp_plus_300.py
python scripts\make_compression_sanity.py
```

## Core 7-Method LLM Run

Dry run:

```powershell
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile deepseek --tag mvp300_deepseek_core --preview-count 1
```

Real run:

```powershell
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile deepseek --tag mvp300_deepseek_core --run --resume
```

## Six-Model Core Runs

```powershell
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile deepseek --tag mvp300_deepseek_core --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile qwen --tag mvp300_qwen_core --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile kimi --tag mvp300_kimi_core --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile gpt --tag mvp300_gpt_core --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile claude --tag mvp300_claude_core --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set base --profile gemini --tag mvp300_gemini_core --run --resume
```

## Retrieval-Only Experiments

Top-k curve:

```powershell
python experiments\run_retrieval_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set retrieval_all --tag mvp300_topk
```

MSR ablation:

```powershell
python experiments\run_retrieval_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set msr_ablation --tag mvp300_msr_ablation
```

Hybrid-MSR ablation:

```powershell
python experiments\run_retrieval_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set hybrid_ablation --tag mvp300_hybrid_ablation
```

## LLM Retrieval/Ablation Runs

```powershell
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set retrieval_all --profile deepseek --tag mvp300_deepseek_topk --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set msr_ablation --profile deepseek --tag mvp300_deepseek_msr_ablation --run --resume
python experiments\run_llm_eval.py --episodes data\episodes\mvp_plus_300_en.jsonl --method-set hybrid_ablation --profile deepseek --tag mvp300_deepseek_hybrid_ablation --run --resume
```

## Failure-Error Matrix

```powershell
python experiments\run_failure_matrix.py --episodes data\episodes\mvp_plus_300_en.jsonl --results outputs\logs\mvp300_deepseek_core_llm_results.json --tag mvp300_deepseek_core --group-by agent,policy_state
python experiments\run_failure_matrix.py --episodes data\episodes\mvp_plus_300_en.jsonl --results outputs\logs\mvp300_deepseek_core_llm_results.json --tag mvp300_deepseek_domain_state --group-by agent,domain,policy_state,case_type
```

## Lightweight Checks

```powershell
python -m compileall safemem experiments scripts tests
python -m unittest
```
