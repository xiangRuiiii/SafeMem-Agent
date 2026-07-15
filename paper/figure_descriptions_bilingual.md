# SafeMemBench-Action 图表描述（中英文）

> 本文件仅描述 benchmark-centered 稿件中的活动图表。历史验证原型的图件不应进入主稿或补充材料，除非未来以新的主实验重新验证。

## Figure 1 | Benchmark design and policy-carriage states / 基准设计与策略携带状态

**中文描述。** 图 1 展示 SafeMemBench-Action 的因果链：策略首先出现在长程上下文中，经过摘要、检索或截断后以 preserved、absent、weakened、misbound 或 over-included 状态抵达候选工具动作。随后，评测器将动作决策归为正确、执行违规、确认不足或误拒。图中同时区分 canonical policy registry、corruption artifacts、noisy policy pool、carried policy 以及仅供离线评测的标注字段，强调策略选择与决策不能读取答案标签。

**English description.** Figure 1 presents the causal chain in SafeMemBench-Action. A policy originates in long context and reaches a candidate tool action as preserved, absent, weakened, misbound, or over-included after summarization, retrieval, or truncation. The action decision is then evaluated as correct, unsafe execution, under-blocked confirmation, or false refusal. The diagram distinguishes the canonical registry, corruption artifacts, noisy pool, carried policy and offline-only annotations, making the leakage boundary explicit.

**正文可用结论 / Claim suitable for the text.** Policy carriage is a measurable transition from long-context policy state to action-level safety behavior, rather than an undifferentiated memory or retrieval error.

## Figure 2 | Failure state to action-error matrix / 策略状态到动作错误矩阵

**中文描述。** 图 2 汇总 300 条 DeepSeek carried-policy 结果。preserved 为对照条件；absent、weakened 与 misbound 主要形成不安全允许或确认不足；over-included 则集中形成安全任务的误拒。可用热图展示每个 policy state 下的 correct、unsafe allow、under-blocked confirmation 与 false refusal 比例，并在旁边标注风险/安全 case 数。

**English description.** Figure 2 summarizes the 300-episode DeepSeek carried-policy run. Preserved policy is the control condition; absent, weakened and misbound policy primarily produce unsafe allows or under-blocked confirmations; over-included policy produces concentrated false refusal on safe tasks. A heatmap should report the proportions of correct, unsafe-allow, under-blocked-confirmation and false-refusal outcomes by policy state, with risky and safe case counts shown alongside.

**正文可用结论 / Claim suitable for the text.** Different policy-carriage failures are associated with different action-error signatures, so safety evaluation must report both violation and false-refusal outcomes.

## Figure 3 | Replay, minimal retrieval and noisy pools / 全量回放、最小检索与噪声策略池

**中文描述。** 图 3 使用 DeepSeek 与 Qwen 的 300 条核心实验，比较 all-policy clean/noisy、MSR clean/noisy、carried policy 与 no policy。主面板同时呈现准确率、执行违规率、误拒率和平均策略 token。clean 条件下 MSR 与全量回放性能接近，但策略 token 大幅下降；noisy 条件下，MSR 保留成本优势，却仍伴随约五分之一的误拒。建议使用两模型并列分面图，并在 token 轴上采用对数刻度。

**English description.** Figure 3 compares all-policy clean/noisy, MSR clean/noisy, carried policy and no policy on the completed 300-episode DeepSeek and Qwen runs. The main panel reports accuracy, executed-violation rate, false-refusal rate and average policy tokens. Under clean sources, MSR nearly matches full replay with dramatically fewer policy tokens. Under noisy sources, MSR retains its cost advantage but still shows approximately one-fifth false refusal. Use matched model facets and a logarithmic token-cost axis.

**正文可用结论 / Claim suitable for the text.** Minimal retrieval solves the clean-context cost problem, but it does not by itself solve over-conservatism induced by noisy policy pools.

## Supplementary Figure 1 | Real-compression sanity check / 真实上下文压缩 sanity check

**中文描述。** 补充图 1 按压缩方法展示 8 个长上下文 seed 的人工策略状态标注及下游动作结果。manual injection、单次摘要、rolling summary、截断和递归摘要各含 8 条实例。图应突出截断导致策略缺失及其后的违规，以及递归摘要中出现的 over-included 个例；同时明确该图检验分类合理性，不估计真实发生率。

**English description.** Supplementary Figure 1 reports human policy-state annotations and downstream action outcomes for eight long-context seeds under manual injection, single LLM summary, rolling summary, truncation and recursive summarization. The figure highlights policy absence after truncation and its downstream violations, together with an over-included recursive-summary case. It tests the plausibility of the controlled taxonomy and is not a prevalence estimate.

**正文可用结论 / Claim suitable for the text.** Controlled policy-carriage states can arise from real context-processing procedures and have the predicted downstream error direction.
