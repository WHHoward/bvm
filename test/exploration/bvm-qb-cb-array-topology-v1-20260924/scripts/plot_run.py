#!/usr/bin/env python3
"""Build a five-page plot plan or render a real raw with classic josim-plot2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
PLOTTER = REPO / "scripts" / "josim-plot2.py"
ASSET = SERIES / "plots" / "assets" / "plotly.min.js"
PAGES = (
    ("01_overview.html", "overview"),
    ("02_bvm.html", "bvm"),
    ("03_qb.html", "qb"),
    ("04_cb.html", "cb"),
    ("05_acc_gap.html", "acc_gap"),
)


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def build_plot_manifest(topology: dict[str, Any], probes: dict[str, Any],
                        raw_sha256: str | None = None) -> dict[str, object]:
    signals = probes.get("signals", [])
    by_group: dict[str, list[str]] = {}
    for item in signals:
        by_group.setdefault(str(item["group"]), []).append(str(item["label"]))
    overview: list[str] = []
    overview.extend(by_group.get("stimulus", []))
    for level in topology["levels"]:
        for key in ("bvm_output_node", "merge_node", "carry_node"):
            node = level.get(key)
            if node:
                overview.append(f"V({node})")
        qb_node = level.get("qb_raw_node") or level.get("merge_node")
        if qb_node:
            overview.append(f"V({qb_node})")
    overview.append("V(FINAL_OUT)")

    bvm = [label for group, items in by_group.items() if group.startswith("bvm") for label in items]
    qb = [label for group, items in by_group.items() if group.startswith("qb") for label in items]
    cb = [label for group, items in by_group.items() if group.startswith("cb:") for label in items]
    cb_roles = [
        {"instance": str(instance), "role": role}
        for instance, role in probes.get("component_roles", {}).items()
    ]
    acc_gap: list[str] = []
    for level in topology["levels"]:
        for field in ("local_output", "upstream_output", "carry_output"):
            output = level.get(field, {})
            if output.get("signal"):
                acc_gap.append(str(output["signal"]))
        acc_gap.extend((f"V({level['merge_node']})", f"V({level['carry_node']})"))
        for instance in level.get("sjtl_instances", []):
            acc_gap.extend(by_group.get(f"sjtl:{instance}", []))
        for instance in (level.get("qb_side_cb"), level.get("post_sjtl_cb")):
            if instance:
                acc_gap.extend(by_group.get(f"cb:{instance}", []))
    acc_gap.append("V(FINAL_OUT)")

    selected = {
        "overview": _unique(overview),
        "bvm": _unique(bvm),
        "qb": _unique(qb),
        "cb": _unique(cb),
        "acc_gap": _unique(acc_gap),
    }
    pages = []
    for filename, key in PAGES:
        if key == "overview":
            title = "System overview — stimulus, boundaries, merge/carry, FINAL_OUT"
        elif key == "bvm":
            title = f"BVM array — {topology['array_size']} levels"
        elif key == "qb":
            title = f"QB chain — {topology['array_size']} levels"
        elif key == "cb":
            title = ("CB components — " + "; ".join(item["role"] for item in cb_roles)
                     if cb_roles else "No CB components in this topology")
        else:
            title = "Per-level local/upstream contribution, MERGE, sJTL, post-CB, CARRY, FINAL_OUT"
        pages.append({
            "file": filename,
            "page": key,
            "title": title,
            "component_roles": cb_roles if key == "cb" else [],
            "signals": selected[key],
            "status": "NO_COMPONENT_PRESENT" if key == "cb" and not selected[key] else "PLANNED",
            "time_range": "FULL_STORED_TIME_RANGE",
        })
    return {
        "schema": "bvm-qb-cb-array-plot-manifest-v1",
        "render_status": topology.get("render_status", "STATIC_RENDER"),
        "run_id": topology.get("run_id"),
        "mask": topology["mask"],
        "plotter": str(PLOTTER.relative_to(REPO)),
        "layout": "josim-plot2.py sep_comb dark",
        "phase_display": "turns (rad/2pi); raw phase remains radians",
        "raw_sha256": raw_sha256,
        "pages": pages,
        "scientific_interpretation_performed": False,
    }


def plan_only(run_dir: str | Path) -> dict[str, object]:
    root = Path(run_dir)
    topology = json.loads((root / "topology_manifest.json").read_text(encoding="utf-8"))
    probes = json.loads((root / "probe_manifest.json").read_text(encoding="utf-8"))
    manifest = build_plot_manifest(topology, probes)
    target = root / "analysis" / "plot_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return manifest


def _load_plotter() -> Any:
    if not PLOTTER.is_file():
        raise RuntimeError(f"classic plotter is missing: {PLOTTER}")
    spec = importlib.util.spec_from_file_location("josim_plot2_classic", PLOTTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load classic plotter: {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_run(run_dir: str | Path) -> dict[str, object]:
    root = Path(run_dir).resolve()
    raw = root / "raw.csv"
    if not raw.is_file():
        raise RuntimeError(f"raw.csv is required for plot rendering: {raw}")
    raw_before = sha256(raw)
    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.raw import read_csv
    trace = read_csv(raw)
    plan = build_plot_manifest(
        json.loads((root / "topology_manifest.json").read_text(encoding="utf-8")),
        json.loads((root / "probe_manifest.json").read_text(encoding="utf-8")),
        raw_sha256=raw_before,
    )
    for page in plan["pages"]:
        missing = [label for label in page["signals"] if label not in trace.headers]
        duplicate = [label for label in page["signals"] if trace.headers.count(label) > 1]
        if missing or duplicate:
            raise RuntimeError(f"plot signals do not resolve uniquely in raw: missing={missing}, duplicate={duplicate}")

    if not ASSET.is_file():
        raise RuntimeError(f"shared Plotly asset is missing: {ASSET}")
    import pandas as pd
    from types import SimpleNamespace

    frame = pd.read_csv(raw)
    plotter = _load_plotter()
    output_dir = root / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, object]] = []
    external_asset = "../../../plots/assets/plotly.min.js"
    shared_asset_reference_pass = True
    for page in plan["pages"]:
        target = output_dir / page["file"]
        labels = page["signals"]
        if not labels:
            target.write_text(
                "<!doctype html><html><meta charset='utf-8'><title>No CB components</title>"
                "<body><p>No CB component exists in this rendered topology.</p></body></html>\n",
                encoding="utf-8",
            )
            outputs.append({"path": target.relative_to(root).as_posix(), "sha256": sha256(target),
                            "status": "NO_COMPONENT_PRESENT"})
            continue
        args = SimpleNamespace(subset=labels, jump="2pi")
        figure = plotter.seperate_combined_layout(frame, args)
        figure.update_layout(title=f"{root.name} — {page['title']}", title_font_size=24,
                             template="plotly_dark")
        figure.write_html(target, include_plotlyjs=external_asset, full_html=True,
                          auto_open=False)
        if external_asset not in target.read_text(encoding="utf-8"):
            shared_asset_reference_pass = False
        outputs.append({"path": target.relative_to(root).as_posix(), "sha256": sha256(target),
                        "status": "PASS"})
    after = sha256(raw)
    qa = {
        "schema": "bvm-qb-cb-array-plot-qa-v1",
        "status": "PASS" if raw_before == after and len(outputs) == 5
        and shared_asset_reference_pass else "FAIL",
        "raw_sha256_before": raw_before, "raw_sha256_after": after,
        "raw_immutable": raw_before == after,
        "page_count": len(outputs), "pages": outputs,
        "plotly_asset_sha256": sha256(ASSET),
        "shared_asset_reference_pass": shared_asset_reference_pass,
        "full_stored_time_range": True,
        "scientific_interpretation_performed": False,
    }
    (root / "analysis" / "plot_manifest.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "analysis" / "plot_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result_path = root / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["plot_qa"] = qa
        result["status"] = (
            "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
            if result.get("artifact_status") == "VALID" and qa["status"] == "PASS"
            else "MECHANICAL_QA_FAIL_AWAITING_USER_REVIEW"
        )
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        brief_path = root / "RESULT_BRIEF.md"
        if brief_path.is_file():
            lines = brief_path.read_text(encoding="utf-8").splitlines()
            lines = ["- plot QA: `PASS`" if line.startswith("- plot QA:") and qa["status"] == "PASS"
                     else (f"- plot QA: `{qa['status']}`" if line.startswith("- plot QA:") else line)
                     for line in lines]
            brief_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        latest_path = SERIES / "analysis" / "LATEST_RUN.json"
        if latest_path.is_file():
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            if latest.get("run_id") == root.name:
                latest["status"] = result["status"]
                latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")
    return qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render five classic JoSIM plot pages")
    parser.add_argument("run_dir")
    parser.add_argument("--plan-only", action="store_true",
                        help="write signal/page manifest without reading raw or rendering HTML")
    args = parser.parse_args(argv)
    try:
        if args.plan_only:
            plan = plan_only(args.run_dir)
            print(json.dumps({"status": "PLAN_ONLY", "page_count": len(plan["pages"]),
                              "html_created": False, "raw_read": False}, indent=2))
            return 0
        qa = render_run(args.run_dir)
        print(json.dumps(qa, ensure_ascii=False, indent=2))
        return 0 if qa["status"] == "PASS" else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
