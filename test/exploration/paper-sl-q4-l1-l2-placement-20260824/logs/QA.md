# PAPER-SL-Q4 artifact QA

## Artifact checks

- four JoSIM exit codes are zero;
- four stderr files are empty;
- each CSV has one header plus 13,599 data rows and 22 columns;
- time is strictly increasing, final time is 169.9875 ps, and the configured
  timestep is 0.0125 ps; raw CSV output spacing is approximately 0.0125–0.025 ps
  with one inherited PWL gap per deck;
- generated Q4 deck differs from Q2 only at the local `L2` line;
- `L1=3.91p` and the four replay decks remain unchanged;
- analysis scripts compile with `python3 -m py_compile`;
- raw event claims are based on continuous unwrapped phase and direct same-JJ
  voltage-area, not on `I>Ic`, voltage peak, total phase range, or old fast-event
  metrics.

## Scientific boundary

The Q4 fixture is an ideal replay QB fixture. It does not contain physical BVM
columns (`V(SL)`, `V(N6)`, `I(L_SL)`, `JM1/JM2`, `JS1/JS2`), so this checkpoint
does not make a new BVM source-guard claim. It only compares the frozen replay
boundary under Q2/Q3/Q4 local QB inductance placement.
