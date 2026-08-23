# R15-B summary

- **Parent:** `571fa918f9623e24ea8038bfb24c32087494316e`
- **Mode:** single-point Exploration execution after analytic gate
- **JoSIM executed:** yes, exactly four matched cases; no sweep
- **Selected route:** split-winding / two-core magnetic transfer
- **Single point:** `L_FQ=L_FO=20 pH`, `R_F=20 Ω`, `K_QFQ=+.90`, `K_FOCTL=-.90`,
  `K_QCTL=K_FQFO=0`
- **Analytic verdict:** `R15B_SINGLE_POINT_WORTH_TESTING`
- **Execution verdict:** `ACTIVE_STAGE_NO_TRIGGER`
- **Source disposition:** `BOUNDED_EXTRA_BACK_ACTION_NOT_ISOLATED`

The corrected AFQ magnetic matrix is positive definite. The topology preserves
the existing `J_Q` refractory branch without a direct `Q→CTL` mutual, keeps the
independent `J_OUT=275 µA` bias-powered output valve, and preserves the
R15-A-local mutual numerator and approximately 2 ps bridge time scale.

The first `logical1 + READ=0` control was stable with no complete AFQ/DCSFQ
segment or free-running, so the other three matched cases were executed. Read1
preserved a `3.913019-turn` B_DET monotonic segment with same-JJ voltage area
`3.913047 turn`; read0 was `0.184906 turn` and controls were inactive.

No J_SET/J_Q/J_OUT read1-selective active sequence appeared. Frozen DCSFQ
`I(L1)` peaked at only `0.510835 µA` and was identical across all four cases;
B3's largest segment was `0.00005774 turn`, so there was no local B3 event.

The source/storage logical signs remained distinct and post ringing decayed,
but read1 source disturbance was materially above canonical no-receiver
baseline. This is recorded as bounded extra back-action, not as a clean source
isolation pass. No downstream SFQ/JTL claim is made.

Detailed evidence is in `analysis/R15B_EXECUTION_REPORT.md`; raw and hashes are
listed in the manifest and `analysis/sha256sums-execution.txt`.
