# Numerical review — mechanical only

- K matrix is recomputed as M=K*sqrt(1.5*10) pH; positive-definiteness is checked for all registered K.
- K=0 fixture uses a grounded L/R loop and no new JJ/bias; its no-op gate is separate from physical success.
- Auxiliary energies and deltas use actual stored timestamps; no interpolation/resampling.
- P(...) remains raw radians; turns use independent unwrap/(2*pi) navigation only.
- No timestep/solver/process sensitivity or physical delay-equivalence claim is made.
