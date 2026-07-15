# Terminology Ledger

| Preferred term | Definition | Avoid |
|---|---|---|
| policy-carriage failure | A failure to preserve the operative meaning and binding of a policy across long-context processing | memory corruption (too broad) |
| policy state | One of preserved, absent, weakened, misbound or over-included | failure type when referring to preserved |
| candidate action | The tool call evaluated immediately before execution | agent output (too broad) |
| action-level safety failure | An unsafe or unnecessarily refused candidate action caused by policy state | hallucination |
| MSR | Minimal Sufficient Policy Retrieval baseline based on applicability-oriented retrieval | oracle retrieval |
| V-MSR | Verification-Guided Minimal Sufficient Policy Retrieval | RAG |
| policy certificate | The selected minimal policies, evidence bindings, decision floor and unresolved/unknown status | chain of thought |
| V-MSR-Struct | V-MSR using structured policy fields | final practical system |
| V-MSR-Text | V-MSR using cached semantics compiled from policy text and trusted provenance | text RAG |
| policy-list diagnostic | Baseline receiving the annotated minimal policy list but no V-MSR certificate | oracle decision |
| clean registry | Canonical policy registry without injected policy corruption | ground truth pool |
| noisy pool | Canonical policies plus conflicting, weakened, misbound or lexically deceptive entries | corrupted answers |

Decision labels are fixed as `allow`, `revise`, `ask_confirmation` and `block`. The conservativeness order is `allow < revise < ask_confirmation < block`, except that an already issued `revise` decision is not overwritten by the execution guard.
