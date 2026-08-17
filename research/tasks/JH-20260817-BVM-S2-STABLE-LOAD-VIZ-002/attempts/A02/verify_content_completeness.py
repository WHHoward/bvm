#!/usr/bin/env python3
"""verify_content_completeness.py -- VIZ-002 A02 independent verifier.

Independently reads frozen requirements (preregistration), the actual
visualization-data.json, and the actual report.html bytes.  Does NOT
import the renderer and does NOT trust renderer self-reports.  Verifies
REAL data fields and panel coverage, including AC2 items: corrected V/I,
source descriptors, control residual, endpoint Rhat/Vth/emax/eligibility/
classification, readiness p2p/threshold/READY values.
"""
import json, pathlib, sys, yaml

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
PRE = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/design/preregistration.yaml"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]

def main() -> int:
    prereg = yaml.safe_load(PRE.read_text(encoding="utf-8"))
    req = prereg["visualization"]
    data = json.loads((ATTEMPT/"visualization-data.json").read_text())
    html = (ATTEMPT/"report.html").read_text(encoding="utf-8")
    fails = []
    # --- data model: selector + trace coverage ---
    if data["loads_ohm"] != LOADS or data["polarities"] != POLS:
        fails.append("selector matrix mismatch")
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            if key not in data["corrected"]:
                fails.append(f"missing corrected V/I for {key}")
            else:
                c = data["corrected"][key]
                for field in ("time_ps", "v_star_V", "i_star_A"):
                    if field not in c or not c[field]:
                        fails.append(f"corrected[{key}] missing {field}")
            if key not in data["control_residual"]:
                fails.append(f"missing control residual for {key}")
            else:
                r = data["control_residual"][key]
                for field in ("v_control_resid_V", "i_control_resid_A"):
                    if field not in r or not r[field]:
                        fails.append(f"control_residual[{key}] missing {field}")
            if key not in data["descriptors"]:
                fails.append(f"missing descriptors for {key}")
            else:
                d = data["descriptors"][key]
                if "v_star" not in d or "i_star" not in d or "rctrl" not in d:
                    fails.append(f"descriptors[{key}] incomplete")
                for field in ("max_V", "rms_V", "time_normalized_l1_V"):
                    if field not in d["v_star"]:
                        fails.append(f"descriptors[{key}].v_star missing {field}")
            if key not in data["readiness"]["strata"]:
                fails.append(f"missing readiness for {key}")
            else:
                rd = data["readiness"]["strata"][key]
                for case in ("read", "control"):
                    for f in ("p2p_jm1_rad", "p2p_jm2_rad"):
                        if case not in rd[f]:
                            fails.append(f"readiness[{key}].{f} missing {case}")
                if "ready" not in rd:
                    fails.append(f"readiness[{key}] missing ready flag")
            ep = data["endpoint_detail"].get(key)
            if ep is None:
                fails.append(f"missing endpoint detail for {key}")
            else:
                s = ep["summaries"]
                for field in ("eligible", "compatible", "not_supported", "ill_conditioned"):
                    if field not in s:
                        fails.append(f"endpoint[{key}] summaries missing {field}")
                for tok in ep.get("per_token", []):
                    for field in ("token_ps", "rhat_ohm", "vth_V", "e_max_V", "compatible"):
                        if field not in tok:
                            fails.append(f"endpoint[{key}] token missing {field}")
    # --- HTML panel coverage ---
    required_html = ["WL", "BL", "SE", "JM1", "JM2", "JS1", "JS2",
                     "V(SL1)", "I(L_SL)", "read", "control", "corrected",
                     "V_star", "I_star", "control residual", "Rhat", "emax",
                     "p2p (rad)", "threshold", "0.020", "disposition",
                     "Claim ceiling", "time (ps)", "mV", "uA", "raw rad",
                     "L01", "L12", "L25", "L50", "positive", "negative"]
    for item in required_html:
        if item not in html:
            fails.append(f"HTML missing required content: {item!r}")
    if "Plotly" not in html:
        fails.append("HTML lacks embedded Plotly")
    if fails:
        print("CONTENT COMPLETENESS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    n_ep = sum(len(data["endpoint_detail"].get(f"L{l:02d}-{p}", {}).get("per_token", []))
               for l in LOADS for p in POLS)
    print(f"CONTENT COMPLETENESS PASS: {len(data['corrected'])} corrected V/I, "
          f"{len(data['descriptors'])} descriptor sets, "
          f"{len(data['control_residual'])} control residuals, "
          f"{n_ep} endpoint tokens, readiness values for all 8 strata, "
          f"{len(required_html)} required HTML items")
    return 0

if __name__ == "__main__":
    sys.exit(main())
