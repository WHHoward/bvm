# RJ1 switched-regime characterization under D working point

This is an evidence-only handoff. Scientific interpretation is NOT_PERFORMED.

The fixed working point is L1=1.6pH, IBias=260uA, BJS area=4/Ic=400uA.
Only RJ1 varies: new 10/14/16ohm runs, with RJ1=12ohm represented by
two immutable historical D references.

All runs preserve the successful history:
WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL
READ -> TAIL. The only masks are 0001 and 0011. The physical solver, timestep,
stop time, BVM/COMMON_SL/JSL/QB/JTL topology and broad raw probes are frozen.

Each new run has exactly three raw-direct whole-run HTML pages. Exactly two
comparison pages use temporary CSV files under /tmp, deleted after rendering.
No event classifier, SFQ counter, mechanism analysis, ranking, tuning or
follow-up is authorized.

