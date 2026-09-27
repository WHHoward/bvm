from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))

from config import USER_CASE_KEYS, load_env  # noqa: E402
from plot_run import build_plot_manifest  # noqa: E402
from run_case import render_case  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


A025 = SERIES / "runs" / "A025_T006_M1111"


def read_snapshot(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


class PlotBoundarySelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="qb-cb-plot-boundaries-")
        cls.root = Path(cls.temp.name)
        baseline = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
        baseline.update(read_snapshot(A025 / "USER_CASE.snapshot.env"))
        stimulus = load_stimulus(A025 / "STIMULUS.snapshot.env")
        cls.fixtures = {}
        for profile in ("core", "debug"):
            values = dict(baseline)
            values["PROBE_PROFILE"] = profile
            fixture_dir = cls.root / profile
            result = render_case(values, stimulus, "1111", fixture_dir, fixture_only=True)
            plan = build_plot_manifest(result["topology_manifest"], result["probe_manifest"])
            cls.fixtures[profile] = {
                "topology": result["topology_manifest"],
                "probes": result["probe_manifest"],
                "plan": plan,
            }
        no_cb_values = dict(baseline)
        no_cb_values.update({
            "QB_CB": "0,0,0,0", "SJTL_COUNT": "1,1,1,1",
            "POST_SJTL_CB": "0,0,0,0", "PROBE_PROFILE": "core",
        })
        no_cb_result = render_case(
            no_cb_values, stimulus, "1111", cls.root / "no_qb_side_cb", fixture_only=True
        )
        cls.fixtures["no_qb_side_cb"] = {
            "topology": no_cb_result["topology_manifest"],
            "probes": no_cb_result["probe_manifest"],
            "plan": build_plot_manifest(
                no_cb_result["topology_manifest"], no_cb_result["probe_manifest"]
            ),
        }
        cls.legacy_debug = json.loads((A025 / "probe_manifest.json").read_text(encoding="utf-8"))
        with (A025 / "raw.csv").open("r", encoding="utf-8", newline="") as stream:
            cls.legacy_raw_headers = set(next(csv.reader(stream)))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def page(self, profile: str, name: str) -> dict[str, object]:
        return next(page for page in self.fixtures[profile]["plan"]["pages"]
                    if page["page"] == name)

    @staticmethod
    def instance(topology: dict[str, object], name: str) -> dict[str, object]:
        return next(item for item in topology["instances"] if item["instance"] == name)

    def test_a_qb_page_has_each_internal_state_and_existing_boundaries(self):
        for fixture_name in ("core", "debug", "no_qb_side_cb"):
            fixture = self.fixtures[fixture_name]
            topology = fixture["topology"]
            signals = set(next(page for page in fixture["plan"]["pages"]
                               if page["page"] == "qb")["signals"])
            for level in topology["levels"]:
                input_node = level["bvm_output_node"]
                output_node = (level["qb_raw_node"] if level["qb_side_cb"]
                               else level["merge_node"])
                qb = next(item for item in topology["instances"]
                          if item["subcircuit"] == "BQ"
                          and item["pins"] == [input_node, output_node])
                self.assertIn(f"V({input_node})", signals)
                self.assertIn(f"V({output_node})", signals)
                for element in ("BJ1", "BJ2", "BJ3"):
                    for quantity in ("P", "V"):
                        self.assertIn(f"{quantity}({element}|{qb['instance']})", signals)
                for element in ("LIN", "L1", "L2", "L3"):
                    self.assertIn(f"I({element}|{qb['instance']})", signals)

    def test_b_qb_side_cb_boundaries_are_selected_independent_of_owner_group(self):
        for profile in ("core", "debug"):
            fixture = self.fixtures[profile]
            topology = fixture["topology"]
            probes = fixture["probes"]
            signals = set(self.page(profile, "cb")["signals"])
            instance = topology["levels"][0]["qb_side_cb"]
            pins = self.instance(topology, instance)["pins"]
            labels = [f"V({pin})" for pin in pins]
            for label in labels:
                self.assertIn(label, signals)
            owners = {item["label"]: item["group"] for item in probes["signals"]}
            self.assertFalse(owners[labels[0]].startswith("cb:"), labels[0])

    def test_c_post_sjtl_cb_boundaries_are_selected_from_actual_pins(self):
        for profile in ("core", "debug"):
            fixture = self.fixtures[profile]
            topology = fixture["topology"]
            signals = set(self.page(profile, "cb")["signals"])
            instance = topology["levels"][0]["post_sjtl_cb"]
            pins = self.instance(topology, instance)["pins"]
            for pin in pins:
                self.assertIn(f"V({pin})", signals)

    def test_missing_cb_boundary_probe_hard_stops(self):
        fixture = self.fixtures["core"]
        topology = fixture["topology"]
        probes = json.loads(json.dumps(fixture["probes"]))
        missing = "V(QB1_RAW)"
        probes["signals"] = [item for item in probes["signals"] if item["label"] != missing]
        with self.assertRaisesRegex(
                RuntimeError, r"CB XQBCB1 boundary requires probe absent.*V\(QB1_RAW\)"):
            build_plot_manifest(topology, probes)

    def test_missing_debug_qb_boundary_probe_hard_stops(self):
        fixture = self.fixtures["debug"]
        probes = json.loads(json.dumps(fixture["probes"]))
        missing = "V(BVM1_SL)"
        probes["signals"] = [item for item in probes["signals"] if item["label"] != missing]
        with self.assertRaisesRegex(
                RuntimeError, r"QB XBQ1 boundary requires probe absent.*V\(BVM1_SL\)"):
            build_plot_manifest(fixture["topology"], probes)

    def test_core_qb_page_remains_compact(self):
        fixture = self.fixtures["core"]
        topology = fixture["topology"]
        signals = set(self.page("core", "qb")["signals"])
        for level in topology["levels"]:
            input_node = level["bvm_output_node"]
            output_node = level["qb_raw_node"] if level["qb_side_cb"] else level["merge_node"]
            qb = next(item for item in topology["instances"]
                      if item["subcircuit"] == "BQ"
                      and item["pins"] == [input_node, output_node])
            for element in ("BJ1", "BJ2", "BJ3"):
                self.assertNotIn(f"I({element}|{qb['instance']})", signals)
            for element in ("LIN", "L1", "L2", "L3"):
                self.assertNotIn(f"V({element}|{qb['instance']})", signals)

    def test_debug_qb_page_includes_detailed_internals(self):
        fixture = self.fixtures["debug"]
        topology = fixture["topology"]
        signals = set(self.page("debug", "qb")["signals"])
        for level in topology["levels"]:
            input_node = level["bvm_output_node"]
            output_node = level["qb_raw_node"] if level["qb_side_cb"] else level["merge_node"]
            qb = next(item for item in topology["instances"]
                      if item["subcircuit"] == "BQ"
                      and item["pins"] == [input_node, output_node])
            for element in ("BJ1", "BJ2", "BJ3"):
                for quantity in ("P", "V", "I"):
                    self.assertIn(f"{quantity}({element}|{qb['instance']})", signals)
            for element in ("LIN", "L1", "L2", "L3"):
                for quantity in ("I", "V"):
                    self.assertIn(f"{quantity}({element}|{qb['instance']})", signals)

    def cb_instances(self, fixture: dict[str, object]) -> list[dict[str, object]]:
        topology = fixture["topology"]
        names = []
        for level in topology["levels"]:
            names.extend(str(level[field]) for field in ("qb_side_cb", "post_sjtl_cb")
                         if level.get(field))
        return [self.instance(topology, name) for name in dict.fromkeys(names)]

    def test_core_cb_page_remains_compact(self):
        fixture = self.fixtures["core"]
        signals = set(self.page("core", "cb")["signals"])
        for cb in self.cb_instances(fixture):
            instance = cb["instance"]
            for element in ("BJ1", "BJ2"):
                for quantity in ("P", "V"):
                    self.assertIn(f"{quantity}({element}|{instance})", signals)
                self.assertNotIn(f"I({element}|{instance})", signals)
            for element in ("L1", "L4"):
                self.assertIn(f"I({element}|{instance})", signals)
            for element in ("L2", "L3"):
                self.assertNotIn(f"I({element}|{instance})", signals)
            for element in ("L1", "L2", "L3", "L4"):
                self.assertNotIn(f"V({element}|{instance})", signals)
            for pin in cb["pins"]:
                self.assertIn(f"V({pin})", signals)

    def test_debug_cb_page_includes_detailed_internals(self):
        fixture = self.fixtures["debug"]
        signals = set(self.page("debug", "cb")["signals"])
        for cb in self.cb_instances(fixture):
            instance = cb["instance"]
            for element in ("BJ1", "BJ2"):
                for quantity in ("P", "V", "I"):
                    self.assertIn(f"{quantity}({element}|{instance})", signals)
            for element in ("L1", "L2", "L3", "L4"):
                for quantity in ("I", "V"):
                    self.assertIn(f"{quantity}({element}|{instance})", signals)
            for pin in cb["pins"]:
                self.assertIn(f"V({pin})", signals)

    def test_d_acquisition_counts_and_legacy_debug_labels_are_unchanged(self):
        core = self.fixtures["core"]["probes"]
        debug = self.fixtures["debug"]["probes"]
        legacy_labels = {item["label"] for item in self.legacy_debug["signals"]}
        debug_labels = {item["label"] for item in debug["signals"]}
        self.assertEqual(core["signal_count"], 189)
        self.assertEqual(debug["signal_count"], 336)
        self.assertEqual(len(self.legacy_debug["signals"]), 336)
        self.assertEqual(debug_labels, legacy_labels)

    def test_e_acc_gap_count_remains_35(self):
        for profile in ("core", "debug"):
            self.assertEqual(self.page(profile, "acc_gap")["trace_count"], 35)

    def test_qb_cb_page_trace_counts_are_profile_specific(self):
        self.assertEqual(self.page("core", "qb")["trace_count"], 48)
        self.assertEqual(self.page("debug", "qb")["trace_count"], 76)
        self.assertEqual(self.page("core", "cb")["trace_count"], 53)
        self.assertEqual(self.page("debug", "cb")["trace_count"], 109)

    def test_f_g_h_pages_are_unique_manifest_backed_and_full_range(self):
        for fixture_name, fixture in self.fixtures.items():
            labels = {item["label"] for item in fixture["probes"]["signals"]}
            for page in fixture["plan"]["pages"]:
                with self.subTest(fixture=fixture_name, page=page["page"]):
                    page_signals = page["signals"]
                    self.assertEqual(len(page_signals), len(set(page_signals)))
                    self.assertTrue(set(page_signals) <= labels)
                    self.assertEqual(page["time_range"], "FULL_STORED_TIME_RANGE")

    def test_a025_profile_pages_resolve_to_existing_raw_columns(self):
        for profile in ("core", "debug"):
            for page in self.fixtures[profile]["plan"]["pages"]:
                with self.subTest(profile=profile, page=page["page"]):
                    self.assertTrue(set(page["signals"]) <= self.legacy_raw_headers)


if __name__ == "__main__":
    unittest.main()
