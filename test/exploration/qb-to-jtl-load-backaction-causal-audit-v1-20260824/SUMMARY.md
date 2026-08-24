# QB→JTL load back-action causal audit v1

## Verdict

`MIXED_DYNAMIC_LOADING`

## Established within the frozen fixture set

- The accepted 10 Ω boundary gives one bounded Q0 BJL2 event.
- OPEN gives multiple local BJL2 events, so the 10 Ω boundary participates in
  one-shot/retrap behavior.
- Direct JTL-only and 10 Ω∥JTL change the pre-crossing settled load-line and
  lose the BJL2 event before a complete crossing is formed.
- M3 series-10 Ω preserves the local BJL2 event but remains below the tested
  JTL transport event criterion.
- Node-4 KCL closes to pA/sub-pA-scale residuals in the reported windows.

## Interpretation boundary

The result is a bounded classification of the five accepted Q0 fixtures. It
does not reduce the interface to a universal scalar impedance, does not prove
a universal load specification, and does not establish physical BVM→JTL
delivery. No transformer, R/L/Ic/bias tuning or new JoSIM run was performed.

See [the full report](analysis/REPORT.md),
[the preregistration](PREREGISTRATION.md), and
[the provenance manifest](analysis/manifest.json).
