# Numerical review — mechanical only

- 0.5/0.6 ps use exact stored shifts of 5/6 samples and a 110-ps hold.
- Integrations and comparisons use actual stored timestamps; no interpolation/resampling.
- P(...) is raw radians; turns are independent unwrap/(2*pi) navigation only.
- No timestep/solver sensitivity or physical delay-equivalence claim was tested.
