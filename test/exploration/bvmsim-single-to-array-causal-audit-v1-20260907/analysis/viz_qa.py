#!/usr/bin/env python3
"""Independent mechanical QA for the task-local comparison pages."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "plots/plot_manifest.json"
OUTPUT = EXP / "analysis/viz_qa.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing plot manifest: {MANIFEST}")
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite viz QA: {OUTPUT}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []
    failures: list[str] = []
    for page in manifest.get("pages", []):
        data_path = REPO / page["data"]
        html_path = REPO / page["html"]
        page_failures: list[str] = []
        try:
            trace = read_csv(data_path)
            labels = list(trace.headers[1:])
            if trace.duplicate_columns:
                page_failures.append("duplicate derived data labels")
            if labels != page["labels"]:
                page_failures.append("manifest labels differ from derived CSV")
            if sha256(data_path) != page["data_sha256"]:
                page_failures.append("derived data hash changed")
        except Exception as exc:  # noqa: BLE001 - report artifact failure verbatim
            page_failures.append(f"data read failure: {exc}")
            labels = []
        if not html_path.is_file() or html_path.stat().st_size == 0:
            page_failures.append("missing/empty HTML")
            html = ""
        else:
            html = html_path.read_text(encoding="utf-8")
            if sha256(html_path) != page["html_sha256"]:
                page_failures.append("HTML hash changed")
            if any(label not in html for label in labels):
                page_failures.append("plotted label missing from HTML")
            lowered = html.casefold()
            axis_text = lowered.replace("\\u002f", "/")
            if '\"title\":{\"text\":\"unknown\"' in lowered:
                page_failures.append("Unknown axis/value marker present")
            if any(label.startswith("P") for label in labels) and "phase (turns) [rad/2pi]" not in axis_text:
                page_failures.append("phase axis is not labelled in turns")
            if any("sfq" in label.casefold() for label in labels):
                page_failures.append("SFQ appears in a plot label")
        for name, expected_hash in manifest["source_raw_hashes_at_render"].items():
            source_record = json.loads((EXP / "source/source_manifest.json").read_text(encoding="utf-8"))["files"][name]
            source_path = REPO / source_record["path"]
            if sha256(source_path) != expected_hash or sha256(source_path) != source_record["sha256"]:
                page_failures.append(f"source raw hash changed: {name}")
        checks.append({"page": page["name"], "status": "PASS" if not page_failures else "FAIL", "failures": page_failures})
        failures.extend(f"{page['name']}: {failure}" for failure in page_failures)
    result = {
        "schema": "bvmsim-single-to-array-causal-audit-viz-qa-v1",
        "created_at_local": now_local(),
        "manifest": rel(MANIFEST),
        "page_count": len(checks),
        "all_pages_present_and_valid": not failures,
        "raw_hashes_unchanged": not any("source raw hash changed" in failure for failure in failures),
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "page_count": len(checks), "failure_count": len(failures)}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
