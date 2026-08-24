# v2 execution record

Execution batch completed at `2026-08-24T08:49:12+08:00` (Asia/Shanghai
recording time). All 11 v2 jobs returned exit code 0 and all v2 stderr files
are empty.

| fixture | raw cases | timestep | stop | artifact status |
|---|---:|---:|---:|---|
| A Q0 OPEN | 1 six-pulse deck | 0.1 ps | 300 ps | valid |
| B Q0 JTL-only | 1 six-pulse deck | 0.1 ps | 300 ps | valid |
| C Q0 10Ω || JTL | 1 six-pulse deck | 0.1 ps | 300 ps | valid |
| D Q5 OPEN | 4 replay decks | 0.0125 ps | 170 ps | valid |
| E Q5 JTL-only | 4 replay decks | 0.0125 ps | 170 ps | valid |

Expected numeric rows were observed: 2,999 for each Q0 trace and 13,599 for
each Q5 trace. The JoSIM progress text precedes the fixed-width data header in
the raw files; the analysis parser locates that header explicitly.

No parameter or topology follow-up was run after the five fixtures. The only
post-run action was raw phase/voltage-area analysis.
