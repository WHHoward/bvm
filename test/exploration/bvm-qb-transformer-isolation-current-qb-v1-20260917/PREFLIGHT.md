# R6-style transformer isolation of current population QB — bvm-qb-transformer-isolation-current-qb-v1-20260917

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: 1348140f17f0d9467dc42238eaa1e252e877e07a; remote bvm/master: 1348140f17f0d9467dc42238eaa1e252e877e07a.
- Study phase: EXPLORATORY; role: Experimental Operator + Evidence Packager.
- Current canonical population QB is retained unchanged. The direct B_JSL8 JSL_NODE7-to-QBIN connection is removed and replaced by the frozen passive interface.
- Frozen interface: R_PRI=12.0 ohm, L_PRI=0.20 pH, L_SEC=2.00 pH, K_ISO=0.50, M=0.31622776601683794 pH.
- Topology: B_JSL8 -> ISO_SOURCE_OUT -> R_PRI -> L_PRI -> ground, with L_SEC QBIN -> ground and K_ISO coupling. Canonical QB/JTL/BVM internal parameters otherwise remain unchanged.
- No parameter sweep, R6-B ratio point, added JJ, current/voltage source, bias, C, PTL, or timestep refinement.
- Fixed cases are ISO_R6A_0011 and ISO_R6A_0111. Conditional N1/N4 cases run only if both fixed cases mechanically give N2=2 and N3=3.
- JoSIM .tran 0.1p 200p; all integrations use actual timestamps. P(...) is raw radians and turns are navigation only, not literal SFQ counts.

## Runner

    chmod +x run.sh
    ./run.sh --dry-run
    ./run.sh

Edit only USER-EDITABLE PARAMETERS in run.sh. Default raw overwrite is refused; --force creates a timestamped sibling backup.

Static K/matrix audit: PASS; canonical branch audit: {"0011": "PASS", "0111": "PASS"}.

Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW; scientific interpretation is not performed.
