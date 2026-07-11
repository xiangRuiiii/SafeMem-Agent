# Verification-Guided MSR Commands

以下命令由用户本地执行。它们会读取或生成较大的数据文件，Codex 不会代为运行。

## 1. Generate the bilingual challenge set

```powershell
python scripts/make_vmsr_episodes.py
```

Expected console summary:

```text
episodes=72 domains=6 risky=36 safe=36 challenge_types=6 bilingual=1
```

## 2. Build the V-MSR-Text policy manifest cache

先只编译 72 条挑战集，减少调试阶段 API 成本。以下命令只预览 cache miss，不调用 API：

```powershell
python experiments/build_policy_cache.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --cache data/policy_cache/vmsr_text_v3.jsonl --profile deepseek
```

确认后编译挑战集策略；`--resume` 会复用已完成记录：

```powershell
python experiments/build_policy_cache.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --cache data/policy_cache/vmsr_text_v3.jsonl --profile deepseek --run --resume
```

挑战集达标后，再向同一缓存补齐 300 条主集策略：

```powershell
python experiments/build_policy_cache.py --episodes data/episodes/mvp_plus_300_en.jsonl,data/episodes/vmsr_challenge_72_en.jsonl --cache data/policy_cache/vmsr_text_v3.jsonl --profile deepseek --run --resume
```

v3 manifest 使用 `tool + normalized predicates + effect`，不会复用 v2 的自由 object/condition 输出。

## 3. Run retrieval-only V-MSR evaluation

```powershell
python experiments/run_retrieval_eval.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --method-set vmsr --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_challenge_en_v3
```

新指标口径：

- `certificate_internal_validity`：证书自身的 entailed/unknown/conflict 记录是否自洽。
- `certificate_validity`：必要策略是否被证书覆盖；存在 required policy 时，空证书计为失败。
- `certificate_minimality`：算法删除测试得到的最小性。
- `certificate_oracle_match`：证书 policy IDs 是否与隐藏标注完全一致。
- `decision_stability`：不存在 unknown 或未解决冲突时才为真。

When an OpenAI-compatible embedding endpoint is configured, V-MSR can replace BM25 candidate recall with true Dense Embedding. This calls the embedding API only after the explicit flag:

```powershell
python experiments/run_retrieval_eval.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --method-set vmsr --vmsr-retrieval dense --embedding-profile qwen --run-dense --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_challenge_dense_v3
```

## 4. Run V-MSR Context and Guard with an LLM

Preview prompts first; do not add `--run` for the preview:

```powershell
python experiments/run_llm_eval.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --method-set vmsr --profile deepseek --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_challenge_deepseek_v3
```

Run the API evaluation with resume enabled:

```powershell
python experiments/run_llm_eval.py --episodes data/episodes/vmsr_challenge_72_en.jsonl --method-set vmsr --profile deepseek --vmsr-cache data/policy_cache/vmsr_text_v3.jsonl --vmsr-compiler-model deepseek-chat --tag vmsr_challenge_deepseek_v3 --run --resume
```

## 5. Run the real compression sanity check

```powershell
python scripts/make_compression_sanity.py
python experiments/run_compression.py --profile deepseek
python experiments/run_compression.py --profile deepseek --run --resume
```

After manually filling `data/annotations/compression_labels_template.csv`:

```powershell
python experiments/analyze_compression.py --results data/compression_sanity/compressed_deepseek.jsonl --labels data/annotations/compression_labels_template.csv --tag compression_deepseek
```
