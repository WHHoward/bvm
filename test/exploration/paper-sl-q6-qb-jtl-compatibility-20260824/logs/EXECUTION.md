# PAPER-SL-Q6 execution record

| case | JoSIM exit | stderr bytes | CSV lines including header | result |
|---|---:|---:|---:|---|
| `paper-j1-logical1-read0-control` | 0 | 0 | 13,600 | control passed; no JTL complete event |
| `paper-j1-logical1-read` | 0 | 0 | 13,600 | completed; no JTL complete event |
| `paper-j0-logical0-read` | 0 | 0 | 13,600 | completed; no JTL complete event |
| `paper-j0-logical0-read0-control` | 0 | 0 | 13,600 | control passed; no JTL complete event |

The first control was analyzed before the remaining three cases were launched.
All four CSV time columns are strictly increasing to 169.9875 ps with median
`dt=0.0125 ps`. All solver stderr files are empty. The accepted R11-A standard
JTL positive control was not rerun because Q6 freezes and reuses that validated
fixture provenance.

