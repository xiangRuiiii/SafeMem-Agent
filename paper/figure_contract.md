# Figure Contract

## Paper-level conclusion

Policy-carriage failures produce distinct action-level safety errors. Minimal retrieval preserves the efficiency of full policy replay in clean policy sources, but both replay and retrieval remain vulnerable to false refusal when noisy policy artifacts enter the decision context.

## Evidence logic

| Figure | Question | Evidence | Intended conclusion |
|---|---|---|---|
| Fig. 1 | What is policy carriage and what does the benchmark control? | Benchmark schematic and policy-source schema | Policy state must be evaluated at the action boundary, with clean, noisy, carried and offline-only fields separated. |
| Fig. 2 | Do policy-carriage states cause distinct action errors? | Completed 300-episode DeepSeek failure matrix | Absence, weakening and misbinding increase unsafe execution; over-inclusion produces false refusal. |
| Fig. 3 | What is the safety--utility--cost trade-off of replay and minimal retrieval? | Completed 300-episode DeepSeek and Qwen core runs | MSR matches clean replay with far fewer tokens, but noisy policy artifacts create false refusal for both approaches. |
| Fig. S1 | Can realistic compression reproduce the controlled states? | Completed 40-instance compression sanity check | Truncation induces absence and downstream violations; recursive summarization can over-include. |

## Visual and statistical rules

- Backend: Python with Matplotlib only.
- Main-figure width: 183 mm-equivalent (`7.2 in`); minimum text size: 7 pt.
- Palette: color-blind-aware blue, vermilion, green, amber and neutral grey.
- Present exact episode proportions and state the evaluation size in every panel. Add uncertainty intervals only after the planned expanded multi-model analysis is complete.
- Primary exports: editable SVG and PDF; review exports: 300-dpi PNG and 600-dpi TIFF.
- Source data are stored in `paper/source_data/`; scripts never call an LLM API.

## Review risks

1. The benchmark is synthetic and currently evaluated on two completed decision models.
2. The full six-model comparison and bilingual action evaluation remain pending.
3. The compression sanity check is qualitative and must not be presented as a prevalence estimate.
4. Historical verification-prototype figure artifacts are not part of the current paper narrative and must not be cited in the submitted manuscript.
