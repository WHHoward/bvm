# QB-Q2B central-bias bracketing report

## Verdict: `BIAS_BRACKET_NO_BJL1_EVENT`

The selected 30/40 µA bracket did not produce a qualifying read1 BJL1 event while the guards remained bounded.

The 35 µA C/C0 result is the accepted QB-Q2A baseline and was not rerun. All Q2B cases use frozen canonical source-isolated voltage replays; only IBIAS changes.

## Case summary

| bias (µA) | case | BJs units | BJL1 units | BJL2 units | BJL1 largest Δturn | BJL1 area | BJL2 largest Δturn | classification |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 30 | logical1-read0-control | 0 | 0 | 0 | 3.1831e-08 | 1.6758e-08 | 1.59155e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 30 | logical0-read0-control | 0 | 0 | 0 | -2.06901e-07 | -1.99425e-07 | -7.95775e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 30 | logical1-read | 1 | 0 | 0 | 0.320614 | 0.320657 | 0.12624 | `BOUNDED_NO_COMPLETE_EVENT` |
| 30 | logical0-read | 0 | 0 | 0 | -0.0592331 | -0.0592432 | 0.0307294 | `BOUNDED_NO_COMPLETE_EVENT` |
| 40 | logical1-read0-control | 0 | 0 | 0 | 6.3662e-08 | 6.03906e-08 | 3.1831e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 40 | logical0-read0-control | 0 | 0 | 0 | -3.1831e-07 | -3.12216e-07 | -1.27324e-07 | `BOUNDED_NO_COMPLETE_EVENT` |
| 40 | logical1-read | 1 | 0 | 0 | -0.414649 | -0.41471 | -0.175025 | `BOUNDED_NO_COMPLETE_EVENT` |
| 40 | logical0-read | 0 | 0 | 0 | -0.0595289 | -0.0595391 | 0.0315704 | `BOUNDED_NO_COMPLETE_EVENT` |

## Settled operating points

The settled window is `[80,90) ps`; currents are in the declared element directions.

| bias | case | I(RB) µA | I(L1) µA | I(L2) µA | I(BJL1) µA | I(BJL2) µA | I(BJs) µA |
|---:|---|---:|---:|---:|---:|---:|---:|
| 30 | logical1-read0-control | 29.9107 | -14.8083 | 15.1023 | 10.1841 | 15.1238 | -4.69213 |
| 30 | logical0-read0-control | 29.9107 | -18.4241 | 11.4866 | 4.7166 | 11.4989 | -13.7845 |
| 30 | logical1-read | 29.9107 | -4.10655 | 25.8041 | 10.1841 | 15.1238 | -4.69213 |
| 30 | logical0-read | 29.9107 | -17.9485 | 11.9621 | 4.7166 | 11.4989 | -13.7845 |
| 40 | logical1-read0-control | 39.8809 | -20.3902 | 19.4907 | 12.6254 | 19.5171 | -7.85748 |
| 40 | logical0-read0-control | 39.8809 | -23.97 | 15.9108 | 7.24653 | 15.9284 | -16.8251 |
| 40 | logical1-read | 39.8809 | -6.77541 | 33.1055 | 12.6254 | 19.5171 | -7.85748 |
| 40 | logical0-read | 39.8809 | -23.4967 | 16.3842 | 7.24653 | 15.9284 | -16.8251 |

## Event evidence boundary

A complete event requires a same-JJ continuous monotonic phase segment of at least one turn, same-segment direct voltage-area consistency, and bounded post behavior. Current above Ic, voltage peaks and phase activity alone are not event evidence.

## Observed

- Q2B changes only IBIAS at 30 and 40 µA; the source replay and all QB passive/JJ parameters are frozen.
- READ=0 controls were run before READ cases at each point.
- Raw P/V/I for BJs/BJL1/BJL2 and branch currents are retained.

## Derived

- Turns are raw `P()` phase differences divided by `2π`; voltage areas use the actual time column and direct same-JJ voltage.
- The Q2A 35 µA baseline remains the comparison point; Q2B does not claim a continuous bias threshold from two extra points.

## Inference / unknown

- Within this two-point, frozen-source bracket, central bias movement alone did not close the BJL1 dynamic gap.
- No BVM source guard is applicable because this is still standalone source-replay diagnosis; physical BVM reconnection is outside this Exploration.
- No further bias, AREA, L, R or load point is authorized by this run.
