# BVMSim source snapshot boundary

Stage A treats the existing `BVMSim/` tree as historical/exploratory source
evidence.  The files listed in `SHA256SUMS.txt` remain in place and are not
edited, cleaned, renamed, deleted, or overwritten.  The historical
`BVMSim/data_tran.csv` is read only for M0 comparison; it is not a mutable
experiment output.

The migrated decks reference the preserved BVMSim BVM and the exact preserved
BVMSim `library_josim/jtl2.cir`.  Only the active QB packaging is replaced by
`circuits/qb/bq_cell_bvmsim_v1.cir`.

`BVMSim/bvm_cell.cir` is not canonical BVM authority.  In particular, its
`R_JM1` is 8 ohm, while `circuits/bvm/bvm_cell.cir` uses 6 ohm.  Stage A does
not reconcile this difference and does not claim that canonical BVM drives
this QB.
