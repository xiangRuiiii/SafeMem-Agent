# SafeMemBench-Action Paper Outline

> Working title: **SafeMemBench-Action: Evaluating Policy-Carriage Failures in Long-Horizon LLM Agents at the Action Level**
>
> Paper type: benchmark and empirical safety study. The central contribution is a controlled, leakage-aware measurement framework, not a claim that MSR is a universally robust safety method.

## One-sentence thesis

When long-context processing changes the operative state of a policy before a tool call, the resulting action-level error is structured rather than random: absence, weakening and misbinding tend to permit unsafe actions, whereas over-inclusion tends to refuse safe actions.

## Evidence boundary

- Main benchmark: 300 bilingual episode pairs across email, file, calendar, Slack, database and browser.
- Completed English decision runs: DeepSeek, Qwen, Kimi and GPT-5.4-mini. Claude and GLM are incomplete and must not enter aggregate claims.
- Compression evidence: 40 instances; it is a plausibility sanity check, not a prevalence estimate.
- Do not make V-MSR, its challenge sets, top-k curves, Hybrid-MSR or unfinished ablations part of the main narrative. A frozen preliminary verification extension may receive one short limitation sentence in Discussion only.

## 0. Abstract (write last, 180--220 words)

**Purpose.** State the concrete problem, benchmark, central empirical finding and evidence boundary in one compact paragraph.

1. Open with the action-boundary problem: policies may exist earlier in context but be incorrectly carried when an agent acts.
2. Define the contribution: a leakage-controlled bilingual benchmark with five policy states, risky and safe actions, and distinct clean/noisy/carried policy sources.
3. Report only the headline findings: the failure--error mapping; clean MSR's large context-cost reduction with high but model-dependent utility; noisy pools' persistent false refusal.
4. Close with the implication: action safety must evaluate policy carriage and utility loss, not policy recall alone.

**Do not write.** A universal safety claim, a V-MSR claim, uncompleted model results, or a claim that the sanity check estimates real-world frequency.

## 1. Introduction

**Goal.** Create the reader's need for an action-level policy-carriage benchmark before introducing any method name.

| Paragraph | Role | What to write |
| --- | --- | --- |
| 1 | Opening problem | Tool-using LLM agents execute consequential actions. The relevant policy must be available, scoped and object-bound at execution time. |
| 2 | Concrete challenge | Summarization, later context, retrieval and restatement can alter the policy that reaches the next tool call; unsafe allowance and unnecessary refusal are both possible. |
| 3 | Concept | Define policy carriage and the four failure states: absent, weakened, misbound and over-included. Explain the safety--utility asymmetry. |
| 4 | Gap | Position tool-use safety, long-context memory, compression and retrieval work. Explain why replay and semantic relevance do not directly test action applicability. |
| 5 | Solution | Introduce SafeMemBench-Action, its 300 bilingual episodes, policy-source separation and leakage boundary. |
| 6 | Evidence preview | Preview only completed findings: structured failure-error signatures, low-cost clean MSR, and noisy-pool false refusal. |
| 7 | Contributions | State benchmark, failure--error taxonomy and controlled replay/retrieval evidence. |

**Required transition.** The final sentence must lead to a benchmark specification, not to an algorithm pipeline.

## 2. Related Work

**Goal.** Establish the precise gap without turning this section into a citation list. Use three focused subsections.

### 2.1 Tool-use and action-level agent safety

- Summarize work on tool-use constraints, action authorization, guardrails and risky tool execution.
- Distinction: this paper evaluates whether policy content survives long-context processing before the same action is selected; it does not claim a production-time guardrail.

### 2.2 Long-context memory and context compression

- Summarize memory, summarization and compression methods for agents.
- Distinction: previous metrics typically measure task retention or summary quality, while this work measures policy state and its downstream tool-action consequence.

### 2.3 Retrieval and policy-context selection

- Summarize retrieval-augmented agents and policy/instruction selection.
- Distinction: relevant retrieval is not equivalent to a correctly scoped policy for a visible action; full replay can also introduce false refusal.

**Ending sentence.** SafeMemBench-Action evaluates the missing transition: long-context policy state to immediate action decision.

## 3. SafeMemBench-Action

**Goal.** Define the benchmark and its leakage boundary precisely enough for reproduction.

### 3.1 Action-level decision task

- Define an episode: task goal, long context, candidate action and policy sources.
- Define the four outputs: `allow`, `revise`, `ask_confirmation`, `block`.
- Define correct decision, executed violation, false refusal and task success.

### 3.2 Policy-carriage taxonomy

- Define `policy_preserved` as the control condition.
- Define `policy_absent`, `policy_weakened`, `policy_misbound` and `policy_over_included` with one short action-level example each.
- State the directional hypotheses: first three risk unsafe execution; over-inclusion risks false refusal. Present these as benchmark hypotheses, not universal laws.

### 3.3 Episode design and coverage

- Report six domains, 50 episodes per domain, five policy states per domain and the 180 risky / 120 safe split.
- Explain risky and safe action families, bilingual pairing and why both case types are required.
- Use **Table 1** for counts by domain, state and case type.

### 3.4 Policy-source schema and corruption design

- Define `canonical_policy_registry`, `corruption_artifacts`, `noisy_policy_pool`, `carried_policy` and offline annotations.
- Explain that clean and noisy sources answer different questions: access to valid policies versus robustness to policy artifacts.
- Use **Figure 1** to show sources, long-context processing and the action boundary.

### 3.5 Leakage controls and dataset validation

- State explicitly that agents cannot read `required_policy_ids`, expected/allowed decisions, labels or ground-truth policies.
- Explain generator-level validation: bilingual ID alignment, state balance, pool membership and policy-source integrity.
- Describe these as experimental validity controls, not model features.

## 4. Experimental Protocol

**Goal.** Make every comparison fair and every metric interpretable.

### 4.1 Research questions

- **RQ1:** Do controlled policy states produce distinct action-level error signatures?
- **RQ2:** What safety--utility--context-cost trade-off do carried policy, full replay and MSR create under clean and noisy sources?
- **RQ3:** Which patterns persist across completed decision models?
- **RQ4:** Can real compression procedures instantiate the controlled states and predicted downstream errors?

### 4.2 Compared policy contexts

- Define `no_policy`, `carried_policy`, `all_policy_clean`, `all_policy_noisy`, `msr_clean`, `msr_noisy` and `oracle_minimal`.
- Clarify that oracle-minimal is an offline policy-list diagnostic, not a deployable action oracle.
- Use **Table 2**: each baseline's source, visible fields, expected role and whether it is deployable.

### 4.3 Models and inference settings

- Report model identifier, provider/API date, temperature, response limit, prompt version, retry policy and profile for every completed model.
- Current completed set: DeepSeek, Qwen, Kimi and GPT-5.4-mini. Report each model separately first; only report a macro summary with a clear aggregation rule.
- Place incomplete Claude and GLM attempts in an appendix note, not in a performance table.

### 4.4 Metrics and statistical reporting

- Primary: accuracy, executed-violation rate, false-refusal rate and task-success rate.
- Context diagnostics: policy coverage, irrelevant-policy rate, retrieved-policy count, policy-token cost and LLM total tokens.
- Report exact episode proportions and denominators. Add paired bootstrap confidence intervals only after generating them for all four complete models.

### 4.5 Compression sanity-check protocol

- Describe the 8 long-context seeds and five transformations: manual injection, LLM summary, rolling summary, truncation and recursive summary.
- Explain human policy-state annotation, blindness requirements and downstream decision protocol.
- State in the subsection opening that this is a methodological plausibility check.

## 5. Results

**Goal.** Organize by research question, not by method name. Every subsection begins with a direct answer, then gives evidence and interpretation.

### 5.1 RQ1: Policy-carriage failures have distinct action-error signatures

- Start with the headline: failures do not merely lower aggregate accuracy; they change the error type.
- Show carried-policy results by state, beginning with preserved control and then absent/weakened/misbound/over-included.
- Use **Figure 2** as the main failure--error matrix and **Table 3** for exact counts/proportions.
- Explain that over-inclusion needs safe cases to be visible; a violation-only metric would miss it.
- Keep this causal language bounded to the benchmark's controlled interventions.

### 5.2 RQ2: Clean minimal retrieval reduces context cost while retaining high utility

- Compare all-policy clean and MSR clean on each complete model.
- Lead with token reduction, then show accuracy, violation and false refusal.
- Use cautious language: "retains high utility" or "closely approaches replay", not "matches replay" across all models.
- Report model-dependent exceptions, especially GPT's higher clean-MSR false refusal.

### 5.3 RQ2: Noisy pools expose an unresolved false-refusal bottleneck

- Compare clean versus noisy results for all-policy and MSR within each model.
- Show that both methods remain safe on risky cases but often reject safe cases under noise.
- Use the safe/risky split to prove that the accuracy decline is a utility loss, not hidden unsafe allowance.
- State the conclusion plainly: minimization lowers token cost but is not a general solution to corrupted or over-broad policies.

### 5.4 RQ3: Cross-model replication and heterogeneity

- Use **Figure 3** or **Table 4** with one panel/row per complete model: DeepSeek, Qwen, Kimi and GPT-5.4-mini.
- Report directions shared across models: full clean context is high-performing; noisy context produces roughly one-fifth false refusal; carried policy is substantially worse than clean sources.
- Report differences rather than averaging them away: no-policy is much more conservative for Kimi/GPT than for DeepSeek, and clean MSR has a larger GPT utility gap.
- Frame the result as multi-model directional replication, not proof for all LLMs.

### 5.5 RQ4: Real compression can reproduce controlled failure states

- Use **Supplementary Figure S1** and a compact table.
- Report truncation's eight absent cases and three downstream violations; report the recursive-summary over-inclusion example.
- Explain the result's purpose: it establishes plausible correspondence between the controlled taxonomy and real context-processing behavior.

### 5.6 Error analysis and representative cases

- Give two short, fully anonymized examples: one risky action with a missing/weakened policy leading to unsafe allowance, and one safe action with an over-included policy leading to refusal.
- Tie each case to an already reported aggregate pattern; do not add a one-off claim.
- Put full domain-by-state matrices in the appendix.

## 6. Discussion and Limitations

**Goal.** State what the benchmark teaches, what it does not establish, and what the next research problem is.

### 6.1 Main implication

- A safe agent must be evaluated on whether it carries policy meaning to the action level, not only on whether it retrieved a lexically relevant policy.
- Safety evaluation must jointly report executed violations and false refusals.

### 6.2 What MSR does and does not show

- MSR is a useful low-context baseline under clean policy sources.
- The noisy-pool result shows that selecting fewer policies alone cannot resolve policy validity, scope or conflict errors.

### 6.3 Threats to validity

- Controlled synthetic policy/action schemas and unknown real-world prevalence.
- One-step action boundary rather than full closed-loop trajectories.
- Current English decision evaluation and four completed model profiles; model/API variation and repeat sampling remain limitations.
- Compression check is small and manually annotated.

### 6.4 Frozen preliminary extension

- One concise paragraph only: a preliminary verification-oriented extension helped in a targeted missing-evidence probe but was over-conservative on the 300-episode main benchmark.
- Do not name it in the title, abstract, contribution list, primary methods or primary results.
- Use it only to motivate calibrated uncertainty handling as future work.

## 7. Conclusion

**Goal.** Close on the benchmark insight, not on a method victory.

1. Restate the problem: policies can exist in long context yet fail to be carried to a tool action.
2. Restate the contribution: SafeMemBench-Action makes this transition observable with controlled states and leakage-aware policy sources.
3. State the strongest supported result: different states yield distinct safety/utility errors; minimal retrieval saves context under clean sources but noisy artifacts retain false refusal.
4. End with the research implication: future agent safety mechanisms must preserve and verify policy meaning at the action level while calibrating conservatism.

## Appendix and supplementary material

- Full bilingual dataset schema and field definitions.
- Domain templates and complete policy-state examples.
- Full prompts, model profiles, API dates and retry policy.
- Complete per-domain, per-state and per-model result tables.
- Failure-error matrix definitions and calculation details.
- Compression seed construction, annotation guide and all 40 annotations.
- Dataset validation tests and leakage-control tests.
- A reproducibility checklist, license and data/code availability statements.

## Required figures and tables

| Item | Core message | Status |
| --- | --- | --- |
| Fig. 1 | Benchmark schema: long context, policy sources, action boundary and offline labels | Required main figure |
| Fig. 2 | Policy state to error-type matrix | Required main figure |
| Fig. 3 | Four-model clean/noisy replay versus MSR: safety, utility and token cost | Required main figure after source-data freeze |
| Fig. S1 | Real-compression sanity check | Required supplementary figure |
| Table 1 | Dataset composition by domain, policy state and risky/safe type | Required |
| Table 2 | Baseline policy sources, visible fields and diagnostic role | Required |
| Table 3 | Exact carried-policy failure-state counts and rates | Required or supplementary, depending on space |
| Table 4 | Per-model core results and aggregation protocol | Required |

## Claims that must remain out of the manuscript for now

- A universal or state-of-the-art safety claim for MSR.
- A claim that all models behave identically.
- A claim that the 40-instance sanity check estimates real-world failure prevalence.
- Any performance claim for incomplete Claude or GLM runs.
- Any primary-result claim for uncompleted bilingual action evaluation, top-k curves, Hybrid-MSR or ablations.
