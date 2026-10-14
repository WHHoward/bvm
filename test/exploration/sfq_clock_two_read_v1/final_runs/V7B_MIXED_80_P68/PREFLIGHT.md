# PREFLIGHT — V7B_MIXED_80_P68

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Frozen registration

- Risk level: `NORMAL`; bounded waveform/round-attribution observation only.
- Task-start local and fetched `bvm/master` HEAD: `5742d11585f8a58403271a6193f62252d2186e69`.
- No circuit, model, device parameter, topology, or solver setting is changed.
- Authorized solve count: exactly one for this condition; paired only with the separately registered V7A run.
- Frozen source fixture: `sfq_clock_timesteptest/deck.cir`, SHA-256
  `b7982fc348001a78144a1a0ca389b610411a15237b214e01d0abd3e16aad57d1`.
- `deck.template.cir` SHA-256: `74f7ee648b1be165a531bb808e8854c2c6a76bb472d732ae701598f89a85a7ea`.
- `deck.cir` SHA-256: `e93b7b26859d9acab68b5e0f98620789aaf7451de3a16314a1437df483e9336a`.
- `stimulus.inc` SHA-256: `f3ef4e729a875eabea66a9bc18402587abad9ac586d38b4983c18567ce8a29d6`.
- `USER_CASE.env` SHA-256: `b01e1c0a7b723af31c12eb33b8baad3c30162ae7c964f2d9334c5e3763160fdf`.
- Generator SHA-256: `4c1a14f05c889df75d576c9d9e99cd58d23ae5459c4016b3128513ef005754b2`.
- Configure entry SHA-256: `55151938426e5d23389e1e735cd6fe56910e4bb896f9fac8b8d29ed181b56274`.
- `SOURCE_MANIFEST.json` snapshots all 11 include files. Their hashes are byte-identical to the frozen V0 source closure; see that manifest for paths and per-file SHA-256 values.
- Solver is explicitly `/usr/local/bin/josim-cli`, version `v2.7.02a34ee` (Apr 23 2026), SHA-256 `d6913de92f71ee57bcb519f40c9fb60f3b51f404ec46ef8b00d3a7f3dfdf4b9c`.

## Exact case and stimulus

- `ROUND_CASES=15:7,15:15,0:0`; expected products by round: `105, 225, 0`.
- `A=15`, `B=7` identify the first round and preserve the legacy fallback fields.
- One WRITE1 initializes all 16 BVMs: WL/BL source pulses start at 50 ps. No WRITE0, READ0, or inter-round write occurs. BL sources have no later pulses.
- Per-round read starts: `110, 190, 270 ps`; interval 80 ps.
- Corresponding clock PWL starts: `178, 258, 338 ps`; period 80 ps; SE-to-clock start offset 68 ps. All eight clock sources receive all three pulses.
- `DT=0.01 ps`; automatic `STOP=420 ps`; `PROBES=outputs-clocks`.
- Output integration windows are fixed before solve and are not shifted to fit expected output: pre-clock `[0,178)`, rounds `[178,258)`, `[258,338)`, `[338,420) ps`. Adjacent-sample trapezoids use actual stored timestamps and are assigned by interval midpoint; no raw interpolation or resampling.
- Per output/window, report stored-grid positive maximum and negative minimum times plus separate positive and negative sample-clipped voltage-time integrals divided by `Phi0`. These are waveform landmarks and derived integrals, not event counts.
- Per actual CLK/window, report the stored-grid maximum absolute voltage and its timestamp. PWL source start is not treated as actual CLK arrival.

## Probes, QA, limits

- Final outputs to ground: `V(S_D0_OUT)` … `V(S_D6_OUT)`, `V(DFF_O)` (V).
- Actual clock output nodes to ground: `V(CLK_D0)` … `V(CLK_D6)`, `V(CLK_DFF)` (V).
- Static checks: 16 BVM, 16 BQ, seven T1, one DFF; D6 two-CB path; exact 4 WL + 4 BL + 16 SE + 8 clock signal sources; 16 registered `.print` probes; single WRITE1 on every WL/BL source; per-round WL/SE gating; unchanged source closure.
- Post-run checks: solver exit status, immutable nonempty raw, all 16 probes present, monotonic stored time, actual time range/grid, raw SHA before/after plotting, standalone classic HTML generated from this run's raw.
- Expected output words are references only: round 1 `105` (`01101001` MSB-first; D0-to-DFF `10010110`), round 2 `225` (`11100001` MSB-first; D0-to-DFF `10000111`), round 3 zero.
- Extra/missing SFQ event classification is `INCONCLUSIVE` with this output/clock-only probe set; no post-hoc event threshold or expected-answer-tuned window is authorized.
- No mechanism/physics conclusion, parameter change, extra period, sweep, or follow-up solve is authorized.

The unrelated pre-existing V8 worktree changes are outside this run and are not part of the input, evidence, or submission scope.

## Execution HEAD reconciliation

During preparation, a concurrent user commit advanced HEAD from the task-start
`5742d11585f8a58403271a6193f62252d2186e69` to
`e3b97c112b3c78729803ba1b0e633365d11a2db0` at 15:57:56 +0800, before this
run's raw/log creation at 16:10:13 +0800. The intervening commit added only
the V8 experiment artifacts; it did not change the shared stimulus generator,
configure entry, frozen deck fixture, or canonical circuit/model sources. The
execution HEAD is therefore `e3b97c112b3c78729803ba1b0e633365d11a2db0`;
`RUN_MANIFEST.json` records both task-start and execution HEADs. This is a
metadata reconciliation only; raw, deck, stimulus, and measured values are
unchanged.

## Static gate result

`PASS` before solver invocation. `deck.cir` contains the frozen two-CB D6 route,
16 BVMs, 16 BQs, seven T1s and one DFF; all 16 registered output/CLK probes
are present. `stimulus.inc` contains exactly 32 signal sources (4 WL, 4 BL, 16
SE, 8 CLK). Parsed PWL active intervals match the registered row/column masks
for every round; each BL has only its initialization pulse, and every clock
source has all three registered pulses. Both frozen template and 11-source
hash closure match V0. No raw, log or HTML existed at this run path before the
authorized solve.
