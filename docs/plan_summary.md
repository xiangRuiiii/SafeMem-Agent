# SafeMemBench-Action Plan Summary

SafeMemBench-Action is a benchmark plus empirical study plus lightweight method.
The core research question is whether failures in carrying policies through long
agent contexts lead to unsafe tool actions.

## Main Claim

Policy state failures such as absent, weakened, misbound, and over-included
policies should be measured at the action level, not only at the context state
level.

## MVP Path

1. Build a small set of email, file, and calendar episodes.
2. Check expected decisions by hand.
3. Run no-policy, summary-policy, and all-policy baselines.
4. Confirm that policy carriage failures produce different action safety results.
5. Expand to 90 episodes.
6. Implement and evaluate Minimal Sufficient Policy Retrieval.

## Key Metrics

- Executed violation rate.
- False refusal rate.
- Task success rate.
- Decision accuracy.
- Policy token cost.
- Policy coverage and irrelevant policy rate.
