# QB-Q2C uniform junction-scale report

## Verdict: `UNIFORM_SCALE_NO_OUTPUT_EVENT`

All newly tested uniform scales remained bounded but produced no complete read1 BJL1/BJL2 event.

s=1 is an accepted Q2A/Q2B reference and was not rerun. It is shown only as a reference row; all new raw data are s=0.85/0.70/0.55.

## Scale → event-unit summary

| scale | source case | N(BJs) | N(BJL1) | N(BJL2) | BJL1 largest Δturn | BJL1 area | classification |
|---:|---|---:|---:|---:|---:|---:|---|
| 1.00 reference | logical1 + READ | 1 | 0 | 0 | +0.3394 activity | not a complete event | accepted Q2A/Q2B reference |
| 1.00 reference | logical0 + READ | 0 | 0 | 0 | ~+0.059 activity | not a complete event | accepted Q2A/Q2B reference |
| 0.85 | logical1-read | 1 | 0 | 0 | 0.326368 | 0.326408 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.85 | logical0-read | 0 | 0 | 0 | -0.0559509 | -0.0559616 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.85 | logical1-read0-control | 0 | 0 | 0 | 4.77465e-08 | 3.31433e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.85 | logical0-read0-control | 0 | 0 | 0 | -2.38732e-07 | -2.23163e-07 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.70 | logical1-read | 1 | 0 | 0 | 0.309636 | 0.30968 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.70 | logical0-read | 0 | 0 | 0 | 0.067753 | 0.0677562 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.70 | logical1-read0-control | 0 | 0 | 0 | 3.1831e-08 | 2.98056e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.70 | logical0-read0-control | 0 | 0 | 0 | -1.90986e-07 | -1.80931e-07 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.55 | logical1-read | 1 | 0 | 0 | 0.285857 | 0.285906 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.55 | logical0-read | 0 | 0 | 0 | 0.0641593 | 0.064162 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.55 | logical1-read0-control | 0 | 0 | 0 | 1.59155e-08 | 1.42386e-08 | `BOUNDED_NO_COMPLETE_EVENT` |
| 0.55 | logical0-read0-control | 0 | 0 | 0 | -1.59155e-07 | -1.54583e-07 | `BOUNDED_NO_COMPLETE_EVENT` |

## Settled operating points

The settled window is `[80,90) ps`; currents use declared element directions.

| scale | case | I(RB) µA | I(L1) µA | I(L2) µA | I(BJL1) µA | I(BJL2) µA | I(BJs) µA |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0.85 | logical1-read0-control | 29.6614 | -14.9819 | 14.6795 | 9.67105 | 14.6939 | -5.38508 |
| 0.85 | logical0-read0-control | 29.6614 | -18.2811 | 11.3803 | 5.11205 | 11.3876 | -13.2504 |
| 0.85 | logical1-read | 29.6614 | -4.57668 | 25.0847 | 9.67105 | 14.6939 | -5.38508 |
| 0.85 | logical0-read | 29.6614 | -17.8464 | 11.815 | 5.11205 | 11.3876 | -13.2504 |
| 0.70 | logical1-read0-control | 24.427 | -12.3606 | 12.0664 | 7.94557 | 12.0709 | -4.48352 |
| 0.70 | logical0-read0-control | 24.427 | -15.3061 | 9.12093 | 4.24686 | 9.12065 | -11.1325 |
| 0.70 | logical1-read | 24.427 | -3.8515 | 20.5755 | 7.94557 | 12.0709 | -4.48352 |
| 0.70 | logical0-read | 24.427 | -14.9185 | 9.50854 | 4.24686 | 9.12065 | -11.1325 |
| 0.55 | logical1-read0-control | 19.1927 | -9.73028 | 9.46239 | 6.22934 | 9.45668 | -3.56398 |
| 0.55 | logical0-read0-control | 19.1927 | -12.255 | 6.93764 | 3.37856 | 6.9301 | -8.94134 |
| 0.55 | logical1-read | 19.1927 | -3.28103 | 15.9116 | 6.22934 | 9.45668 | -3.56398 |
| 0.55 | logical0-read | 19.1927 | -11.9233 | 7.26939 | 3.37856 | 6.9301 | -8.94134 |

## Evidence boundary

Complete event claims require a same-JJ continuous monotonic phase segment of at least one turn, same-segment direct voltage-area consistency and bounded post behavior. `I>Ic`, voltage peaks and sub-turn activity are not event counts.

## Observed

- Only the three declared uniform scales were newly simulated; s=1 was not rerun.
- Each scale was analyzed controls-first; all available controls in this matrix remained bounded.
- The source replay, external load and non-junction inductors/resistors were frozen.

## Derived / inference / unknown

- Within the declared replay, load, timestep and three-point scale bracket, uniform junction/current scaling did not close the BJs→BJL1/BJL2 dynamic gap.
- Uniform scaling changes Ic, C, RN and R0 together; the result cannot be attributed to Ic alone.
- This standalone replay does not establish physical BVM source guards or downstream JTL delivery.
- No further scale point is authorized by this Exploration.
