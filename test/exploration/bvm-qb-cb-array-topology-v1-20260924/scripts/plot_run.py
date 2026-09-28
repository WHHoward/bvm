#!/usr/bin/env python3
"""Build the selected-mode plot plan or render a real raw with classic josim-plot2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from topology import T1_CORE_INDUCTORS, T1_CORE_JUNCTIONS

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
    profile = str(probes.get("profile", topology.get("probe_profile", "debug")))
    output_mode = str(topology.get("output_mode", "TERMINAL"))
    if output_mode not in {"TERMINAL", "T1"}:
        raise RuntimeError(f"unsupported output mode in topology manifest: {output_mode!r}")
    page_defs = PAGES + (("06_t1.html", "t1"),) if output_mode == "T1" else PAGES
    signal_labels = {str(item["label"]) for item in signals}
    by_group: dict[str, list[str]] = {}
    for item in signals:
        by_group.setdefault(str(item["group"]), []).append(str(item["label"]))
    overview: list[str] = []
    if output_mode == "T1":
        # Receiver-integrated overview is a compact propagation view. Keep the
        # four WL drives, BVM outputs, merge boundaries, and T1 outputs; detailed
        # BL/SE and receiver internals remain available in raw or focused pages.
        for index in range(1, int(topology["array_size"]) + 1):
            overview.append(f"I(I_WL{index})")
        for level in topology["levels"]:
            overview.append(f"V({level['bvm_output_node']})")
        for level in topology["levels"]:
            overview.append(f"V({level['merge_node']})")
        overview.extend(("V(FINAL_OUT)", "V(S)", "V(C)"))
        receiver = topology.get("receiver", {})
        if receiver.get("clock_mode") != "QUIET":
            overview.append("V(CLK)")
    else:
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
    instance_records = {
        str(item["instance"]).casefold(): item for item in topology.get("instances", [])
    }

    def require_probe(label: str, context: str) -> str:
        if label not in signal_labels:
            raise RuntimeError(f"{context} requires probe absent from manifest: {label}")
        return label

    # Probe groups are acquisition/storage ownership, not plot membership:
    # labels are globally deduplicated when the probe manifest is built.
    internal_junction_quantities = ("P", "V", "I") if profile == "debug" else ("P", "V")
    internal_inductor_quantities = ("I", "V") if profile == "debug" else ("I",)
    qb: list[str] = []
    for level in topology["levels"]:
        input_node = str(level["bvm_output_node"])
        output_node = str(
            (level.get("qb_raw_node") or level["merge_node"])
            if level.get("qb_side_cb") else level["merge_node"]
        )
        candidates = [
            item for item in topology.get("instances", [])
            if str(item.get("subcircuit", "")).casefold() in {"bq", "qb"}
            and len(item.get("pins", [])) == 2
            and str(item["pins"][0]).casefold() == input_node.casefold()
            and str(item["pins"][1]).casefold() == output_node.casefold()
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                f"cannot uniquely map QB pins {input_node}->{output_node} from topology instances"
            )
        instance = str(candidates[0]["instance"])
        for element in ("BJ1", "BJ2", "BJ3"):
            for quantity in internal_junction_quantities:
                qb.append(require_probe(
                    f"{quantity}({element}|{instance})", f"QB {instance} internal state"
                ))
        for element in ("LIN", "L1", "L2", "L3"):
            for quantity in internal_inductor_quantities:
                qb.append(require_probe(
                    f"{quantity}({element}|{instance})", f"QB {instance} branch state"
                ))
        # Keep CORE's historical optional-boundary behavior. DEBUG promises a
        # complete diagnostic set, so every boundary must be present there.
        for node in (input_node, output_node):
            label = f"V({node})"
            if profile == "debug":
                qb.append(require_probe(label, f"QB {instance} boundary"))
            elif label in signal_labels:
                qb.append(label)

    cb: list[str] = []
    cb_roles: list[dict[str, str]] = []
    role_by_instance = {
        str(instance).casefold(): str(role)
        for instance, role in probes.get("component_roles", {}).items()
    }
    seen_cb_instances: set[str] = set()
    for level in topology["levels"]:
        for field in ("qb_side_cb", "post_sjtl_cb"):
            instance_value = level.get(field)
            if not instance_value:
                continue
            instance = str(instance_value)
            folded = instance.casefold()
            if folded in seen_cb_instances:
                continue
            seen_cb_instances.add(folded)
            record = instance_records.get(folded)
            if (record is None or str(record.get("subcircuit", "")).casefold() != "cb"
                    or len(record.get("pins", [])) != 2):
                raise RuntimeError(f"topology does not define two-pin CB instance {instance}")
            role = role_by_instance.get(folded, f"CB instance {instance}")
            cb_roles.append({"instance": instance, "role": role})
            for element in ("BJ1", "BJ2"):
                for quantity in internal_junction_quantities:
                    cb.append(require_probe(
                        f"{quantity}({element}|{instance})", f"CB {instance} internal state"
                    ))
            cb_inductors = ("L1", "L2", "L3", "L4") if profile == "debug" else ("L1", "L4")
            for element in cb_inductors:
                for quantity in internal_inductor_quantities:
                    cb.append(require_probe(
                        f"{quantity}({element}|{instance})", f"CB {instance} branch state"
                    ))
            for pin in record["pins"]:
                cb.append(require_probe(f"V({pin})", f"CB {instance} boundary"))

    t1: list[str] = []
    if output_mode == "T1":
        receiver = topology.get("receiver")
        t1_instance = instance_records.get("xt1")
        if (not isinstance(receiver, dict) or t1_instance is None
                or str(t1_instance.get("subcircuit", "")).casefold() != "t1"):
            raise RuntimeError("T1 plot page requires a topology-backed XT1 receiver")
        if profile == "debug":
            for node in ("FINAL_OUT", str(receiver["input_node"]), "CLK", "S", "C"):
                t1.append(require_probe(f"V({node})", f"T1 {node} boundary"))
            for element in ("R_S", "R_C"):
                t1.append(require_probe(f"I({element})", f"T1 {element} output load"))
            receiver_junctions = list(receiver["junction_elements"])
            receiver_inductors = list(receiver["inductor_elements"])
            for element in receiver_junctions:
                for quantity in ("P", "V", "I"):
                    t1.append(require_probe(
                        f"{quantity}({element}|XT1)", f"T1 XT1 junction {element}"
                    ))
            for element in receiver_inductors:
                for quantity in ("I", "V"):
                    t1.append(require_probe(
                        f"{quantity}({element}|XT1)", f"T1 XT1 inductor {element}"
                    ))
        else:
            for node in ("FINAL_OUT", "S", "C"):
                t1.append(require_probe(f"V({node})", f"T1 {node} boundary"))
            for element in T1_CORE_JUNCTIONS:
                t1.append(require_probe(f"P({element}|XT1)", f"T1 XT1 junction phase {element}"))
            for element in ("L3", "L11", "L14", "L17"):
                t1.append(require_probe(f"I({element}|XT1)", f"T1 XT1 branch current {element}"))

    acc_gap: list[str] = []
    instance_pins = {
        str(item["instance"]).casefold(): [str(pin) for pin in item["pins"]]
        for item in topology.get("instances", [])
    }
    for level in topology["levels"]:
        for field in ("local_output", "upstream_output"):
            output = level.get(field, {})
            if output.get("signal"):
                acc_gap.append(str(output["signal"]))
        merge_label = f"V({level['merge_node']})"
        carry_label = f"V({level['carry_node']})"
        if merge_label in signal_labels:
            acc_gap.append(merge_label)
        for instance in level.get("sjtl_instances", []):
            for quantity in ("P", "V"):
                label = f"{quantity}(BJ1|{instance})"
                if label in signal_labels:
                    acc_gap.append(label)
            pins = instance_pins.get(str(instance).casefold(), [])
            if len(pins) == 2:
                output_label = f"V({pins[1]})"
                if output_label in signal_labels:
                    acc_gap.append(output_label)
        post_cb = level.get("post_sjtl_cb")
        if post_cb:
            for quantity in ("P", "V"):
                label = f"{quantity}(BJ2|{post_cb})"
                if label in signal_labels:
                    acc_gap.append(label)
            pins = instance_pins.get(str(post_cb).casefold(), [])
            if len(pins) == 2:
                output_label = f"V({pins[1]})"
                if output_label in signal_labels:
                    acc_gap.append(output_label)
        if carry_label in signal_labels:
            acc_gap.append(carry_label)
    acc_gap.append("V(FINAL_OUT)")

    selected = {
        "overview": _unique(overview),
        "bvm": _unique(bvm),
        "qb": _unique(qb),
        "cb": _unique(cb),
        "acc_gap": _unique(acc_gap),
    }
    if output_mode == "T1":
        selected["t1"] = _unique(t1)
    for page, labels in selected.items():
        missing = sorted(set(labels) - signal_labels)
        if missing:
            raise RuntimeError(f"{page} plot plan references probes absent from manifest: {missing}")
    pages = []
    for filename, key in page_defs:
        if key == "overview":
            title = "System overview — stimulus, boundaries, merge/carry, FINAL_OUT"
        elif key == "bvm":
            title = f"BVM array — {topology['array_size']} levels"
        elif key == "qb":
            title = f"QB chain — {topology['array_size']} levels"
        elif key == "cb":
            title = ("CB components — " + "; ".join(item["role"] for item in cb_roles)
                     if cb_roles else "No CB components in this topology")
        elif key == "t1":
            title = "T1 receiver — FINAL_OUT, selected phases/branches, S/C outputs"
        else:
            title = "Per-level local/upstream contribution, MERGE, sJTL, post-CB, CARRY, FINAL_OUT"
        pages.append({
            "file": filename,
            "page": key,
            "title": title,
            "component_roles": cb_roles if key == "cb" else [],
            "signals": selected[key],
            "trace_count": len(selected[key]),
            "status": "NO_COMPONENT_PRESENT" if key == "cb" and not selected[key] else "PLANNED",
            "time_range": "FULL_STORED_TIME_RANGE",
        })
    return {
        "schema": "bvm-qb-cb-array-plot-manifest-v1",
        "render_status": topology.get("render_status", "STATIC_RENDER"),
        "run_id": topology.get("run_id"),
        "mask": topology["mask"],
        "probe_profile": profile,
        "plotter": str(PLOTTER.relative_to(REPO)),
        "plotter_sha256": sha256(PLOTTER) if PLOTTER.is_file() else None,
        "shared_plotly_asset": str(ASSET.relative_to(REPO)),
        "shared_plotly_asset_sha256": sha256(ASSET) if ASSET.is_file() else None,
        "layout": "josim-plot2.py sep_comb dark",
        "phase_display": "turns (rad/2pi); raw phase remains radians",
        "raw_sha256": raw_sha256,
        "pages": pages,
        "scientific_interpretation_performed": False,
        **({"output_mode": "T1"} if output_mode == "T1" else {}),
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
                            "status": "NO_COMPONENT_PRESENT", "trace_count": 0})
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
                        "status": "PASS", "trace_count": len(labels)})
    after = sha256(raw)
    qa = {
        "schema": "bvm-qb-cb-array-plot-qa-v1",
        "status": "PASS" if raw_before == after and len(outputs) == len(plan["pages"])
        and shared_asset_reference_pass else "FAIL",
        "raw_sha256_before": raw_before, "raw_sha256_after": after,
        "raw_immutable": raw_before == after,
        "page_count": len(outputs), "pages": outputs,
        "plotly_asset_sha256": sha256(ASSET),
        "plotter_path": str(PLOTTER.relative_to(REPO)),
        "plotter_sha256": sha256(PLOTTER),
        "probe_profile": plan["probe_profile"],
        "shared_asset_reference_pass": shared_asset_reference_pass,
        "full_stored_time_range": True,
        "scientific_interpretation_performed": False,
    }
    if plan.get("output_mode") == "T1":
        qa["output_mode"] = "T1"
    (root / "analysis" / "plot_manifest.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "analysis" / "plot_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result_path = root / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["plot_qa"] = qa
        link_metric = result.get("mechanical_metrics", {}).get("t1_link_consistency", {})
        t1_mechanical_pass = (
            plan.get("output_mode") != "T1"
            or link_metric.get("status") == "MEASURED_REPORT_ONLY"
        )
        result["status"] = (
            "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
            if result.get("artifact_status") == "VALID" and qa["status"] == "PASS"
            and t1_mechanical_pass
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
    try:
        from try_case import refresh_batch_for_run
        refresh_batch_for_run(root)
    except (OSError, ValueError, RuntimeError) as exc:
        raise RuntimeError(f"plot QA completed but batch revalidation failed: {exc}") from exc
    return qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render classic JoSIM pages for the selected output mode")
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
