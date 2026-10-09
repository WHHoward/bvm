# Executor Now

Current routine JoSIM/BVM entry point. Read this short note, then
`memory/BVM_CURRENT_CONTEXT.md` and only the active experiment's README/env.
`memory/LUNA_EXECUTOR_MEMORY.md` is an optional detailed history/submit reference.

- User + ChatGPT own design, scientific interpretation, and next-experiment choices.
  Codex owns only authorized implementation, exact solves, mechanical QA,
  requested classic plots, and bounded evidence packaging; stop when complete.
- Reuse the current platform's `USER_CASE.env`/presets and `try.sh`; do not make a
  worktree or parallel platform unless explicitly requested.
- Current 4×4 platform:
  `test/exploration/bvm-4x4-diagonal-array-v1-20261009/`. It uses 16 BVMs,
  independent QB, shared row WL/column BL, cell-local SE, seven serial diagonal
  outputs, and configurable per-level sJTL count. Canonical includes are
  `bvm_cell_0923.cir`, `BQ_0928.cir`, `sJTL_0923.cir`, `CB_0928.cir`, and
  `jjmit.cir`; verify their manifest hashes before use.
- A001–A006 are the 200u shared-bus low-drive baseline: artifact/mechanical QA
  remains valid, but normal 4×4 function was not established. Their raw and ZIPs
-  are immutable. The 400u BUS400 batch A007/A008 is complete with artifact and
  mechanical/plot QA PASS; interpretation is pending user review. The 400u is a
  tested bus-source total, not an optimal setting or per-cell current claim;
  measured per-cell branch arithmetic lives in the run metrics.
- In 4×4, T1/CBU/DFF are not connected; `T1_PARAMS.env` is reference-only.
- Never overwrite raw, add an unrequested run/sweep, infer physical function from
  arithmetic/plots, or continue past the authorized batch. Record provenance and
  keep artifact validity separate from scientific verdict.
- Active standards: `docs/EXPERIMENT_CONTRACT.md` and
  `docs/research/EXPERIMENT_WORKFLOW_V1.md`; risk levels are QUICK/NORMAL/FORMAL
  and distinct from research tiers.
