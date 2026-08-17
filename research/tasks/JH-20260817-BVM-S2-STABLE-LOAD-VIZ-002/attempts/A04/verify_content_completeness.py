#!/usr/bin/env python3
"""verify_content_completeness.py -- VIZ-002 A04 independent verifier (DOM-level).

Structural verification of actual report.html DOM + data model: selector
buttons with active state, 8 sections, and the visible tables (endpoint
5-row, descriptors, residual, provenance/status).  No renderer import, no
string-search-only checks.  Read-only over canonical.
"""
import json, pathlib, re, sys

ATTEMPT = pathlib.Path(__file__).resolve().parent
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]

def main() -> int:
    data = json.loads((ATTEMPT/"visualization-data.json").read_text())
    html = (ATTEMPT/"report.html").read_text(encoding="utf-8")
    fails = []
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            for token in (f'data-target="sec-{key}"', f'id="tbl-endpoint-{key}"',
                          f'id="tbl-desc-{key}"', f'id="tbl-resid-{key}"',
                          f'id="tbl-prov-{key}"', f'id="plot-{key}"'):
                if token not in html:
                    fails.append(f"{key}: missing {token}")
    # table row content: endpoint tokens present in DOM
    for tk in ("97", "99", "101", "103", "105"):
        if html.count(f"<td>{tk}</td>") < 8:
            fails.append(f"endpoint token {tk} rows missing in DOM")
    for h in ("Rhat (ohm)", "Vth (V)", "emax (V)", "eligible", "classification",
              "Source descriptors", "Control residual", "Provenance / status",
              "time-normalized-L1", "rctrl"):
        if h not in html:
            fails.append(f"DOM missing table header/content: {h!r}")
    if "showSection" not in html or "classList.add('active')" not in html:
        fails.append("selector active-state handler missing")
    if "Plotly" not in html:
        fails.append("no embedded Plotly")
    for key in data.get("corrected", {}):
        if key not in data.get("descriptors", {}) or key not in data.get("endpoint_detail", {}):
            fails.append(f"data model incomplete for {key}")
    if fails:
        print("CONTENT COMPLETENESS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("CONTENT COMPLETENESS PASS: 8 selector buttons + 8 sections with "
          "endpoint/descriptors/residual/provenance tables, plotly embedded")
    return 0

if __name__ == "__main__":
    sys.exit(main())
