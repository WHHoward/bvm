# Numerical review — mechanical only

- M values are exact registered values; K=M/sqrt(0.5*10) is derived without a free K sweep.
- The two-winding matrix audit records |K|<1, determinant and positive eigenvalues.
- All integrations and comparisons use actual stored timestamps; no interpolation/resampling.
- R_AUX dissipation is computed as actual-grid integral of I(R_AUX)^2*20 ohm and is not a hardware claim.
- P(...) is raw radians; rad/(2*pi) turns are navigation only.
