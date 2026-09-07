# ANALYSIS-01 — superseded derived analysis

- Status: **SUPERSEDED**
- Reason: the first analysis pass registered the shared-node balance with the wrong sign, `sum_i I(L_SL|XBVMi) + I(B_JSL1)`. Raw inspection shows `I(B_JSL1)` has the same sign as the summed `L_SL` branches, so the checked identity is `sum_i I(L_SL|XBVMi) - I(B_JSL1) = 0`.
- The four physical raw files were not changed. This directory preserves only the superseded derived JSON and plot-input CSVs; it is not scientific authority.
- The optional `V(IB|XBQ1)` probe was absent from the JoSIM raw schema and was already treated as optional.
