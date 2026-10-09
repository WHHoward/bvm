# A025/A026 D1 carry-side CB_0928 preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Batch: `BVM4X4_CB_CARRY_BUFFER_D1_20261009`; risk: `NORMAL`; physical solves authorized: `2`.
- Preflight HEAD: `e0155de0c19e95d8c909550c67097db65695c842`; solver: `/home/howard/JoSIM/build/josim-cli`; SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Source closure is pinned in `STATIC_QA.json`; canonical CB_0928 ports are `IN OUT` and its SHA is verified.
- Topology change is only the D1 carry branch: `C_D0 -> V_CARRY_IN_D1 -> XCB_CARRY_D1 (CB_0928) -> V_CBU_B_D1 -> CBU_JOIN_D1`; `DOUT_D1 -> V_CBU_A_D1 -> CBU_JOIN_D1`; `V_T1_LINK_D1 -> T1_D1.I`.
- No CB/JTL/sJTL/other component is added after JOIN. D1 has no `THmitll_MERGE`; D2-D6 remain `THmitll_MERGE`.
- All array BVM/QB/CB/sJTL, T1/DFF, biases, loads, clock, and stimulus otherwise match A021/A022; D0 uses the original single entrance sJTL.
- Frozen timing: DT=0.01 ps; STOP=300 ps; global single clock at 200 ps, 1.2 mV, 1/2/1 ps, series R=2 ohm.
- Windows are half-open and use actual stored timestamps: ARRAY_FINAL_READ [110,121), PRE_CLOCK [121,200), CLOCK_EDGE [200,205), POST_CLOCK [205,300), TOTAL [0,300) ps.
- P is raw radians. Per-JJ phase is independently unwrapped; phase delta/(2π) is navigation arithmetic only. V area is same-JJ, same direction, same raw rows; no event classifier is defined.
- Interpretation ceiling: artifact validity and registered arithmetic only. SFQ event classification, mechanism, isolation, and full multiplier function are not determined.
- If static/solver/raw/mechanical artifact QA hard-fails, stop and preserve the attempt. Do not retry physics, tune parameters, add sJTL, or expand beyond A025/A026.

## Locked run matrix

| Run | ROW/COL | Override | Clock | DT / STOP | Probes / estimate | Baseline |
|---|---|---|---|---|---|---|
| A025_CARRY_CB_D1_ALL_CLOCK | 1111/1111 | CB_CARRY_BUFFER | GLOBAL_ONESHOT@200 ps | 0.01 / 300 ps | 189 / 73002656 B | A021_CHAIN_ALL_GLOBAL_CLOCK |
| A026_CARRY_CB_D1_PAPER_CLOCK | 1101/1101 | CB_CARRY_BUFFER | GLOBAL_ONESHOT@200 ps | 0.01 / 300 ps | 189 / 73002656 B | A022_CHAIN_PAPER_GLOBAL_CLOCK |

## Frozen checks

- All three modes (`NONE`, `CB_DIRECT`, `CB_CARRY_BUFFER`) render; historical A021/A022 and A023/A024 decks remain byte-identical to their stored render.
- Candidate deck differs from its A021/A022 base only in the D1 carry topology and `.print` probe directives; `stimulus.inc` is byte-identical.
- JoSIM `-s` syntax/model check PASS; this is static validation and `physical_solve_count=0`.
- Static QA and per-run probe manifest are hash-bound in `WORK_UNIT.json`.
