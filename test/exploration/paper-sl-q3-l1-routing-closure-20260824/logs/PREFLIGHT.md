# PAPER-SL-Q3 preflight

- wall-clock record: `2026-08-24T04:49:13+08:00`
- repository HEAD before execution: `0cdb92e53aa1444d1bba1337567b781886c9149f`
- worktree before execution: clean apart from the new Q3 directory
- JoSIM binary: `build/josim-cli`
- JoSIM version: `v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- metric specification: `docs/research/METRIC_SPEC_V2.md`, SHA-256 recorded in `reference/source-provenance.yaml`
- timestep: `0.0125 ps`
- stop time: `170 ps` (`13,599` data rows plus header; final printed time `169.9875 ps`)
- source replay: byte-identical copies of accepted PAPER-SL-Q2 `inputs/40u` decks
- physical change: local QB snapshot only, `L1 3.91p -> 4.50p`
- no canonical BVM, physical JSL load, JTL, T1, parameter sweep, or waveform reshape was used

The first `logical1 + READ=0` control exited successfully with no complete
phase/area-consistent transition or startup/free-running signature in the
registered windows. The remaining three matched runs were therefore executed.
