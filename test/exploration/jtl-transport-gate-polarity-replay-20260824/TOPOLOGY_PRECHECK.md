# Topology / provenance precheck

The tested chain is exactly:

```text
V_REPLAY(JTL_IN, 0) -> THmitll_JTL(JTL_IN, JTL_MID)
                         -> THmitll_JTL(JTL_MID, JTL_OUT) -> R_TERM(1 Ω) -> GND
```

Each `THmitll_JTL` is the repository `circuits/standard/JTL.cir` subcircuit;
its two internal junctions are `B1`, `B2`, so the four monitored branches are
`B1|XJTL1`, `B2|XJTL1`, `B1|XJTL2`, and `B2|XJTL2`.

The only new source is the ideal diagnostic voltage replay at `JTL_IN`. It has
no DC path into BVM because BVM/QB is not present in either new fixture. The
source is zero during startup, reproduces accepted Q0 pulse 5 at absolute
times `200..259.9 ps`, and is held at zero through `300 ps`.

The positive and reverse fixtures are built independently from the same source
CSV and frozen JTL/model copies. The reverse fixture changes only the sign of
`V_REPLAY`; all time points, load, JTL cells, model and bias are identical.

Provenance hashes are recorded in `analysis/manifest.json` and
`analysis/SHA256SUMS.txt` after generation and execution.
