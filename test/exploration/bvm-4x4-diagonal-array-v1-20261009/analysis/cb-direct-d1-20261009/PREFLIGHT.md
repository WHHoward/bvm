# CB_DIRECT D1 A023-A024 preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Frozen identity

- Experiment: `bvm-4x4-cb-direct-d1-20261009` (risk `NORMAL`).
- Static preflight source HEAD: `a0b24261645599fb854cbedbd1ddacf056dbccd1`.
- Batch: `BVM4X4_CB_DIRECT_D1_20261009`; exactly two authorized physical solves.
- Static QA: `STATIC_QA.json`, SHA-256 `389992c9e6e53e7bbdc204d6049caa6dda8fc471dedaff6477d2c7e09f2a3be3`; probes registry SHA-256 `159eeb86fe293d1a8752bd7b50637317612b2a8a8c69efb23ecfd6231237821f`.
- A021 raw SHA: `85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e`; A022 raw SHA: `2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb`.
- Canonical CB_0928 SHA: `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`.

## Question and topology

Only the D1 CBU implementation changes. DOUT_D1 and T1_D0.C each pass through their own zero-volt current sensor to the shared `CBU_JOIN_D1` node; canonical `.subckt CB IN OUT` consumes that common input and its OUT feeds T1_D1 through `V_T1_LINK_D1`. No isolator, sJTL, delay element, or ideal current adder is inserted. D2-D6 remain THmitll_MERGE; D0 entrance JTL and all remaining stages are frozen.

## Fixed parameters and stimulus

A021/A022 settings are retained: shared WL/BL 400u, independent SE 100u, array CB/sJTL topology, D0 entry sJTL, seven T1s, DFF, all device parameters, and one-shot global clock at 200 ps (1.2m amplitude, 1/2/1 ps edges/hold, 2 ohm series R). `DT=0.01p`, `STOP=300p`; no extra sJTL.

## Exact run matrix

| Run | Preset | ROW/COL | Deck SHA-256 | Stimulus SHA-256 | Probes | Raw estimate bytes |
|---|---|---|---|---|---:|---:|
| A023_CB_DIRECT_D1_ALL_CLOCK | CB_DIRECT_D1_ALL_CLOCK | 1111/1111 | 46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4 | d149f6f4e83360d8a1b1671e655ed1c9ea241722ebbbc1de48ae4e9fc792f4e2 | 235 | 90770498 |
| A024_CB_DIRECT_D1_PAPER_CLOCK | CB_DIRECT_D1_PAPER_CLOCK | 1101/1101 | 46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4 | d129cc80bceae1382a3d8011c3265dfc451993a2ae7211ed4f1a341ae9ca7926 | 235 | 90770498 |

The paired controls are A021→A023 (`1111/1111`) and A022→A024 (`1101/1101`). Exact PWL/stimulus hashes must match each baseline. Existing A001-A022 evidence remains immutable.

## Registered windows and arithmetic

Use actual stored timestamps only; windows are half-open: ARRAY_FINAL_READ `[110,121) ps`, PRE_CLOCK `[121,200) ps`, CLOCK_EDGE `[200,205) ps`, POST_CLOCK `[205,300) ps`, TOTAL `[0,300) ps`. Report D1 upstream CB BJ1 P/V; branch currents `I(V_CBU_A_D1)` and `I(V_CBU_B_D1)` in the stated source directions; CB BJ1/BJ2 P/V and output-link current; T1_D1 input and B_J1/B_J9/B_J10/B_J11 P/V, S/C; D0 C and carry-JJ P/V. Phase remains radians; `delta/(2*pi)` is navigation only. Same-JJ voltage areas use the same run, JJ, direction, actual rows, and window. No time interpolation.

## QA, plots, and interpretation ceiling

Static checks require one D1 CB_0928, no D1 THmitll_MERGE, no D1 output sJTL, D2-D6 MERGE, unchanged D0/T1/DFF/clock, unique names, resolved probes, exact stimulus, pinned canonical SHA, and JoSIM `-s` syntax checks. Every run gets the existing classic `josim-plot2.py` responsive focus pages; two matched comparison pages use common signals in separate sections and their native grids.
No SFQ/event classifier, physical success threshold, functional verdict, or mechanism explanation is authorized. A waveform peak, lobe candidate, local phase change, or mechanical QA PASS is not an event count or a functional-success decision. Timestep convergence is `UNKNOWN`; no follow-up is authorized.

Scientific interpretation: `NOT PERFORMED`. Automatic follow-up: `NONE`.
