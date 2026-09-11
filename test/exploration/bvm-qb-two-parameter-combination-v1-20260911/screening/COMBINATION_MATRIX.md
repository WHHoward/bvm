# Two-parameter full closed-loop QB combination matrix

All points use the registered full BVM→COMMON_SL/JSL→QB→six-stage JTL→terminal topology, `.tran 0.1p 200p`, and masks `0011`/`0111`.

| order | id | changed parameters | N2 deck | N3 deck |
|---:|---|---|---|---|
| 1 | `C01` | `L2_pH=1.6`, `L3_pH=1.6` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C01/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C01/0111.cir` |
| 2 | `C02` | `L2_pH=1.6`, `L1_pH=1.2` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C02/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C02/0111.cir` |
| 3 | `C04` | `BJ1_area=1.1`, `L3_pH=1.6` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C04/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C04/0111.cir` |
| 4 | `C03` | `L2_pH=1.6`, `RJ1_ohm=40` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C03/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C03/0111.cir` |
| 5 | `C05` | `BJ1_area=1.1`, `L1_pH=1.2` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C05/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C05/0111.cir` |
| 6 | `C07` | `IBias_uA=240`, `L3_pH=1.6` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C07/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C07/0111.cir` |
| 7 | `C06` | `BJ1_area=1.1`, `RJ1_ohm=40` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C06/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C06/0111.cir` |
| 8 | `C08` | `IBias_uA=240`, `L1_pH=1.2` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C08/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C08/0111.cir` |
| 9 | `C09` | `IBias_uA=240`, `RJ1_ohm=40` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C09/0011.cir` | `test/exploration/bvm-qb-two-parameter-combination-v1-20260911/screening/decks/C09/0111.cir` |

Registered combination points: `9`; logical cases: `18`; maximum new screening solves: `18`; validation, if and only if a clean S point is found: `0001` and `1111` (at most 2 additional solves).
