# SafeMemBench-Action 中文稿论证审计

## 一、紧凑结构

- 引言：从工具动作后果引出 action boundary，再定义 policy carriage 与四类失效。
- 相关工作：工具安全、长上下文压缩、策略检索三条线共同指向“策略状态到动作决策”的缺口。
- 基准：定义决策任务、五类状态、六领域配额、策略来源和泄露边界。
- 实验协议：四个 RQ、七类上下文、四个完整模型、统一指标与压缩 sanity check。
- 结果：先 failure-error mapping，再 clean 成本收益、noisy 边界、跨模型异质性和真实压缩对应。
- 讨论：MSR 仅为低上下文基线；V-MSR 只保留一段冻结负面结果。
- 结论：回到 benchmark insight，不以方法胜利收尾。

## 二、反向提纲

| 章节 | 首要信息 | 证据或解释 |
| --- | --- | --- |
| 摘要 | 策略可能存在却未正确到达动作边界 | 300 对双语数据、四模型英文结果、40 条压缩检查 |
| 引言 | policy carriage 是独立于普通 recall 的安全问题 | unsafe execution 与 false refusal 的方向不对称 |
| 相关工作 | 现有工具安全、压缩和检索没有直接测量该转化 | 三类工作各自的目标与本文测量目标不同 |
| 基准 | 受控状态与策略源隔离使 failure-error mapping 可测 | 6 domain × 50、180 risky/120 safe、标签隔离 |
| 协议 | 比较的是不同策略上下文，而非宣称新 SOTA 方法 | 七类 context、统一 LLM decision、oracle 仅诊断 |
| RQ1 | 四类失效产生不同错误类型 | DeepSeek 300 条 carried-policy state table |
| RQ2 clean | MSR 大幅降低策略上下文并保持较高效用 | 958.87→23.15 tokens；四模型 accuracy 95.67%--98.33% |
| RQ2 noisy | 最小检索不能消除污染池误拒 | 四模型 MSR noisy FR 20.67%--21.00% |
| RQ3 | 方向复现但模型先验不同 | no-policy/carried-policy 四模型对照 |
| RQ4 | 真实压缩能产生至少 absent/over-included | truncation 8/8 absent、3/8 violation；recursive 1/8 over-included |
| 讨论 | 未来问题是有效性/作用域/冲突验证和校准 | noisy 边界与 preliminary verification 负面结果 |

## 三、Claim–Evidence Map

| Claim | Evidence | Status |
| --- | --- | --- |
| 策略携带失效产生结构化动作错误 | `carried_failure_by_state_300.csv`：absent/weakened/misbound 高违规，over-included 100% 误拒 | **Supported（受控 DeepSeek 条件）** |
| 基准包含 300 对双语 episode、六领域和五状态 | 生成器、双语 JSONL、配额测试 | **Supported；投稿前需给数据统计脚本引用** |
| clean MSR 将策略 token 降低约 41.4 倍 | `main_results_300.csv`：958.87/23.15 | **Supported** |
| clean MSR 保持高但模型相关的效用 | 四模型 accuracy 95.67%--98.33%，违规均为 0 | **Supported** |
| noisy MSR 不能消除约 21% 误拒 | 四模型 noisy summary，FR 20.67%--21.00% | **Supported** |
| carried policy 在四模型上明显弱于 clean source | 四模型 carried accuracy 43.33%--54.00% | **Supported** |
| 真实压缩可产生受控状态 | `compression_sanity_40.csv` | **Supported as plausibility only** |
| 方法不存在答案字段泄露 | agent API、policy source tests、label separation tests | **Supported by code；投稿前需列出测试文件/commit** |
| 结论可推广到中文决策 | 当前无中文 LLM 主实验 | **Not supported；正文已避免该主张** |
| GPT 结果代表 OpenAI 官方模型 | 中转站只提供 advertised ID | **Not supported；正文已明确限定** |

## 四、五维对抗性自审

### 1. Contribution

- **Pass：** 新意定位为受控 benchmark、failure-error taxonomy 与 leakage-aware policy-source schema，而非普通 RAG 改进。
- **风险：** reviewer 可能认为四类 corruption 是人工构造。40 条 sanity check 只能缓解合理性问题，不能估计 prevalence。
- **需要补强：** 在附录加入每类状态的生成原则、反例和人工审查协议。

### 2. Writing Clarity

- **Pass：** action boundary、policy carriage、carried/noisy/canonical source 和 oracle diagnostic 已分别定义。
- **Pass：** 每个结果小节先直接回答 RQ，再给表格与边界解释。
- **Needs revision：** 正式投稿前统一中英文术语格式，并补齐 Figure/Table 交叉引用编号。

### 3. Experimental Strength

- **Pass：** 四个完整模型均覆盖同一 300 条与七方法，方向性复现明确。
- **Pass：** 同时报告 violation、false refusal 和 token cost，未隐藏 noisy 失败。
- **Needs new analysis：** 生成四模型 episode-level paired bootstrap CI；当前不能使用显著性措辞。
- **Needs caution：** GPT 为网关宣称模型，单独报告，不参与“官方模型”结论。

### 4. Evaluation Completeness

- **Needs new experiment/decision：** 中文数据已发布但中文动作评测未完成；需补跑或明确 release-only。
- **Needs new analysis：** 压缩标注缺少双人盲标与一致性系数。
- **Needs appendix：** BM25/hash-vector/Hybrid 历史结果不进入主线，但可作为 appendix retrieval diagnostics；不得重新包装为主贡献。
- **Pass with scope：** 作为 benchmark paper，不要求 MSR 组件消融支撑主贡献；MSR 仅为 baseline。

### 5. Method Design Soundness

- **Pass：** 标签隔离与策略来源拆分解决了早期实现中的 clean-pool leakage 风险。
- **风险：** 单动作边界无法代表完整闭环恢复和执行后补救。
- **风险：** 合成 predicate/schema 可能使 action applicability 过于规则化。
- **未来方向：** 在真实组织策略、策略版本冲突和多步执行轨迹上验证 taxonomy。

## 五、投稿前阻断项

1. 补齐并核验所有参考文献，删除全部“待补引用”。
2. 生成四模型 paired bootstrap CI 与完整 denominator 表。
3. 决定中文评测是补跑还是明确列为 release-only。
4. 为压缩 sanity check 增加双人标注与一致性。
5. 冻结 Figure 3 四模型 source data，并更新所有旧的两模型图注。
6. 记录模型 profile、API 日期、prompt hash、代码 commit 与网关 provenance。
