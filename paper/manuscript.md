# SafeMemBench-Action: Evaluating Policy-Carriage Failures in Long-Horizon LLM Agents at the Action Level

> Draft status: Introduction, Methods, Experiments and Discussion. Citation placeholders are retained until a dedicated literature search is completed. Numerical claims are limited to completed 300-episode runs with DeepSeek and Qwen, plus a 40-instance compression sanity check.

## Introduction

Large language model (LLM) agents increasingly make consequential decisions through external tools. After reading user requests, organizational memory, retrieved documents and prior tool outputs, an agent may send a message, share a file, modify a database record, grant a browser permission or approve a payment. In each case, the immediate safety question is not merely whether a relevant policy appeared somewhere earlier in the trajectory. It is whether the policy's operative meaning is still available, correctly scoped and bound to the proposed action at the moment of execution [CITATION: tool-using agents; long-context memory; agent safety].

This action-boundary requirement is easy to lose in long-horizon agent pipelines. Policies can be compressed into summaries, displaced by later context, retrieved alongside similar but inapplicable rules, or restated with a changed object or condition. An agent may therefore possess a valid organizational policy without carrying the part of that policy needed to decide the next tool call. The resulting error is consequential in two directions: missing or weakened constraints can permit an unsafe action, while overly broad or irrelevant constraints can unnecessarily stop a safe one.

We term this phenomenon **policy carriage**: the preservation of a policy's decision effect, scope and protected-object binding from long context to a candidate action. Policy carriage can fail as `absent`, `weakened`, `misbound` or `over-included`. These states are operationally distinct. Absent, weakened and misbound policies can remove the protection needed for a risky action; over-included policies can transform a permissible action into a refusal. Treating all four as generic retrieval or memory errors obscures this safety--utility asymmetry.

Prior work has investigated tool-use safety, instruction following, long-context memory, retrieval and context compression [CITATION: tool-use safety; instruction following; agent memory; retrieval; context compression]. Yet these settings rarely isolate how the state of a policy in long context changes the decision on one imminent tool action. Full policy replay offers nominal coverage but can be costly and can expose the decision model to irrelevant or conflicting restrictions. Similarity-oriented retrieval reduces context length, but policy relevance alone does not establish applicability to the visible action or prevent a broad policy from overriding a safe task. Consequently, existing evaluations make it difficult to distinguish a failure to retrieve a policy from a failure to carry its operative meaning correctly.

We introduce **SafeMemBench-Action**, a leakage-controlled benchmark for measuring policy carriage at the action boundary. The benchmark contains 300 bilingual episodes spanning email, file, calendar, Slack, database and browser domains. It balances five policy states with risky and safe actions, enabling evaluation of executed violations and false refusals rather than safety violations alone. Its schema separates the canonical policy registry, corruption artifacts, noisy policy pool and carried policy from offline-only annotations. Retrieval and decision methods are prohibited from reading `required_policy_ids`, expected decisions, allowed decisions or ground-truth policy lists, so policy selection cannot silently use answer-bearing fields.

Our completed experiments make the benchmark's central distinction concrete. On the carried-policy condition, the four failure states lead to sharply different error patterns: absence, weakening and misbinding primarily yield unsafe allows or insufficient confirmation, whereas over-inclusion yields systematic false refusal. Under a clean policy registry, Minimal Sufficient Policy Retrieval (MSR) matches full replay on the completed DeepSeek and Qwen runs while using far fewer policy tokens. Under noisy pools, however, both full replay and MSR remain over-conservative, showing that minimal context alone does not resolve policy-pool corruption. A 40-instance compression sanity check further shows that truncation can naturally induce policy absence and downstream unsafe execution.

Our contributions are threefold:

1. **Benchmark.** We introduce SafeMemBench-Action, a bilingual 300-episode benchmark that operationalizes five policy-carriage states at the tool-action boundary across six tool-use domains.
2. **Failure--error taxonomy.** We isolate how policy absence, weakening, misbinding and over-inclusion map to unsafe execution, under-blocked confirmation and false refusal, thereby evaluating both safety and utility.
3. **Controlled empirical evidence.** We compare no-policy, carried-policy, full-replay and MSR contexts in completed DeepSeek and Qwen runs, quantifying the clean-context token advantage of minimal retrieval and the unresolved false-refusal problem under noisy policy pools.

## Methods

### Problem formulation

An episode contains a task goal, long interaction context, a candidate tool action $a$, and one or more policy collections. The candidate action consists of a tool identifier and the arguments visible immediately before execution. A method returns a decision from

$$
\mathcal{D}=\{\texttt{allow},\ \texttt{revise},\ \texttt{ask\_confirmation},\ \texttt{block}\}.
$$

Offline annotations specify the allowed decisions for each episode. A decision is correct when it belongs to this set. An **executed violation** occurs when a risky action is allowed. A **false refusal** occurs when a safe action whose expected outcome is `allow` receives any non-allow decision. Offline labels are consulted only after a decision is logged.

### Benchmark design and policy states

SafeMemBench-Action contains 300 English and Chinese episode pairs across six domains: email, file, calendar, Slack, database and browser. Each domain has 50 episodes, with ten episodes for each policy state. The resulting dataset has 180 risky and 120 safe actions. Risky cases include external disclosure, protected deletion, sensitive-data modification, credential handling, risky permission grants and payment approval. Safe cases include internal non-sensitive communication, public-document access, aggregate queries and read-only search.

The benchmark uses five states. `policy_preserved` is a control condition in which the operative policy and its object binding remain intact. `policy_absent` removes the operative policy from carried context. `policy_weakened` preserves the topic but loses decision strength or a decisive condition. `policy_misbound` attaches a policy to an incorrect object, recipient or scope. `policy_over_included` activates an unjustifiably broad restriction in a safe case.

Each episode stores semantically distinct policy collections. The `canonical_policy_registry` contains valid canonical policies and clean irrelevant policies. The `corruption_artifacts` collection contains weakened, misbound, conflicting or overly broad policy entries. Their union forms the `noisy_policy_pool`. `carried_policy` represents policy content actually available after long-context processing. `ground_truth_policies` and `required_policy_ids` are offline annotations only. This design makes it possible to distinguish a method that retrieves a valid policy source from one that merely receives an answer-bearing label.

### Decision baselines

We compare seven policy-context baselines. **No policy** supplies no policy context. **Carried policy** supplies only the policy content propagated through the episode context. **All-policy clean** and **all-policy noisy** replay the full canonical registry or noisy pool, respectively. **MSR clean** and **MSR noisy** apply Minimal Sufficient Policy Retrieval (MSR) to the corresponding source. MSR is an applicability-oriented baseline: it selects a small policy context based on the candidate action's tool, object and visible conditions, but it does not use offline labels. Finally, a **policy-list diagnostic** receives the annotated minimal policy list; it is a diagnostic ceiling for policy-list selection, not an action-level decision oracle.

### Metrics and leakage controls

Primary metrics are decision accuracy, executed-violation rate, false-refusal rate and task-success rate. Task success requires an allowed decision with neither an executed violation nor a false refusal. We additionally report required-policy coverage, irrelevant-policy rate, average retrieved-policy count, average policy-token cost and total LLM tokens. Safe cases without a required policy are excluded from policy-coverage averaging.

Completed decision runs use temperature-zero DeepSeek and Qwen configurations with a 300-token response limit. The decision model receives only the task goal, candidate action and method-specific policy context. Retrieval and decision code must not read `required_policy_ids`, expected decisions, allowed decisions, forbidden decisions, `labels` or ground-truth policies. These fields are accessed only by the evaluator after the decision.

### Real-compression sanity check

The compression sanity check contains eight long-context seeds whose policies originate in early user instructions, organizational memory, loaded policy documents, dialogue history or retrieved memory. Each seed is processed by manual injection, a single LLM summary, a rolling summary, truncation and recursive summarization. Human annotation assigns the resulting carried policy to one of the five policy states before a downstream action decision is evaluated. This 40-instance study tests methodological plausibility rather than population prevalence.

## Experiments

### Questions and reporting scope

We ask four questions. **RQ1:** Do policy-carriage states yield distinct action-level error patterns? **RQ2:** What safety--utility--cost trade-off is created by replay and minimal retrieval? **RQ3:** Does this pattern persist across the completed DeepSeek and Qwen model runs? **RQ4:** Can real compression procedures induce failure states resembling the controlled taxonomy?

The primary evidence consists of completed 300-episode English runs with DeepSeek-V4-Flash and Qwen3.6-Flash. Values are exact episode proportions from temperature-zero runs. We report both models to check directional consistency, but do not treat two model instances as a sufficient basis for broad model-family inference. The 40-instance compression check is reported separately as a sanity experiment.

### Policy-carriage failures have distinct action-error signatures

The carried-policy baseline makes the failure taxonomy visible. In the DeepSeek run, preserved policy context was correct on all 60 episodes. In contrast, absent context produced 31 unsafe allows among 60 episodes (51.67%), weakened context produced 31 unsafe allows (51.67%) and 16 under-blocked confirmations, and misbound context produced 29 unsafe allows (48.33%). Over-included context produced no unsafe allows, but falsely refused all 60 safe episodes. The corresponding aggregate carried-policy accuracy was 43.33%, with a 30.33% executed-violation rate and a 20.33% false-refusal rate.

The no-policy baseline confirms that risky actions cannot be handled reliably without policy context: its executed-violation rate was 38.33% with DeepSeek and 27.33% with Qwen. Carried policy reduced unsafe execution to 30.33% and 25.00%, respectively, but introduced a 20.33% false-refusal rate for both models. Thus, corrupted policy carriage does not simply remove safety information; it changes the type of decision error.

### Minimal retrieval matches clean replay at a fraction of the context cost

Under the clean registry, full replay and MSR achieved nearly identical outcomes. DeepSeek obtained 98.33% accuracy with 0% executed violations for both methods; Qwen obtained 98.33% for full replay and 98.00% for MSR. However, clean MSR used 23.15 policy tokens per episode, compared with 958.87 tokens for full replay, a 41.4-fold reduction. It also retrieved 0.75 policies on average rather than 31.23.

The noisy setting exposes the limit of minimal retrieval. With DeepSeek, noisy full replay and noisy MSR achieved 79.67% and 79.33% accuracy, respectively, and both had approximately 20% false-refusal rates. Qwen showed the same pattern: 79.00% and 78.33% accuracy with 21.00% false refusal. MSR therefore preserves the cost advantage under noise, but it does not by itself resolve broad or conflicting policy artifacts that make a safe action appear restricted.

### The noisy-pool effect is consistent across completed models

The two completed model runs agree on the qualitative pattern. All-policy clean and MSR clean have near-zero violation and false-refusal rates, whereas all-policy noisy and MSR noisy retain zero or near-zero violation at the cost of roughly one fifth of actions being unnecessarily refused. This consistency supports a bounded claim: in the evaluated models and synthetic policy pools, policy-pool corruption primarily manifests as a utility loss rather than unsafe execution once a policy context is present.

### Real compression naturally produces controlled failure states

The 40-instance sanity check supports the plausibility of the controlled taxonomy. Truncation removed the operative policy in all eight seeds and yielded 37.5% downstream executed violations. Recursive summarization produced an over-included state in one seed, while the single LLM summary and rolling summary preserved the annotated policy in all eight seeds. These results are not prevalence estimates, but they show that at least absence and over-inclusion can arise from realistic context-processing procedures and affect downstream action decisions in the predicted direction.

## Discussion and limitations

SafeMemBench-Action is intentionally a controlled benchmark, so its policy texts, action schemas and corruption artifacts do not establish real-world prevalence. The completed evidence covers two decision models; the remaining planned model families, multilingual action evaluation and confidence intervals remain future work. The benchmark also measures a single action boundary rather than a full multi-step closed-loop trajectory.

We also evaluated a preliminary verification-guided retrieval extension outside the primary comparison. It reduced unsafe allowance in a targeted missing-evidence probe, but its frozen configuration was over-conservative on the 300-episode benchmark and increased false refusals for safe cases. We therefore do not present it as a main method contribution. This negative result motivates future work on calibrated uncertainty handling: action safety requires not only detecting unsupported policy predicates, but also distinguishing genuinely unresolved risk from irrelevant or overly broad constraints.
