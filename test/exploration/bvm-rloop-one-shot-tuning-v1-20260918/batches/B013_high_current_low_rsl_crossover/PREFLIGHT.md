# B013 — high-current BVM × low-RSL source-delivery crossover validation

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Status: PRE-REGISTERED / PASSIVE SANITY + CLOSED CROSSOVER / NO QB-JTL MODIFICATION

Registered matrix:

- S1-R6 PASSIVE N1/N4: `SE=110u`, `JS1=.74`, `JS2=.90`, `RSL=6`.
- S2-R6 PASSIVE N1/N4: `SE=120u`, `JS1=1.00`, `JS2=1.00`, `RSL=6`.
- S0-R12 CLOSED N1/N2/N4: strict reuse from U039.
- S0-R6 CLOSED N1/N2/N4: strict reuse from U097.
- S1-R12, S1-R6, S2-R12, S2-R6 CLOSED N1/N2/N4: new solves.

Expected logical points: 22. Expected strict reuse: 6. Expected new physical
solves: 16. No Track-A sweep, no LM3/RSL sweep, no combined knob search, no
additional CLOSED cases, and no QB/JTL/terminal source edits.

All raw, deck, stimulus, source, time-grid and plot QA are required. Scientific
terminal/event/Gate/decomposition conclusions require the explicit scientific
review authorization and must separate Observed, Derived, Inference, and
Unknown.
