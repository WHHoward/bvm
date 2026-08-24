# Window robustness disposition

The numerical ladder itself passed for all three fixtures, and the reverse
signed transport oracle remained non-transport. The freeze did not close
because one pre-registered independent window family was not fully stable:

- `pulse5-original`: 18/27 pre/post combinations passed;
- all failures were the `post-plus` combinations at the three timestep
  values, for each of the three pre variants;
- the affected downstream JTL settled p2p comparison exceeded the registered
  `0.005 turn` window band for at least one downstream JJ;
- the same traces retained the positive settled-well vector, phase/area
  consistency, causal onset order, and full-tail no-extra-event guard.

This is a bounded numerical robustness failure/inconclusive Gate result, not
a JTL transport physics failure. No window, timestep, or physical parameter
was changed after observing it.
