# D3 Carry timing A040/A041 — evidence-only summary

- Physical solve count: 2 new solves; A036 is a read-only baseline reference.
- Mechanical QA only; scientific interpretation and event/SFQ classification: NOT PERFORMED.
- DOUT and JOIN share a node; DOUT voltage is not treated as an array-only event count.
- `P(...)` is raw radians; phase/2π is navigation arithmetic only.

| Run | D3 Carry sJTL count | Raw bytes | Samples | Raw SHA-256 | QA |
|---|---:|---:|---:|---|---|
| A036_PRE_CB_SJTL_ALL_200 | 1 | 94506907 | 29999 | `586ba6eafa62d25bf6cd7a7ea8b533903826616b4b5575a9023f7393b74faf75` | PASS |
| A040_D3_PRE_CB_SJTL_0_ALL_200 | 0 | 85514801 | 29999 | `3c3ec6904b900e6a3a2c8bbac82431eca05150b3aad58c52feec10b29bf7ae61` | PASS |
| A041_D3_PRE_CB_SJTL_2_ALL_200 | 2 | 89494895 | 29999 | `e1037690671ff9457b9e032a65332cedf6d0c4f93af55ae44dfc3124521d7792` | PASS |

## Registered arithmetic

See the stage and same-JJ tables for exact-window P/V cross-checks, branch-current arithmetic, output areas, and stored-grid time descriptors. No pulse count, mechanism, or product-bit verdict is assigned by this report.

## Visualizations

- A036_A040_A041_D3_FOCUS.html: `35c661817f4a0059a5bae9d99373ba906c977e040580620660666ab2a7152340`
- A040_A041_D3_EXTENDED_JJ.html: `e890e25528de957adac72b619b1cd532e72f7b26214e0337175c055b337815b4`
- A036_A040_A041_D3_CARRY_PATH.html: `e828c8ce5712093553c7c6413038771eff03de2a112321e54fb48f8b21dcf425`
- A036_A040_A041_FULL_CHAIN.html: `e8409e56af0c5e591516add3f82ec5b4ce0b3a2e8ec7ae906cc33052902e0779`
- A036_A040_A041_OUTPUTS_DFF.html: `396ec1e94ffd9e44feffb1fc309843fe1c5c219d5fd9fd32b26d92ad2d01126e`
