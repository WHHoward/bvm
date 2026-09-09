# Minimal L1 x IBias interaction under BJS400

This is an evidence-only handoff. Scientific interpretation is NOT_PERFORMED.

The physical and stimulus authority is the completed BJS400 ARRAY experiment
qb-bjs400-array-population-single-matched-v1-20260909. The exact history is
WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL
READ -> TAIL, with 0.1ps timestep and 200ps stop time.

The registered matrix has four corners:
A = L1=2.0pH, IBias=250uA
B = L1=2.0pH, IBias=260uA (historical immutable reuse)
C = L1=1.6pH, IBias=250uA
D = L1=1.6pH, IBias=260uA

Only masks 0001 and 0011 are authorized. There are exactly six new physical
solves and two reused historical BJS400 cases. No extra mask, parameter,
SINGLE run, retry, tuning, focused plot, mechanism analysis or follow-up is
authorized.

Standalone plots are raw.csv-direct whole-run 0-200ps pages. Comparison input
CSV files are temporary files under /tmp and are deleted after rendering.

