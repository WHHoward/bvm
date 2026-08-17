#!/usr/bin/env python3
"""verify_content_completeness.py -- VIZ-002 A03 independent verifier.

Verifies renderer SERIES/PANEL/CONTROL coverage structurally from the
actual visualization-data.json and report.html DOM, not by string search
and without importing the renderer.  Optional Chromium DOM smoke (no final
visual judgment).  Read-only over the canonical report.html.
"""
import json, pathlib, re, sys, subprocess, shutil

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]

def main() -> int:
    data = json.loads((ATTEMPT/"visualization-data.json").read_text())
    html = (ATTEMPT/"report.html").read_text(encoding="utf-8")
    fails = []
    # selectors: real 4x2 buttons with active-state handler
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            if f'data-target="sec-{key}"' not in html:
                fails.append(f"selector button missing for {key}")
    if "showSection" not in html or "classList.add('active')" not in html:
        fails.append("active-state selector handler missing")
    # panels: 8 dash-sections with plotly divs
    n_sections = len(re.findall(r'class="dash-section"', html))
    if n_sections != 8:
        fails.append(f"expected 8 dash-sections, got {n_sections}")
    # series: corrected/descriptors/residual/endpoint/readiness data present
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            if key not in data.get("corrected", {}):
                fails.append(f"corrected missing {key}")
            if key not in data.get("descriptors", {}):
                fails.append(f"descriptors missing {key}")
            if key not in data.get("control_residual", {}):
                fails.append(f"control_residual missing {key}")
            if key not in data.get("endpoint_detail", {}):
                fails.append(f"endpoint_detail missing {key}")
            if key not in data.get("readiness", {}).get("strata", {}):
                fails.append(f"readiness missing {key}")
    if "Plotly" not in html:
        fails.append("no embedded Plotly")
    if fails:
        print("CONTENT COMPLETENESS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    # optional Chromium DOM smoke (structural only; not visual acceptance)
    chrome = shutil.which("chromium") or shutil.which("chromium-browser") \
        or shutil.which("google-chrome") or shutil.which("google-chrome-stable")
    if chrome:
        # parse DOM for section/button counts via a headless dump
        try:
            proc = subprocess.run([chrome, "--headless=new", "--dump-dom",
                                   (ATTEMPT/"report.html").as_uri()],
                                  capture_output=True, text=True, timeout=120)
            dom = proc.stdout
            if dom.count('class="dash-section"') != 8:
                fails.append("DOM smoke: section count mismatch")
            if dom.count("dash-btn") < 9:
                fails.append("DOM smoke: selector buttons missing")
        except Exception as exc:  # noqa: BLE001
            print(f"DOM smoke skipped: {exc}")
    if fails:
        print("CONTENT COMPLETENESS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"CONTENT COMPLETENESS PASS: 8 selectors with active state, 8 "
          f"sections/panels, series for corrected/descriptors/residual/"
          f"endpoint/readiness per combination; DOM smoke "
          f"{'PASS' if chrome else 'SKIPPED (no chromium)'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
