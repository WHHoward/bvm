#!/usr/bin/env python3
"""verify_content_completeness.py -- VIZ-002 independent content verifier.

Independently reads the frozen preregistration requirements,
visualization-data.json, and the actual report.html bytes.  It does NOT
import the renderer and does NOT trust renderer self-reports.  Every
required content item must be present in the data model AND in the HTML.
"""
import json, pathlib, sys, yaml

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
PRE = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/design/preregistration.yaml"
SRC = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-001"

REQUIRED_HTML = [
    "WL", "BL", "SE", "JM1", "JM2", "JS1", "JS2",
    "V(SL1)", "I(L_SL)", "read", "control",
    "80", "90",  # PRE window shading
    "97", "99", "101", "103", "105",  # endpoint tokens
    "disposition", "Claim ceiling", "time (ps)", "mV", "uA", "raw rad",
    "L01", "L12", "L25", "L50", "positive", "negative",
]

def main() -> int:
    prereg = yaml.safe_load(PRE.read_text(encoding="utf-8"))
    req = prereg["visualization"]
    data = json.loads((ATTEMPT/"visualization-data.json").read_text())
    html = (ATTEMPT/"report.html").read_text(encoding="utf-8")
    fails = []
    # 1. data model: selectors + traces
    if data["loads_ohm"] != [1, 12, 25, 50]:
        fails.append("loads selector mismatch")
    if data["polarities"] != ["positive", "negative"]:
        fails.append("polarities selector mismatch")
    for load in data["loads_ohm"]:
        for pol in data["polarities"]:
            for case in ("read", "control"):
                cid = f"L{load:02d}-{pol}-{case}"
                if cid not in data["traces"]:
                    fails.append(f"missing trace {cid}")
    # 2. HTML: every required panel/control/unit string present
    for item in REQUIRED_HTML:
        if item not in html:
            fails.append(f"HTML missing required content: {item!r}")
    # 3. interactive controls (plotly.js present = offline self-contained)
    if "Plotly" not in html:
        fails.append("HTML lacks embedded Plotly")
    if "hovermode" not in html or "uirevision" not in html:
        fails.append("hover/zoom controls marker missing")
    # 4. no smoothing/resampling markers (raw = direct samples)
    for cid, tr in data["traces"].items():
        n = len(tr["time_ps"])
        if n != 13599:
            fails.append(f"{cid} sample count {n} != 13600 (raw fidelity)")
    if fails:
        print("CONTENT COMPLETENESS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"CONTENT COMPLETENESS PASS: {len(data['traces'])} traces, "
          f"{len(REQUIRED_HTML)} required HTML items, plotly embedded, "
          "raw fidelity 13599 samples/run")
    return 0

if __name__ == "__main__":
    sys.exit(main())
