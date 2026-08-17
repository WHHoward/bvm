#!/usr/bin/env python3
"""salvage_analyze.py -- SALVAGE-001 A03 independent recomputation + COMPLETE
computed source provenance.

Reads ONLY frozen TIMING-001 sources (raw CSVs, inputs incl.
generate_inputs.py/matrix.txt, manifest, closure-hashes, stdout/stderr,
frozen preregistration, frozen analysis schema).  Does NOT read or import
any prior analysis.json.  Computes (not copies) a repository-safe source
provenance inventory with path + SHA-256 + byte size for EVERY reused
source file, writes schema-valid analysis.json (validated against the
frozen analysis-schema.json), and writes source-provenance.yaml.
"""
import csv
import hashlib
import json
import pathlib
import yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-init-timing-20260817-01"
TASK = REPO / "research/tasks/JH-20260817-BVM-S2-TIMING-001"
PRE = TASK / "design/preregistration.yaml"
SCHEMA = TASK / "design/analysis-schema.json"
WINDOWS_PS = {"settling_early": (Decimal("30"), Decimal("40")),
              "settling_mid": (Decimal("50"), Decimal("60")),
              "settling_late": (Decimal("70"), Decimal("80")),
              "readiness": (Decimal("80"), Decimal("90"))}
THRESHOLD = Decimal("0.020")
CASES = ["A-positive", "B-positive", "A-negative", "B-negative"]


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def entry(rel: pathlib.Path, kind: str) -> dict:
    return {"path": str(rel), "kind": kind,
            "sha256": sha256(REPO / rel), "bytes": (REPO / rel).stat().st_size}


def provenance() -> dict:
    items = []
    # frozen spec
    items.append(entry(PRE.relative_to(REPO), "frozen_preregistration"))
    items.append(entry(SCHEMA.relative_to(REPO), "frozen_analysis_schema"))
    # source manifest + closure hashes
    items.append(entry(RUN.relative_to(REPO) / "manifest.yaml", "source_manifest"))
    items.append(entry(RUN.relative_to(REPO) / "closure-hashes.txt", "closure_hashes"))
    # every source inputs file (including generator and matrix)
    for p in sorted((RUN / "inputs").iterdir()):
        if p.is_file():
            items.append(entry(p.relative_to(REPO), "source_input"))
    # raw CSVs, stdout, stderr per case
    for case in CASES:
        for suffix, kind in (("run-01.csv", "raw_csv"),
                             ("stdout.txt", "stdout"),
                             ("stderr.txt", "stderr")):
            items.append(entry((RUN / "raw" / case / suffix).relative_to(REPO), kind))
    return {"schema_version": "bvm-s2-salvage-provenance-v1",
            "run_id": "bvm-s2-init-timing-20260817-01",
            "attempt": "A03",
            "source_files": items}


def load(path: pathlib.Path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    times = [Decimal(r[0]) for r in rows[1:]]
    cols = {h: [Decimal(r[j]) for r in rows[1:]]
            for j, h in enumerate(hdr[1:], start=1)}
    return times, cols


def p2p(times, vals, lo, hi):
    lo_s, hi_s = lo * Decimal("1e-12"), hi * Decimal("1e-12")
    sel = [v for t, v in zip(times, vals) if lo_s <= t < hi_s]
    if not sel:
        raise ValueError("empty window coverage")
    return max(sel) - min(sel)


def main() -> None:
    runs = []
    for case in CASES:
        times, cols = load(RUN / "raw" / case / "run-01.csv")
        entry_d = {"id": case, "polarity": "positive" if "positive" in case else "negative",
                   "timing": "S2_REGISTERED" if case.startswith("A") else "S1_REGISTERED",
                   "windows": {}, "readiness": {}}
        for wname, (lo, hi) in WINDOWS_PS.items():
            jm1 = p2p(times, cols["P(B_JM1|XBVM1)"], lo, hi)
            jm2 = p2p(times, cols["P(B_JM2|XBVM1)"], lo, hi)
            entry_d["windows"][wname] = {"jm1_p2p_rad": str(jm1),
                                         "jm2_p2p_rad": str(jm2)}
            if wname == "readiness":
                entry_d["readiness"] = {
                    "jm1_ready": jm1 <= THRESHOLD,
                    "jm2_ready": jm2 <= THRESHOLD,
                    "co_primary_ready": jm1 <= THRESHOLD and jm2 <= THRESHOLD}
        runs.append(entry_d)
    contrasts = {}
    for pol in ("positive", "negative"):
        a = next(e for e in runs if e["polarity"] == pol and e["timing"] == "S2_REGISTERED")
        b = next(e for e in runs if e["polarity"] == pol and e["timing"] == "S1_REGISTERED")
        d2 = Decimal(b["windows"]["readiness"]["jm2_p2p_rad"]) - Decimal(a["windows"]["readiness"]["jm2_p2p_rad"])
        d1 = Decimal(b["windows"]["readiness"]["jm1_p2p_rad"]) - Decimal(a["windows"]["readiness"]["jm1_p2p_rad"])
        contrasts[pol] = {
            "delta_jm2_readiness_p2p_rad": str(d2),
            "delta_jm1_readiness_p2p_rad": str(d1),
            "abs_delta_jm2_ge_threshold": abs(d2) >= THRESHOLD,
            "readiness_classification_changed": a["readiness"]["co_primary_ready"] != b["readiness"]["co_primary_ready"]}
    pos, neg = contrasts["positive"], contrasts["negative"]
    ps = pos["abs_delta_jm2_ge_threshold"] or pos["readiness_classification_changed"]
    ns = neg["abs_delta_jm2_ge_threshold"] or neg["readiness_classification_changed"]
    same = (Decimal(pos["delta_jm2_readiness_p2p_rad"]) * Decimal(neg["delta_jm2_readiness_p2p_rad"])) > 0
    if ps and ns and same:
        disposition = "CONSISTENT_TIMING_SENSITIVITY_SUPPORTED"
    elif ps != ns:
        disposition = "POLARITY_CONTINGENT_TIMING_SENSITIVITY"
    elif not ps and not ns:
        disposition = "NO_REGISTERED_TIMING_SENSITIVITY_OBSERVED"
    else:
        disposition = "INCONCLUSIVE"
    analysis = {
        "schema_version": "bvm-s2-timing-analysis-v1",
        "run_id": "bvm-s2-init-timing-20260817-01",
        "metric_spec": {"readiness_threshold_rad": "0.020",
                        "p2p_window_semantics": "half_open_actual_csv_time",
                        "timestamp": "Decimal_from_literal_CSV_token"},
        "provenance": {"binary": "build/josim-cli", "version": "v2.7.2837d13",
                       "timestep_ps": "0.0125", "tstop_ps": "92.0",
                       "source": "frozen TIMING-001 raw (recomputed, not old analysis.json)",
                       "salvage_attempt": "A03"},
        "windows": {"settling_early": [30.0, 40.0], "settling_mid": [50.0, 60.0],
                    "settling_late": [70.0, 80.0], "readiness": [80.0, 90.0]},
        "runs": runs, "contrasts": contrasts,
        "disposition": disposition, "unknowns": []}
    import jsonschema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(analysis, schema)  # raises on violation
    (ATTEMPT / "analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    (ATTEMPT / "source-provenance.yaml").write_text(
        yaml.safe_dump(provenance(), sort_keys=False), encoding="utf-8")
    # explicit schema-validation evidence
    (ATTEMPT / "schema-validation.json").write_text(json.dumps(
        {"schema": str(SCHEMA.relative_to(REPO)), "valid": True,
         "validator": "jsonschema.Draft202012Validator"}, indent=2), encoding="utf-8")
    print(f"A03 analysis + complete provenance written; disposition={disposition}")


if __name__ == "__main__":
    main()
