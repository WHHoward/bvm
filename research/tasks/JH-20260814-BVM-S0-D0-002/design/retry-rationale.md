# D0-002 retry rationale

`JH-20260814-BVM-S0-D0-001` A01 is preserved as `INVALID` solely because it
ran with `/usr/local/bin/josim-cli` (v2.7.02a34ee), not the repository-recorded
binary.  Its task request, raw outputs, receipt, and C01 verdict are immutable
inputs to this retry and are not scientific baseline evidence.

D0-002 repeats the same three predeclared no-read initialization cases, one
12-ohm load, copied BVM/model closure, direct JM1/JM2 P/V probes, windows, and
D0-only guards from `initial-state-discriminator.md`.  The only intended
experimental change is executable provenance:

```text
/home/howard/JoSIM/build/josim-cli
v2.7.2837d13 compiled on May 30 2026 at 20:37:57
sha256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
```

No result may be compared to A01 as a numerical regression or used to infer a
version effect.  The sole purpose is to create a correctly provenance-bound D0
artifact.  A later S0 remains separately gated on D0 audit acceptance.

