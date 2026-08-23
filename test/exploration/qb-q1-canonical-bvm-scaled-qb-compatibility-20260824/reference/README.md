# QB-Q1 canonical no-receiver references

These four CSV files are immutable copies of the existing canonical BVM readout evidence from `test/exploration/bvm-internal-readout-20260819/`. They are used only as source/storage guard baselines; QB-Q1 does not modify or reinterpret the original exploration.

| copied file | source | SHA-256 |
|---|---|---|
| `logical1-read-no-receiver.csv` | `raw/pos-read-single/run-01.csv` | `3674b974dc0c897402745436a083704c1320560242ac20ba0634d11f6d18d2fa` |
| `logical0-read-no-receiver.csv` | `raw/neg-init-pos-read/run-01.csv` | `f2c58c10de5f4ef91b10d7e8de72a420bf5238a19caf0b0106aa3b440ba99a4b` |
| `logical1-read0-no-receiver.csv` | `raw/pos-control/run-01.csv` | `2325b12fde4be62bcc3d72f062d6db872f68de198d40912a6173f954a1b9f00a` |
| `logical0-read0-no-receiver.csv` | `raw/neg-control/run-01.csv` | `efe88f80194a96c25ce09d48b8f63427ffab807fe6a69a45da045c3ab6665a93` |

The canonical baseline already contains the BVM-side probes `V(SL1)`, `V(N6|XBVM1)`, `I(L_SL|XBVM1)`, `JM1/JM2`, and `JS1/JS2`. Absolute logical1/read1 JS1/JS2 running is expected source behavior and must not be counted as receiver back-action without a differential comparison.
