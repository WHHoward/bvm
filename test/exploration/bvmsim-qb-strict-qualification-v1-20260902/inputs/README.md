# Stage A inputs

`prepare_decks.py` derives the two migrated decks from the preserved
`BVMSim/test_bvm_mixed_0.cir` fixture after checking its SHA-256.  The
derivation is deliberately limited to:

1. using the shared `jjmit` model;
2. importing the active QB as `BQ_BVMSIM_V1`;
3. exposing the unchanged 250-uA bias source at `QB_BIAS`;
4. replacing the historical print block with explicit QB/JTL diagnostic
   observables; and
5. changing only the S1 timestep and output start rule.

The four-BVM fixture, accumulated sensing line, exact BVMSim JTL, final 10-ohm
load, stimulus schedule, and QB component values remain fixed.
