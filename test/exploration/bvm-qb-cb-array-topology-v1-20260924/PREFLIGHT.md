# Platform implementation preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Scope

- Startup HEAD: `3874aca666361696b319f682ed09ed195d9d9f30`.
- Startup worktree: clean.
- Change scope: new BVM-array → QB/CB/sJTL platform, its static render fixtures,
  and platform-local tests.
- Authoritative component sources are the four `0923` circuits listed in
  `README.md`; this task does not edit those source files.
- Output mode is terminal-only; no T1 is connected.
- The source files contain their own `.model jjmit` definitions; the solver's
  acceptance of repeated definitions across included subcircuits remains
  UNKNOWN until a separately authorized real run. No source edits or workaround
  are made here.

## Authorized this turn

- Read source circuits and repository helpers.
- Implement config validation, topology/stimulus/probe rendering, static plot
  plans, immutable-run code paths, and local submit/package code paths.
- Generate only the three `RENDER_FIXTURE_ONLY` examples under `tests/fixtures`.
- Run Python unit/static tests and dry-run logic only.
- Make one ordinary source commit after static validation.

## Explicitly not authorized

- JoSIM execution, raw.csv generation, physical interpretation, topology
  ranking/optimization, parameter sweep, T1, repeated-read/rewrite-read,
  timestep sweep, real evidence ZIP, Drive mirror, or push.
- Modification of canonical circuit sources or any existing experiment/raw.

## Interpretation ceiling

This platform implementation and its render fixtures are not physical evidence.
All result/manifest defaults must set `scientific_interpretation_performed` and
`automatic_follow_up` to `false`. Stop after tests and source commit for user
review of generated CIR.
