# V-MSR Hard-Noise Commands

`vmsr_hard_noise_36` 是独立 held-out challenge，不修改或覆盖既有 72 条 V-MSR 机制验证集。

## 1. Generate the bilingual hard-noise set

```powershell
python scripts/make_vmsr_hard_noise.py
```

Expected console summary:

```text
episodes=36 domains=6 risky=18 safe=18 hard_noise_types=3 bilingual=1
```

## 2. Compile only the new Text policies

Preview cache misses without an API call:

```powershell
python experiments/build_policy_cache.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --cache data/policy_cache/vmsr_text_v3.jsonl --profile deepseek
```

Then compile missing manifests. Existing v3 entries are reused:

```powershell
python experiments/build_policy_cache.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --cache data/policy_cache/vmsr_text_v3.jsonl --profile deepseek --run --resume
```

## 3. Run retrieval-only verification

First compare Struct/Text clean and noisy V-MSR:

```powershell
python experiments/run_retrieval_eval.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --method-set vmsr --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_hard_noise_en_v3
```

Then compare noisy retrieval baselines with V-MSR:

```powershell
python experiments/run_retrieval_eval.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --methods bm25_noisy_top3,embedding_noisy_top3,msr_noisy,hybrid_msr_noisy,oracle_minimal,vmsr_text_context_noisy --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_hard_noise_retrieval_compare
```

## 4. Run the LLM comparison after retrieval passes

V-MSR Context/Guard only:

```powershell
python experiments/run_llm_eval.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --method-set vmsr --profile deepseek --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_hard_noise_deepseek --run --resume
```

Noisy baseline comparison:

```powershell
python experiments/run_llm_eval.py --episodes data/episodes/vmsr_hard_noise_36_en.jsonl --methods bm25_noisy_top3,msr_noisy,hybrid_msr_noisy,vmsr_text_context_noisy,vmsr_text_guard_noisy,oracle_minimal --profile deepseek --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_hard_noise_compare --run --resume
```

## Interpretation

- `predicate_contradiction`: 同工具但 predicate 被候选动作明确反证。
- `semantic_neighbor`: 同工具、语义相邻，但 private/confidential/public 的条件不同。
- `authority_competition`: 同工具、真实匹配的低权威旧策略必须被高权威具体策略覆盖。

该集的目标不是让 noisy 必然降低 V-MSR，而是验证 V-MSR 的事实验证和来源解析可以拒绝有效但不适用的策略。
