# Preserved parse-failure attempt — 001

- Attempt count: 12 registered cases attempted; 0 raw files produced.
- Solver: `build/josim-cli`, exit code `255` for every case.
- Error: `Mismatched parenthesis in expression: )` while parsing the derived BQ
  source line `IB 0 3 pwl(0 0 1p {IB_VALUE})`.
- Classification: tool/netlist parameter syntax failure, not a physical result.
- HEAD: `f61bcc97d5bd82f499f9e957d2850e39889bda12`.
- All original failed `deck.cir`, `run.log` and `metadata.json` files are
  retained under each `runs/<case>/attempts/parse_failure_001/` directory.
- The failed execution summary is retained as `execution_summary.json` in this
  directory.
- Repair: a versioned `BQ_parameterized_v2.cir` uses JoSIM's supported bare
  `IB_VALUE` token in the PWL expression. The registered parameter matrix,
  topology, stimulus, timing, solver and interpretation ceiling are unchanged.
- This failure attempt adds no physical solve and authorizes no extra case.
