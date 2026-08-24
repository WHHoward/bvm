# Execution record

- Parent accepted HEAD: `8bb86f61c3243655467d61f00680977349b41cf3`
- Mode: read-only bounded audit of accepted raw evidence
- New JoSIM runs: none
- Parameter/topology changes: none
- Analysis command: `python3 analysis/audit_load_backaction.py`
- JoSIM binary: `build/josim-cli` v`2.7.2837d13`
- Binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Model/JTL parameters: inherited unchanged from the accepted parent fixtures

The five cases were loaded from their accepted raw CSV/fixed-width outputs.
The pulse-5 reference event and the pre/crossing/retrap windows were resolved
from the accepted Q0+10 ohm trace, then applied identically to every case.
All currents and node-4 KCL residuals were recomputed from the raw columns;
no missing probe was imputed.
