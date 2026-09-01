# Preserved post-processing failure

The single authorized candidate solver run completed with return code `0` and
produced a complete raw CSV. The first `scripts/bvm-exp.py` post-processing
attempt then failed while selecting a registered signal because the config used
`I(Lin|XBQ)` while the exact JoSIM header is `I(LIN|XBQ)`.

- candidate run id: `13ps-12x320-logical1-read-lsl-removed`
- raw SHA-256: `d31cdfdddcf5b7db7ee2a1c323c6f349e1d7eff593bc8fb198cb72ba0d0c4984`
- raw size: `13489216` bytes
- raw QA: valid, 13599 samples, 0–169.9875 ps, duplicate `I(B_LD1)` and
  `I(B_LD12)` occurrences retained
- solver: `build/josim-cli`, return code `0`
- failed layer: analysis signal lookup only; no circuit or raw-data failure

The raw, solver logs, and deck snapshot in this directory are preserved and are
consumed by the corrected analysis. They are not overwritten or silently
deleted; no second science run is needed for this tooling-only correction.
