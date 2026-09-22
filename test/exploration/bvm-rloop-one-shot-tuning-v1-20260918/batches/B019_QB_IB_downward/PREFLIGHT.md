# B019 QB_IB downward sweep preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment: `B019_QB_IB_downward`
- Study phase: `EXPLORATORY`
- Parent HEAD: `8fcd69f1ead0861dc5c1e7c32659a21cc3a369df`
- Repository: `/home/howard/JoSIM`
- Existing raw: immutable; no existing case is overwritten.
- Scientific review token: absent. The executor will stop at mechanical/raw evidence and will not assign a scientific Gate or mechanism verdict.

## Source closure

- BVM authority source: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir`, SHA-256 `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54`.
- Experiment-local BVM template: `circuits/bvm_tunable.cir`, SHA-256 `1b0431c5c06616bc04e3c1c21187a74e7e1dd0805552905e0c4e609849c95c66`.
- Experiment-local QB template: `circuits/bq_tunable.cir`, SHA-256 `140154e3375a76de07b55c218f5069b27fdbacea23308485124422ece5163eda`.
- JJ model: `circuits/models/jjmit.cir`, SHA-256 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.
- JTL source: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir`, SHA-256 `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`.
- Solver: `build/josim-cli`, version `v2.7.2837d13`, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

## Authorized physical solves

1. `CONTROL_ONLY` C0: one `0000` run, `QB_BJ1_AREA=0.90`, `QB_RJ1=32`, `QB_IB=260u`, STOP `120p`.
2. `CONTROL_ONLY` C1: one `0000` run, `QB_BJ1_AREA=0.75`, `QB_RJ1=32`, `QB_IB=260u`, STOP `120p`.
3. Only after the C0/C1 registered pattern gate is satisfied: normal CLOSED B019, masks `0000,0001,0011`, and only `QB_IB=220u,230u,240u,250u,260u`.

The normal B019 matrix is exactly 5 parameter points × 3 masks = 15 logical runs. `260u` may strict-reuse an existing complete point. No control-only sweep over the five IB values is authorized.

## Control-only stimulus and windows

- `DT=0.1p`, stop `120p`.
- `0–50 ps` idle.
- `50–61 ps` canonical WRITE0: WL/BL `-100u`, SE `0u`, 1 ps rise/fall.
- `61–70 ps` settle.
- `70–81 ps` canonical CONTROL: WL/SE `100u`, BL `0u`, 1 ps rise/fall.
- `81–120 ps` all external sources zero.
- No WRITE1 and no FINAL READ.
- Control terminal locator: `I(R_TERM)`, positive local maxima above `50uA`, minimum separation `2.5 ps`, window `[70,120) ps`, label `terminal_candidate`.
- All integration and selection use actual stored samples; no interpolation, smoothing, resampling, time shift, amplitude scaling, or sign correction.

## Mechanical/raw QA

- Preserve raw SHA-256 before and after analysis.
- Check finite values, monotonic stored time, actual time range, sample count, stored-grid irregularity, required QB/JTL/terminal probes, deck/stimulus hashes, and visualization source hashes.
- C0/C1 validation uses only the registered `+0.5` navigation crossings and terminal-candidate count pattern; the approximate C1 timing/peak is reported, not used as an invented numeric PASS threshold.
- A raw/analysis artifact failure is `ARTIFACT_INVALID`, not a physical failure.

## Prohibited actions

- Do not modify BVM topology, JTL, LS3/RS, or any second sweep variable.
- Do not add IB points, run a two-dimensional sweep, run sentinel follow-up, extend the normal READ, or change the normal B019 protocol.
- Do not overwrite B017/B018 or any historical raw.
- Restore `USER_CASE.env` to `SWEEP_ENABLED=no`, `SWEEP_KEY=NONE`, and empty `SWEEP_VALUES` after execution.
