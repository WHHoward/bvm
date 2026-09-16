# Numerical review — mechanical only

- Delay transforms use exact stored index shifts of 2 and 4 samples, with 110-ps hold and half-open windows.
- All integrations use actual stored timestamps; no interpolation/resampling.
- P(...) is raw radians; turns are independent unwrap/(2*pi) navigation only.
- Same-JJ JS1/JS2 phase-area records use matched endpoints/direction/window.
- No timestep/parameter/solver sensitivity was run; convergence is UNKNOWN.
