# PREFLIGHT — V0_15x15_T70

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Risk level: `NORMAL` (bounded 4×4 array/link validation; not a FORMAL system
  Gate or paper-level claim).
- Baseline HEAD and fetched `bvm/master`: `22d1157eb4a3811c0e6dd7f677321d19ca9cd36b`
  (`usercomitt:11111`, 2026-10-13). The actual pre-run HEAD is recorded in
  `RUN_MANIFEST.json` after the scoped pre-registration commit.
- Generated `deck.cir` SHA-256:
  `71becb54893d02068a1c6068e078a259040d604ae22ce6bb7957ecc603d0b17a`;
  `stimulus.inc` SHA-256:
  `b1337be290d66f812700403611bb8f242dbc66101dded662eea23acb2eb5f6db`;
  deck-template SHA-256:
  `74f7ee648b1be165a531bb808e8854c2c6a76bb472d732ae701598f89a85a7ea`.
- Exactly one authorized JoSIM solve: `V0_15x15_T70`; A=15, B=15; expected
  product 225 (`11100001`, bit order D0=LSB through D7=DFF_O).
- No prior raw or output existed at this run path. Existing sibling data is not
  used as this run's evidence.
- A pre-existing unrelated untracked sibling path was present at task start:
  `test/exploration/sfq_clock_two_read_v1/sfq_clock_timesteptest_11X13/`. It is
  outside this run scope and will not be staged or changed. The run gate checks
  this experiment directory for cleanliness.

## Frozen source closure

The source and snapshot hashes below are checked again by `run.sh` before use.
`SOURCE_MANIFEST.json` contains the full paths and exact per-file hashes.

| Frozen include | SHA-256 |
|---|---|
| `00_jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `01_bvm_cell_0923.cir` | `bbb741ba572924f018749d1fa0cf888876e4e0e352635614b9aeec14fb8cdb16` |
| `02_BQ_0928.cir` | `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a` |
| `03_sJTL_0923.cir` | `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688` |
| `04_CB_0928.cir` | `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370` |
| `05_MERGE.cir` (included library; D6 MERGE instance inactive) | `79b0d219db60ca41a03d732eaac82b436114b02436cf4dc8719e9b25d58940e0` |
| `06_dcsfq2.cir` | `76e9866ef32a73ac8bda2a4698ba1d39dc8e1c83312da168ba0aab8eee5fc280` |
| `07_jtl2.cir` | `9ec481453c5aa519dec18c07efc2c377b11f3ca0345c6e7971bd6806036455aa` |
| `08_t1_cell_tunable.cir` | `da7f1c5065081caccbd6cbd698630a9cf94019840e39e3beb0839b99e5e7bcdb` |
| `09_DFF.cir` | `e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0` |
| `10_d0_jtl_tunable.cir` | `b242741e4630a54411db48de649361e8daedfd6a083358d675d2fdf657314039` |

Generation tool identity:

- `scripts/bvm_stimulus.py`: SHA-256
  `be0486ac5d648e498cb0d331355b40915b9b6ebcdd274a8b4c86887b24f3d666`.
- Source fixture: `sfq_clock_timesteptest/deck.cir`, SHA-256
  `b7982fc348001a78144a1a0ca389b610411a15237b214e01d0abd3e16aad57d1`.
- `/usr/local/bin/josim-cli` is discoverable but is v2.7.02a34ee (SHA-256
  `d6913de92f71ee57bcb519f40c9fb60f3b51f404ec46ef8b00d3a7f3dfdf4b9c`). The
  runner prefers the repository-recorded `build/josim-cli`, v2.7.2837d13
  (SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`);
  any explicit `JOSIM_CLI` override is recorded in `RUN_MANIFEST.json`.

## Static QA — PASS before solve

- 16 BVM instances; 16 independent BQ instances; seven T1 instances; one DFF.
- `XCB_D6_L1` and `XCB_CARRY_D6` both terminate at `T1_I_D6`.
- No active `XMERGE_D6`; no inline top-level `V_TRIG_CLK_*` remains in
  `deck.cir`; `stimulus.inc` is included exactly once.
- `stimulus.inc`: exactly 4 WL + 4 BL + 16 SE + 8 clock sources (32 total).
- All four WLs have one WRITE1 pulse at 50 ps and read pulses at 110/180/250 ps;
  all four BLs have one WRITE1 pulse only; all 16 SE sources pulse only at the
  three read starts; all eight clock PWLs start at 180/250/320 ps.
- `.tran 0.01p 400p`; no existing raw/log/output at this new path.
- Probe profile `outputs-clocks`: only eight final outputs and eight actual CLK
  outputs.
- Frozen include snapshots and SHA-256 match `SOURCE_MANIFEST.json`.

The remaining static artifact checks are run by `run.sh` before the solver
launch. No JoSIM parser/sanity mode is invoked as a substitute because this
JoSIM build constructs a simulation object after its sanity-check option.

## Registered output arithmetic and limits

- Output windows use actual stored samples; each adjacent-sample trapezoid is
  assigned by its midpoint to `[180,250)`, `[250,320)`, or `[320,400)` ps.
- The existing `scripts/final_mul_case.py` task-local area screen is recorded:
  net area within ±0.30 Φ0 of the expected bit, plus absolute-area ceilings of
  0.5 Φ0 for expected zero and 1.6 Φ0 for expected one. This is only a derived
  output-area screen, not an SFQ event classifier.
- Terminal `V(S_D*_OUT)` / `V(DFF_O)` plus CLK probes do not provide an
  independent event-identity/count method. Per-bit SFQ event count and the
  claim “exactly one SFQ per expected one” remain `INCONCLUSIVE` unless the
  raw supports reliable attribution; no post-hoc event threshold will be added.
- Third-round area covers `[320,400)`; any unresolved late activity is reported
  as output-area evidence, not automatically assigned as an extra SFQ event.
- No convergence/sensitivity test is included. No 11×13/15×7/other-period run,
  optimization, topology change, or follow-up is authorized.
