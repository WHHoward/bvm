# Numerical review — mechanical only

- Actual stored grid is retained; no interpolation/resampling was used.
- Exact gate uses all registered phase landmark timing, active JS1/JS2 focus p2p, key waveform normalized RMS, and replay-source injection error.
- Same-JJ phase/voltage-area checks use common endpoints, direction and [110,121) ps actual-grid trapezoids.
- P(...) remains raw radians; displayed turns use independent unwrap/(2*pi) navigation only.
- Timestep/convergence sensitivity and physical equivalence are UNKNOWN/not tested.
