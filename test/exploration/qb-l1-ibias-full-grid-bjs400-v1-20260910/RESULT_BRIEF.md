# BJS400 ARRAY L1 x IBias complete coarse grid — evidence-only result

Scientific interpretation is `NOT_PERFORMED`.

The registered grid contains 24 logical cases: L1={1.2, 1.4, 1.6, 2.0}pH,
IBias={250, 260, 270}uA and masks {0001, 0011}. Fourteen cases are immutable
historical reuse; exactly ten newly authorized physical solves cover the five
missing parameter points and both masks.

The fixture is fixed at BJS area=4 (Ic=400uA), RJ1=12ohm, the stored history
`WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> FINAL READ -> TAIL`,
and the 0.1ps / 200ps solver setting. Mechanical metrics preserve raw phase in
radians and label `rad/(2*pi)` values as diagnostic turns only.

See `qa/` and `mechanical_summary.json` for artifact/mechanical QA, and
`visualization/manifest.json` for the exact 30 standalone and two full-grid
comparison pages. No focused plots, heatmaps, dashboards, event/SFQ classifier,
ranking or follow-up solve is included.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
