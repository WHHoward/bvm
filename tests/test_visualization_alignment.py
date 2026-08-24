#!/usr/bin/env python3
"""Regression tests for PROJECT_VISUALIZATION_INDEX_ALIGNMENT_V2.

These tests use tiny temporary manifests and never invoke JoSIM.  They encode
the failure modes that previously allowed a plausible-looking index to point
at the wrong evidence.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_visualization_alignment", ROOT / "scripts/verify_visualization_alignment.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AlignmentRegression(unittest.TestCase):
    def base(self, *, plot_role="RESULT", plot_source="CURRENT_RESULT", plot_path="plot.html",
             phase="continuous_absolute", claim="generic_exploration", cases=("case",),
             topology_id="topo", signature="sig", publication=None, semantic="PASS", geometric="PASS"):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "raw").mkdir()
        for case in cases:
            raw_path = root / "raw" / f"{case}.csv"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("time,P(J)\n0,0\n", encoding="utf-8")
        (root / "report.md").write_text("report\n", encoding="utf-8")
        (root / plot_path).parent.mkdir(parents=True, exist_ok=True)
        (root / plot_path).write_text("<html></html>", encoding="utf-8")
        topo = {
            "topology_id": topology_id, "topology_signature": signature,
            "representative_experiment": "exp", "shared_by_experiments": ["exp"],
            "publication_schematic": publication,
            "annotated_schematic": None, "connectivity_debug": None,
            "semantic_validation": "semantic.json" if publication else None,
            "geometric_validation": "geometric.json" if publication else None,
        }
        if publication:
            (root / publication).write_text("<svg></svg>", encoding="utf-8")
            (root / "semantic.json").write_text(json.dumps({"status": semantic}), encoding="utf-8")
            (root / "geometric.json").write_text(json.dumps({"status": geometric}), encoding="utf-8")
        entry = {
            "experiment_id": "exp", "scientific_question": "q", "formal_result": "r",
            "required_cases": [{"id": c, "raw": f"raw/{c}.csv", "role": "RESULT"} for c in cases],
            "required_signals": ["P(J)"], "report": "report.md", "current_status": "ALIGNED",
            "claim_type": claim, "topology_id": topology_id, "topology_signature": signature,
            "plots": [{"path": plot_path, "role": plot_role, "cases": list(cases),
                        "source_classification": plot_source, "phase_semantics": phase}],
        }
        manifest = {"experiments": [entry], "parent_head": "test"}
        return tmp, root, manifest, {"topologies": [topo]}

    def fails(self, manifest, root, topology):
        result = MODULE.validate_manifest(manifest, root=root, topology_manifest=topology)
        self.assertEqual(result["overall"], "FAIL")
        return result

    def test_01_scaled_core_cannot_use_paper_reference(self):
        t, root, m, topo = self.base(plot_source="PAPER_REFERENCE")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_02_exactly_one_cannot_use_no_event_reference(self):
        t, root, m, topo = self.base(plot_source="PAPER_REFERENCE")
        m["experiments"][0]["formal_result"] = "EXACTLY_ONE"
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_03_source_only_is_not_receiver_result(self):
        t, root, m, topo = self.base(plot_role="SOURCE_REFERENCE")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_04_bias_comparison_requires_both_points(self):
        t, root, m, topo = self.base(claim="bias_comparison", cases=("37p5u/case",))
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_05_factorial_requires_all_four_points(self):
        t, root, m, topo = self.base(claim="factorial_point", cases=("Q5",))
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_06_load_matrix_requires_accepted_10ohm(self):
        t, root, m, topo = self.base(claim="load_matrix", cases=("Q0 OPEN", "Q0 JTL-only", "Q0 10Ω || JTL"))
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_07_polarity_requires_reverse_and_positive_control(self):
        t, root, m, topo = self.base(claim="polarity_convergence", cases=("r11", "pulse5-original"))
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_08_r13_requires_all_transformations(self):
        t, root, m, topo = self.base(claim="conditioning_matrix", cases=("raw-replay", "c1-rectify"))
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_09_phase_plot_requires_semantics(self):
        t, root, m, topo = self.base(plot_path="phase-comparison.html", phase=None)
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_10_graphviz_cannot_be_publication_schematic(self):
        t, root, m, topo = self.base(publication="topology.svg")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_11_q0_open_wrong_10ohm_topology_not_shared(self):
        t, root, m, topo = self.base(topology_id="q0-10ohm")
        topo["topologies"][0]["shared_by_experiments"] = []
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_12_direct_jtl_wrong_standalone_topology_not_shared(self):
        t, root, m, topo = self.base(topology_id="standalone")
        topo["topologies"][0]["shared_by_experiments"] = []
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_13_parallel_jtl_wrong_series_topology_not_shared(self):
        t, root, m, topo = self.base(topology_id="series-r")
        topo["topologies"][0]["shared_by_experiments"] = []
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_14_ideal_replay_signature_mismatch(self):
        t, root, m, topo = self.base(signature="ideal", topology_id="physical")
        topo["topologies"][0]["topology_signature"] = "physical"
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_15_scaled_jtl_signature_mismatch(self):
        t, root, m, topo = self.base(signature="scaled-jtl", topology_id="standard-jtl")
        topo["topologies"][0]["topology_signature"] = "standard-jtl"
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_16_q6_coupled_cannot_share_q5_standalone(self):
        t, root, m, topo = self.base(signature="q6-coupled", topology_id="q5-standalone")
        topo["topologies"][0]["topology_signature"] = "q5-standalone"
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_17_semantic_validation_must_pass(self):
        t, root, m, topo = self.base(publication="schematic.svg", semantic="FAIL")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_18_geometric_validation_must_pass(self):
        t, root, m, topo = self.base(publication="schematic.svg", geometric="FAIL")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_19_debug_graph_not_publication(self):
        t, root, m, topo = self.base(publication="connectivity-debug.svg")
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_20_two_topologies_cannot_share_mismatched_signature(self):
        t, root, m, topo = self.base(signature="signature-a")
        topo["topologies"][0]["topology_signature"] = "signature-b"
        try: self.fails(m, root, topo)
        finally: t.cleanup()

    def test_21_current_repository_manifest_passes(self):
        manifest_path = ROOT / "docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml"
        topology_path = ROOT / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml"
        manifest = MODULE.yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        topology = MODULE.yaml.safe_load(topology_path.read_text(encoding="utf-8"))
        result = MODULE.validate_manifest(manifest, root=ROOT, topology_manifest=topology)
        self.assertEqual(result["overall"], "PASS")


if __name__ == "__main__":
    unittest.main()
