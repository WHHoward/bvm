This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

# C5R28_210 preflight

- Scope: exactly 28 sequential manual JoSIM solves from the committed
  `run_carry5_functional_28.sh`; A076-A078 are immutable completed anchors and
  are never rerun.
- Initial repository HEAD: `8531d1f172e7bb5a2c22248eb9be248bdf75bdfa`.
- Batch script commit: `b8d4ac6f83d0576b445da5b85139661bab43a230`.
- Parent HEAD used by the final preflight lock is recorded in
  `preflight.ok` and each new run's provenance.
- Baseline run: `A077_MANUAL_CARRY5_15x15_210`; deck SHA-256
  `469247887bd0be999cc39acaad4277191e9aa426273b719615b9b5ddf0cd3a42`, raw
  SHA-256 `e4477449666543784e978cc86e258aa48eee2fce4edcbd540ceb266a11a4c016`.
- Frozen configuration: D3 PRE-CB Carry sJTL counts `1,1,5,1,1,1`; D3 array
  sJTL counts `1,2,2,1`; global one-shot clock at 210 ps; shared WL/BL 400 uA,
  independent SE 100 uA; `DT=0.01 ps`, `STOP=300 ps`, focus `D3`.
- All other circuit, stimulus, T1, CBU, DFF, bias, and topology parameters
  must match A077. Each candidate rendered deck must have the exact A077 deck
  SHA before any physical solve.
- Input order and row/column encoding are frozen in `experiment.yaml` and the
  runner: ROW_BITS lists R1 first (R1 is LSB); COL_BITS lists C1 first (C1 is
  MSB). No input/output product decoding is performed.
- Solver: `/home/howard/JoSIM/build/josim-cli`, version
  `v2.7.2837d13 compiled May 30 2026 20:37:57`, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Before execution: local `master` and `bvm/master` matched; `/` had about
  700 GB free and `/mnt/d` about 124 GB free; Google Drive folder
  `BVM_Backages` was reachable and no file with the new DELTA tag existed.
- Required static gate: 28/28 `./try.sh --dry-run` PASS, 28/28 static deck
  checks PASS with the exact A077 deck SHA, and zero physical solver calls.
- Physical authorization: after the full static gate, exactly 28 new sequential
  solves in the registered order. Any solver, raw-artifact, or mechanical-QA
  hard failure stops the batch; no retries, tuning, decoding, interpretation,
  or follow-up are authorized.
- Required per-run mechanical QA: valid artifact, solver exit 0, immutable raw
  SHA, raw/static/chain/plot QA PASS, provenance, and complete run snapshots.
- Archive: only the 28 new run raws plus their metadata in the generic manual
  DELTA; A001-A078 raw are references only; HTML is excluded; no extra
  `--track-packaged-raws` route.
- Interpretation ceiling: artifact readiness and mechanical QA only;
  scientific interpretation is left to the user and ChatGPT.
