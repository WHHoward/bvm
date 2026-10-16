# PREFLIGHT — SE375_G1_A1_B8

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- experiment_risk_level: NORMAL
- parent_head: 04d6aa304a22f9be99d1f9821d212ccb5e8905d6
- run_id: V9R005_SE375_G1_A1_B8
- run directory: /home/howard/JoSIM/test/exploration/sfq_clock_two_read_v1/runs/V9R005_SE375_G1_A1_B8
- run mode: LOCAL_ONLY
- platform script SHA-256: eb597d0e8d63913c0059445ca8e13107e44a82b8deed2ab983d900c8cb724233
- solver: /home/howard/JoSIM/build/josim-cli; version: JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57; binary SHA-256: 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
- topology: V9_SHARED_ROW_SE_BL; 16 BVM, 16 QB, seven diagonal T1 channels, six carry CBs, one DFF
- this invocation authorizes one solve only
- scientific interpretation: not performed or authorized by this runner

## Effective inputs

- A=1; B=8; ROUNDS=3
- row mapping R1=LSB: 1000
- column mapping C1=MSB: 1000
- READ starts (ps): 110, 190, 270
- CLK PWL starts (ps): 178, 258, 338
- WRITE1 start=50 ps; DT=0.01 ps; STOP=400 ps
- amplitudes: {"BL_READ_AMPLITUDE": "400u", "BL_WRITE_AMPLITUDE": "400u", "SE_READ_AMPLITUDE": "375u", "WL_WRITE_AMPLITUDE": "400u"}
- protocol: V9_SHARED_ROW_SE_BL; legacy fallback disabled

## Frozen source closure

- 00_jjmit.cir: 19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336
- 01_bvm_cell_0923.cir: 76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489
- 02_BQ_0928.cir: 82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a
- 03_sJTL_0923.cir: 3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688
- 04_CB_0928.cir: 70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370
- 05_MERGE.cir: 79b0d219db60ca41a03d732eaac82b436114b02436cf4dc8719e9b25d58940e0
- 06_dcsfq2.cir: 76e9866ef32a73ac8bda2a4698ba1d39dc8e1c83312da168ba0aab8eee5fc280
- 07_jtl2.cir: 9ec481453c5aa519dec18c07efc2c377b11f3ca0345c6e7971bd6806036455aa
- 08_t1_cell_tunable.cir: da7f1c5065081caccbd6cbd698630a9cf94019840e39e3beb0839b99e5e7bcdb
- 09_DFF.cir: e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0
- 10_d0_jtl_tunable.cir: b242741e4630a54411db48de649361e8daedfd6a083358d675d2fdf657314039

## Probes

JoSIM P(...) raw values are radians. Probes are descriptive and are not event counts.

- V(S_D0_OUT) [V] endpoint={"nodes": ["S_D0_OUT"]}; direction=S_D0_OUT relative to ground
- V(S_D1_OUT) [V] endpoint={"nodes": ["S_D1_OUT"]}; direction=S_D1_OUT relative to ground
- V(S_D2_OUT) [V] endpoint={"nodes": ["S_D2_OUT"]}; direction=S_D2_OUT relative to ground
- V(S_D3_OUT) [V] endpoint={"nodes": ["S_D3_OUT"]}; direction=S_D3_OUT relative to ground
- V(S_D4_OUT) [V] endpoint={"nodes": ["S_D4_OUT"]}; direction=S_D4_OUT relative to ground
- V(S_D5_OUT) [V] endpoint={"nodes": ["S_D5_OUT"]}; direction=S_D5_OUT relative to ground
- V(S_D6_OUT) [V] endpoint={"nodes": ["S_D6_OUT"]}; direction=S_D6_OUT relative to ground
- V(DFF_O) [V] endpoint={"nodes": ["DFF_O"]}; direction=DFF_O relative to ground

## Artifact scope

- expected raw: raw.csv in this run directory
- expected output page: res.html (eight final output voltages only)
- expected custom page: none
- archive: not requested; local evidence only
- Drive folder ID (archive mode): not used
- visualization: standalone res.html using scripts/josim-plot2.py, stacked/dark, phase display rad/(2*pi)
- custom diagnostic plot: none
- no SFQ classifier, arithmetic verdict, timing-margin analysis, or mechanism report
- run artifacts include deck, stimulus, env snapshot, this PREFLIGHT, probe manifest,
  raw/log where produced, per-run manifest, frozen sources, and res.html when raw QA permits
