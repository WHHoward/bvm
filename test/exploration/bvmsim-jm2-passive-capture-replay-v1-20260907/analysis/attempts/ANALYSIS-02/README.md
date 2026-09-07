# ANALYSIS-02 — superseded independent check

- Status: **SUPERSEDED**
- Reason: the first independent checker compared a `(time, current)` tuple with a current scalar when checking `I(I_REPLAY)` against `I(LIN|XBQ1)`. A direct raw inspection showed zero differing rows; the checker logic, not the raw data, was wrong.
- The failed JSON and review are preserved here. The four physical raw files were not changed.
