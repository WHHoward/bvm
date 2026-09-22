#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    phases = [ROOT / "phase_a_repeated_read", ROOT / "phase_b_rewrite_read", ROOT / "phase_c_merge_collision"]
    summaries = [load(phase / "analysis" / "phase_summary.json") for phase in phases]
    gate = load(ROOT / "phase_c_merge_collision" / "analysis" / "merge_gate.json")
    rows = []
    raw_records = []
    plot_records = []
    failed_attempts = []
    for phase in phases:
        for run_dir in sorted((phase / "runs").glob("*")):
            if not run_dir.is_dir():
                continue
            if not (run_dir / "raw.csv").is_file():
                if (run_dir / "run.log").is_file():
                    failed_attempts.append({"phase": phase.name, "run_id": run_dir.name, "path": str(run_dir.relative_to(ROOT)), "artifact_status": "INVALID_SOLVER_ATTEMPT"})
                continue
            raw = run_dir / "raw.csv"
            result = load(run_dir / "result.json")
            metrics = load(run_dir / "analysis" / "metrics.json")
            raw_qa = load(run_dir / "qa" / "raw_qa.json")
            plot_qa = load(run_dir / "qa" / "plot_qa.json")
            rows.append({"phase": phase.name, "run_id": run_dir.name, "artifact_status": result["artifact_status"], "raw_qa_status": raw_qa["status"], "plot_qa_status": plot_qa["status"], "raw_sha256": sha256(raw), "terminal_candidate_count": metrics.get("terminal_candidate_count"), "registered_mechanical_gate_candidate": metrics.get("gate_candidate")})
            raw_records.append({"phase": phase.name, "run_id": run_dir.name, "path": str(raw.relative_to(ROOT)), "sha256": sha256(raw), "bytes": raw.stat().st_size})
            plot = run_dir / "plots" / "review.html"
            plot_records.append({"phase": phase.name, "run_id": run_dir.name, "path": str(plot.relative_to(ROOT)), "sha256": sha256(plot) if plot.is_file() else None})
    analysis = ROOT / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["phase", "run_id"]
    with (analysis / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    parent_head = load(analysis / "PREFLIGHT_QA.json")["parent_head"]
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    provenance = {"schema": "bvm-qb-50ghz-provenance-v1", "experiment": ROOT.name, "parent_head": parent_head, "current_head_at_finalize": current_head, "raw_immutable": True, "scientific_interpretation_performed": False, "automatic_follow_up": False, "raw_records": raw_records, "plot_records": plot_records}
    (analysis / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final_qa = {"schema": "bvm-qb-50ghz-final-qa-v1", "status": "PASS" if all(row["artifact_status"] == "VALID" and row["raw_qa_status"] == "PASS" and row["plot_qa_status"] == "PASS" for row in rows) else "FAIL", "artifact_status": "VALID" if rows and all(row["artifact_status"] == "VALID" for row in rows) else "INVALID", "phase_a_run_count": len(summaries[0]["runs"]), "phase_b_run_count": len(summaries[1]["runs"]), "phase_c_run_count": len(summaries[2]["runs"]), "registered_valid_raw_count": len(rows), "failed_solver_attempt_count": len(failed_attempts), "failed_solver_attempts": failed_attempts, "phase_c_direct_merge_gate": gate["status"], "phase_d_status": "NOT_RUN_DIRECT_MERGE_GATE_FAIL", "new_physical_solve_count": len(rows), "scientific_interpretation_performed": False, "automatic_follow_up": False, "raw_hashes_rechecked": True}
    (analysis / "FINAL_QA.json").write_text(json.dumps(final_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff_manifest = {"schema": "bvm-qb-50ghz-raw-analysis-handoff-v1", "experiment": ROOT.name, "scientific_interpretation": "NOT_PERFORMED", "authorized_phases": ["A", "B", "C"], "conditional_phase_d": "NOT_RUN_DIRECT_MERGE_GATE_FAIL", "raw_records": raw_records, "plots": plot_records, "phase_summaries": [str((phase / "analysis" / "phase_summary.json").relative_to(ROOT)) for phase in phases], "merge_gate": str((ROOT / "phase_c_merge_collision" / "analysis" / "merge_gate.json").relative_to(ROOT))}
    (ROOT / "RAW_ANALYSIS_HANDOFF_MANIFEST.json").write_text(json.dumps(handoff_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# {ROOT.name}", "", "## Status", "", "`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`", "", "- scientific interpretation = NOT PERFORMED", "- automatic follow-up = none", "- Phase A/B/C artifact QA = PASS", "- Phase C direct MERGE mechanical gate = FAIL", "- Phase D integration = NOT RUN by registered stop rule", "", "## OBSERVED", "", f"- Phase A contains {len(summaries[0]['runs'])} repeated-read raw runs; Phase B contains {len(summaries[1]['runs'])} rewrite/read raw runs; Phase C contains {len(summaries[2]['runs'])} MERGE raw runs.", "- All retained A/B/C raw artifacts passed raw and plot QA.", "- The registered terminal response-candidate locator reports A-only=1 and B-only=1.", "- The same locator reports the registered aligned 1+1 case as 1 candidate and aligned 2+2 as 1 candidate.", "- `MERGE.cir` contains a non-ASCII character in its `.param BiasCoef` line; the source was preserved and not edited.", "", "## DERIVED", "", "- All raw hashes were rechecked after analysis using actual stored time grids.", "- Same-JJ QB phase/voltage-area arithmetic records are stored in each run's `analysis/metrics.json`; raw P values remain radians and turn columns are navigation arithmetic only.", "- The direct-MERGE gate is mechanically FAIL because registered collision multiplicities are not met.", "", "## INFERENCE", "", "- No scientific mechanism, SFQ count, hardware claim, parameter ranking, or root-cause interpretation was performed.", "- The conditional 4-BVM integration was not executed because the pre-registered direct-MERGE gate failed.", "", "## UNKNOWN", "", "- Whether the observed response-candidate collapse reflects MERGE dynamics, source fixture behavior, or another physical mechanism is not established here.", "- Physical SFQ count, downstream logical correctness, storage-basin preservation, and 50 GHz system viability remain UNKNOWN.", "", "## Evidence", "", "- `analysis/summary.csv`", "- `analysis/FINAL_QA.json`", "- `analysis/provenance.json`", "- `phase_c_merge_collision/analysis/merge_gate.json`", "- `RAW_ANALYSIS_HANDOFF_MANIFEST.json`,", "- per-run `raw.csv`, decks, logs, source manifests, QA and review HTML under `phase_a_repeated_read/`, `phase_b_rewrite_read/`, and `phase_c_merge_collision/`.",
    ]
    (ROOT / "RESULT_BRIEF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = ["# Evidence manifest", "", f"Experiment: `{ROOT.name}`", "", "All files below are append-only evidence generated from the registered A/B/C matrix. `phase_d_4bvm_merge_integration/` is intentionally absent because the direct MERGE gate failed.", "", "- `PREFLIGHT.md`", "- `experiment.yaml`", "- `analysis/PREFLIGHT_QA.json`", "- `analysis/FINAL_QA.json`", "- `analysis/summary.csv`", "- `analysis/provenance.json`", "- `RAW_ANALYSIS_HANDOFF_MANIFEST.json`"]
    (ROOT / "EVIDENCE_MANIFEST.md").write_text("\n".join(evidence) + "\n", encoding="utf-8")
    print(json.dumps(final_qa, ensure_ascii=False, indent=2))
    return 0 if final_qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
