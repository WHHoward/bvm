# Review record

本文件记录机械/数值审查，不替代 Sol XHigh 或用户的物理审阅。

## Checks

- artifact status: `ANALYSIS_VALID`
- all raw duplicate-column checks: `True`
- receiver/passive exact grid: `True`
- single/array exact overlap: `True`
- all derived integrations use actual stored timestamps and shared `bvmtools` helpers.
- current direction is first netlist node to second; voltage is V(first)-V(second).
- phase remains raw radians until explicit continuous unwrap and `/ (2*pi)` display conversion.

## Adversarial limits

- single-vs-array direct divergence is confounded by sensing boundary and protocol/history; it is not treated as a causal verdict.
- quiet victims are explicitly retained; no inactive branch is silently zeroed.
- active and quiet crosstalk are separated, and passive-vs-QB is reported as a difference of differences.
- bridge comparisons stop at G4; no automatic follow-up was run.
- comparison HTML is required evidence for visual inspection, but plots remain descriptive and do not certify SFQ events.

## Pending review

需要 Sol XHigh/read-only adversarial review重点检查 G0→G4 的因果链、QB-extra 定义、phase-unit 和每个 comparison HTML 的 pair/provenance；最终状态仍由用户审阅决定。

```yaml
state: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
next_action: STOP
```
