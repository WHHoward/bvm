# Luna executor routing smoke checks

Static expected-routing checks only; no JoSIM run or scientific analysis was
performed.

| User request | Expected skill route | Required boundary |
|---|---|---|
| Existing platform; change one stimulus config value and run one case | `josim-experiment` | Reuse the platform/config interface; execute only that requested case. |
| Existing valid raw; repair its plot | `josim-viz` | Reuse the same raw; do not invoke JoSIM. |
| Experiment complete; submit and package it | `josim-submit` | Dry-run, then the established series-local submit path; no interpretation or follow-up solve. |

## Adversarial consistency checks

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| A stale repo instruction still makes `HANDOVER` or all specialist skills mandatory for ordinary runs | Cross-checked `AGENTS.md`, skill index, and `josim-experiment` | PASS; bootstrap is explicit and specialist skills are conditional. |
| A post-solve plot/parser repair still routes through a new solve | Inspected `try_candidate.py` and the standalone case-root analyzer/plotter CLI | PASS; instructions direct repair to the same raw; rerunning `try.sh` is explicitly prohibited as a repair. |
| Submit falls back to the generic root workflow despite a series-local script | Cross-checked `josim-submit` route against golden `submit.py`/`submit.sh` | PASS; series-local takes priority, root submit is fallback only. |
| Historical package QA is described as CRC/member verification when it only compares package/mirror hashes | Inspected golden `package.py` and `submit.py` | PASS; memory records the SHA-only limitation and actual mirror-before-QA order. |

Residual: routing behavior was checked statically; no JoSIM, skill-router runtime,
or scientific interpretation was invoked.
