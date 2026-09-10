# RJ2=12 timestep robustness — evidence-only result

Scientific interpretation is `NOT_PERFORMED`.

This experiment reuses the canonical RJ2=12 0.1ps pair and runs only four new
physical cases at 0.05ps and 0.025ps. It changes no circuit parameter and does
not redefine the canonical `.tran=0.1p` timestep.

The repaired oracle and the finite timestep comparison are recorded in
`qa/timestep_qa.json`, `mechanical_summary.json` and `analysis/TIMESTEP_REVIEW.md`.
Any stable classification is local to these tested conditions and is not a
convergence theorem, hardware claim or final SFQ proof.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
