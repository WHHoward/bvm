# R12-A：historical DCSFQ_BVM re-audit + canonical BVM compatibility

日期：2026-08-23
模式：`EXPLORATORY` / gated historical re-audit
基线 HEAD：`ca610ce73bf78ddc99edf3f03197be1968bfe8b2`

## Scientific question

仓库现有 `circuits/interface/DCSFQ_BVM.cir` 是否能把 canonical BVM 的 read1 transient 转为可解释的 regenerative local event，并最终驱动 standard JTL；或者它只产生 bounded sub-turn activity？

本轮先做 Phase A。只有 Phase A 建立 converter 自身的有效 regenerative local behavior，才允许执行 conditional Phase B cascade。Phase A 失败时不创建/运行 Phase B，不调参、不恢复旧 Phase-1 扫描。

## Phase A frozen fixture

原始 `THmitll_DCSFQ_BVM` topology、AREA、bias、L/R、jjmit model 全部原样使用。三个 case 只改变 `IIN`：

| case | `IIN` | role |
|---|---:|---|
| `zero` | `0 µA` | identical bias-startup control |
| `bump-68u4` | `68.4 µA` | historical BVM read1 level |
| `bump-300u` | `300 µA` | historical strong-bump control |

PWL timing exactly follows historical P0 fixture: zero until `10 ps`, rise to IIN at `12 ps`, hold through `40 ps`, fall to zero at `45 ps`; `.tran 0.1p 200p`。没有 sweep、周期源或第二个 amplitude point。

## Registered windows and background separation

- `startup_window = [0,7) ps`：包含 bias ramp (`0→100/175 µA` at 5 ps)，只用于识别 startup trajectory；不作为 input event。
- `pre_input_window = [7,10) ps`：输入尚未开始的 bias-settled reference。
- `input_activity_window = [10,45) ps`：PWL input active window。
- `post_window = [60,180) ps`：输入消失后的 bounded/retrap check。

对每个 B1/B2/B3 同时报告：

1. absolute case phase trajectory / direct same-JJ voltage；
2. `case − zero` unwrapped phase differential trajectory；
3. same-JJ direct voltage-area and differential voltage-area；
4. largest monotonic segment、onset/end、post p2p 和 retrap evidence。

zero case 的 startup phase 不能被称为 input event；68.4/300 的 differential response 也不能只用 endpoint net 或旧 JSON 解释。

## Required probes

每个 case 直接记录：

- `P/V/I(B1|XDCSFQ)`、`P/V/I(B2|XDCSFQ)`、`P/V/I(B3|XDCSFQ)`；
- `I(L1|XDCSFQ)` … `I(L6|XDCSFQ)`、`I(LB1|XDCSFQ)`、`I(LB2|XDCSFQ)`；
- `I(IB1|XDCSFQ)`、`I(IB2|XDCSFQ)`、`I(RB1|XDCSFQ)`、`I(RB2|XDCSFQ)`、`I(RB3|XDCSFQ)`；
- `V(IN1)`、`V(OUT1)`、`I(I_IN)`、`I(R_LOAD)`。

Event evidence requires continuous/unwrapped phase, a complete same-JJ monotonic phase transition, same-segment `∫Vdt/Φ0` consistency, and post-event retrap/bounded behavior. `I>Ic`、voltage peak、phase range、derivative samples和 `sfq_metrics.py fast_events` 均不能单独定义 event。

## Phase-A gate

Phase A is positive only if the controlled raw trajectories establish an interpretable converter behavior, including:

- 68.4 µA classification based on differential same-JJ evidence；
- 300 µA differential response classified as zero/one/multiple complete local transitions, not old fast-sample counts；
- B3 output phase/area and post-state show whether a bounded one-shot is present or absent。

If all three cases remain bounded/sub-turn or the response is not causally separable from bias startup, verdict is `DCSFQ_BVM_NO_TRIGGER` or `INCONCLUSIVE`, and Phase B stops by gate.

## Conditional Phase B (not yet authorized to run)

Only after Phase A positive evidence, use unchanged `DCSFQ_BVM.cir` in:

```text
canonical BVM SL → THmitll_DCSFQ_BVM.a → THmitll_DCSFQ_BVM.q
                 → two unchanged THmitll_JTL cells → R_TERM
```

The Phase-B input would preserve BVM internal `R_SL/L_SL`, use direct galvanic `SL→a` and `q→JTL1.a`, and run the four canonical BVM matched cases. No transformer, amplifier, matching network, B1/B2/IB/L sweep or T1 is permitted. This section is a conditional plan only; no Phase-B netlist is run before the Phase-A gate is evaluated.

## Stop rules

Stop after Phase A if converter regenerative behavior is not established. Do not infer a universal impossibility from this fixed model, fixture, load, timing and timestep; report bounded evidence and return the route decision to BVM-specific temporal rectification/hold review.
