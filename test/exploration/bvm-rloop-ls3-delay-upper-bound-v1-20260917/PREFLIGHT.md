# LS3 ideal timing upper bound — bvm-rloop-ls3-delay-upper-bound-v1-20260917

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: 1348140f17f0d9467dc42238eaa1e252e877e07a; remote bvm/master: 1348140f17f0d9467dc42238eaa1e252e877e07a.
- Study phase: EXPLORATORY; role: Experimental Operator + Evidence Packager.
- Initial fixed cases are LS3_DELAY0P5_0011 and LS3_DELAY0P5_0111. The 0.6-ps pair is conditional on the fixed mechanical gate.
- Validated LS3-only topology: physical R_S retained, physical L_S3 replaced by a same-instance ideal I(L_S3) replay; canonical QB/JSL/JTL/terminal unchanged.
- t0=110 ps; 0.5 ps is 5 stored samples and conditional 0.6 ps is 6 stored samples. The hold interval and later index shift use the actual stored grid.
- No interpolation, smoothing, resampling, scaling, polarity change, N1/N4, other delay, sentinel or timestep sweep.

## Authorized matrix

1. LS3_DELAY0P5_0011
2. LS3_DELAY0P5_0111
3. Conditional only if fixed N2=2, N3=3, and N2 second response/re-arm remains present: LS3_DELAY0P6_0011 and LS3_DELAY0P6_0111

Maximum new physical solves: 4. Navigation/phase turns are diagnostics, not literal SFQ counts.

## Runner

    chmod +x run.sh
    ./run.sh --dry-run
    ./run.sh

Edit only the USER-EDITABLE PARAMETERS block. Default raw overwrite is refused; --force creates a timestamped sibling backup.

Canonical branch direction/KCL audit: {"0011": "PASS", "0111": "PASS"}.
Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW; scientific interpretation is not performed.
