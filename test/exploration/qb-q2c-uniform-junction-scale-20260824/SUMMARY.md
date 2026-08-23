# QB-Q2C uniform junction-scale bracketing — summary

## Verdict

`UNIFORM_SCALE_NO_OUTPUT_EVENT`

在冻结的 canonical source-isolated replay 下，新增的 `s=0.85/0.70/0.55` 三个 uniform junction/current scale 均保持 bounded，但没有产生完整的 read1 BJL1 或 BJL2 transition。read0 和两个 READ=0 controls 均为零 complete event。

该结论限定于本次三点 scale bracket、冻结的 replay、load、模型、`dt=0.0125 ps` 和 170 ps stop time；不升级为 uniform scaling family 的普遍不可能性。

## Tested points

| scale | BJs AREA | BJL1 AREA | BJL2 AREA | IBIAS |
|---:|---:|---:|---:|---:|
| 0.85 | 0.425 | 0.306 | 0.459 | 29.75 µA |
| 0.70 | 0.350 | 0.252 | 0.378 | 24.50 µA |
| 0.55 | 0.275 | 0.198 | 0.297 | 19.25 µA |

The accepted `s=1` Q2A/Q2B reference was not rerun.

## Output evidence

| scale | read1 BJL1 largest segment / area | read1 BJL2 largest segment / area | read0 BJL1 largest segment / area | read0 BJL2 largest segment / area |
|---:|---:|---:|---:|---:|
| 0.85 | `0.326368 / 0.326408 turn` | `0.136322 / 0.136333 Φ0` | `−0.055951 / −0.055962` | `0.032824 / 0.032825` |
| 0.70 | `0.309636 / 0.309680 turn` | `0.126460 / 0.126474 Φ0` | `0.067753 / 0.067756` | `0.034248 / 0.034248` |
| 0.55 | `0.285857 / 0.285906 turn` | `0.113025 / 0.113041 Φ0` | `0.064159 / 0.064162` | `0.035102 / 0.035103` |

Every value is a same-JJ, same monotonic-segment phase/voltage-area pair. All are below one turn for BJL1/BJL2. Read1 BJs retained one bounded local complete phase/area response at all three scales (`N(BJs)=1`); this is upstream local activity, not downstream SFQ delivery.

## Settled operating-point observation

Measured settled `I(RB)` was approximately `29.66/24.43/19.19 µA` for `s=0.85/0.70/0.55`. Read1 settled BJL1 current decreased approximately `9.67 → 7.95 → 6.23 µA`; logical0 was `5.11 → 4.25 → 3.38 µA`. The scale change therefore reduced the absolute current class without producing threshold-like BJL1/BJL2 amplification.

## Observed / Derived / Inference / Unknown

**Observed**

- All 12 final runs exited successfully; controls were run before READ cases at each scale.
- BJs read1 remained state-selective and locally active; BJL1/BJL2 remained sub-turn.
- No control or logical0 complete event, post free-running or multifire was observed.
- The largest read1 post-window phase p2p across the three JJ stages was below `4.2e-4 turn`, consistent with bounded settling at this diagnostic scale.

**Derived**

- Phase turns are raw `P()` differences divided by `2π`.
- Voltage areas use the actual CSV time column and the direct same-JJ voltage.
- `jjmit` area scaling changes `Ic`, `C`, `RN` and `R0` together; this is not an Ic-only test.

**Inference**

Within this finite bracket, uniform scaling did not close the BJs→BJL1/BJL2 dynamic gap. The output activity decreased with scale for read1 rather than showing a nonlinear threshold jump.

**Unknown**

- No physical BVM was connected, so canonical SL/N6/JM/JS source guards are not part of this result.
- No timestep refinement or further scale point was run.
- The result does not distinguish BJL1/BJs ratio changes, bias-routing changes or temporal conditioning.

## Stop

Do not append smaller scales, reconnect physical BVM, change the BJL1/BJs ratio, or connect JTL based only on this run. The next branch, if authorized, should address the junction ratio or topology rather than continue uniform scale reduction.

See [full report](analysis/QB_Q2C_REPORT.md), [analytic precheck](QB_Q2C_ANALYTIC_PRECHECK.md), [raw QA](logs/QA.md), and [hashes](analysis/SHA256SUMS.txt).
