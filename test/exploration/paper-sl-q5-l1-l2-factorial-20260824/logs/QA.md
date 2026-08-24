# PAPER-SL-Q5 artifact QA

- four JoSIM exit codes are zero;
- four stderr files are empty;
- each CSV has one header plus 13,599 data rows and 22 columns;
- each time axis is strictly increasing and ends at 169.9875 ps;
- configured integration timestep is 0.0125 ps; observed CSV output spacing is
  approximately 0.0125–0.025 ps with one inherited PWL gap per deck;
- Q2→Q5 circuit diff contains exactly the two registered L1/L2 replacements;
- four replay decks and jjmit model are byte-identical to Q2;
- analysis scripts compile with `python3 -m py_compile`;
- event claims use continuous unwrapped phase plus direct same-JJ/same-segment
  voltage area, never current threshold or voltage peak alone.

The fixture is an ideal replay QB fixture and does not contain physical BVM
source-guard columns (`V(SL)`, `V(N6)`, `I(L_SL)`, `JM1/JM2`, `JS1/JS2`).
