from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
import re
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

from config import USER_CASE_KEYS, load_env, validate_user_case, ConfigError  # noqa: E402
from probes import generate_probes, validate_probe_lines  # noqa: E402
from topology import SOURCE_FILES, render_topology  # noqa: E402


def base_values():
    values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    values.update({
        "ARRAY_SIZE": "2", "MASKS": "00,01,10,11",
        "QB_CB": "0,1", "SJTL_COUNT": "1,1", "POST_SJTL_CB": "0,0",
        "OUTPUT_MODE": "TERMINAL", "PROBE_PROFILE": "core",
    })
    return values


def config(size: int, mask: str, qb: str, sjtl: str, post: str):
    values = base_values()
    values.update({"ARRAY_SIZE": str(size), "MASKS": mask,
                   "QB_CB": qb, "SJTL_COUNT": sjtl, "POST_SJTL_CB": post})
    params = validate_user_case(values)
    params["MASK"] = mask.split(",")[0]
    return params


def source_paths():
    return {role: REPO / path for role, path in SOURCE_FILES.items()}


class TopologyRenderTests(unittest.TestCase):
    def render(self, size, mask, qb, sjtl, post):
        params = config(size, mask, qb, sjtl, post)
        lines, manifest = render_topology(params, source_paths())
        probe_lines, probe_manifest = generate_probes(manifest, source_paths())
        validate_probe_lines(probe_lines, probe_manifest)
        return params, lines, manifest, probe_lines, probe_manifest

    def assert_structural_invariants(self, params, lines, manifest, probe_lines, probes):
        instances = [str(item["instance"]).casefold() for item in manifest["instances"]]
        self.assertEqual(len(instances), len(set(instances)))
        element_names = [line.split()[0].casefold() for line in lines]
        self.assertEqual(len(element_names), len(set(element_names)))
        internal_nodes = re.findall(r"\bL\d+_\d+\b", "\n".join(lines))
        # Each named inter-stage node is deliberately shared by one output and
        # one input; uniqueness means one distinct node token per stage edge.
        self.assertTrue(all(count == 2 for count in Counter(internal_nodes).values()))
        for line in lines:
            if line.casefold().startswith("x"):
                self.assertNotIn("0", line.split()[1:-1], line)
        self.assertFalse(any(line.split()[0].casefold().startswith("xmerge") for line in lines))
        self.assertTrue(all(line.split()[-1] in {"BVM", "BQ", "CB", "sJTL"} for line in lines))
        self.assertNotIn("0.001p", "\n".join(lines))
        self.assertEqual(manifest["array_size"], params["ARRAY_SIZE"])
        self.assertEqual(len(manifest["levels"]), params["ARRAY_SIZE"])
        self.assertEqual(manifest["terminal"]["output_node"], "FINAL_OUT")
        self.assertEqual(len(probe_lines), len(probes["signals"]))
        self.assertFalse(probes["scientific_classification_performed"])
        for level_index, level in enumerate(manifest["levels"]):
            expected_carry = (manifest["levels"][level_index + 1]["merge_node"]
                              if level_index + 1 < len(manifest["levels"])
                              else "FINAL_OUT")
            self.assertEqual(level["carry_node"], expected_carry)

    def test_T1_simple_two_by_one(self):
        params, lines, manifest, probe_lines, probes = self.render(2, "01", "0,0", "1,1", "0,0")
        self.assertIn("XBQ1 BVM1_SL MERGE1 BQ", lines)
        self.assertIn("XBQ2 BVM2_SL MERGE2 BQ", lines)
        self.assertEqual([len(level["sjtl_instances"]) for level in manifest["levels"]], [1, 1])
        self.assertIsNone(manifest["levels"][0]["post_sjtl_cb"])
        self.assert_structural_invariants(params, lines, manifest, probe_lines, probes)

    def test_T2_requested_two_by_one_example(self):
        params, lines, manifest, probe_lines, probes = self.render(2, "01", "0,1", "13,2", "1,0")
        self.assertIn("XBVM1 WL1 BL1 SE1 BVM1_SL BVM", lines)
        self.assertIn("XBQ1 BVM1_SL MERGE1 BQ", lines)
        self.assertIn("XSJTL1_13 L1_12 L1_13 sJTL", lines)
        self.assertIn("XPOSTCB1 L1_13 MERGE2 CB", lines)
        self.assertIn("XBQ2 BVM2_SL QB2_RAW BQ", lines)
        self.assertIn("XQBCB2 QB2_RAW MERGE2 CB", lines)
        self.assertIn("XSJTL2_02 L2_01 FINAL_OUT sJTL", lines)
        self.assertEqual(manifest["levels"][0]["carry_label"], "CARRY1")
        self.assertEqual(manifest["levels"][0]["carry_node"], "MERGE2")
        self.assert_structural_invariants(params, lines, manifest, probe_lines, probes)

    def test_T3_zero_sjtl_and_merge_alias(self):
        params, lines, manifest, probe_lines, probes = self.render(3, "011", "1,0,1", "0,3,1", "0,1,0")
        self.assertNotIn("XSJTL1_01", "\n".join(lines))
        self.assertEqual(manifest["levels"][0]["merge_node"], manifest["levels"][1]["merge_node"])
        self.assertEqual(manifest["logical_node_aliases"].get("MERGE2"), "MERGE1")
        self.assertEqual(manifest["levels"][0]["carry_output"]["status"], "UNAVAILABLE")
        self.assertIn("XPOSTCB2", [line.split()[0] for line in lines])
        self.assert_structural_invariants(params, lines, manifest, probe_lines, probes)

    def test_T4_four_by_one_level_order(self):
        params, lines, manifest, probe_lines, probes = self.render(4, "1011", "0,0,0,0", "1,2,3,4", "1,0,1,0")
        self.assertEqual([level["level"] for level in manifest["levels"]], [1, 2, 3, 4])
        self.assertEqual([len(level["sjtl_instances"]) for level in manifest["levels"]], [1, 2, 3, 4])
        self.assertEqual(len({item["instance"] for item in manifest["instances"]}),
                         len(manifest["instances"]))
        self.assert_structural_invariants(params, lines, manifest, probe_lines, probes)

    def test_zero_sjtl_terminal_alias(self):
        params, lines, manifest, probe_lines, probes = self.render(1, "1", "0", "0", "0")
        self.assertIn("XBQ1 BVM1_SL FINAL_OUT BQ", lines)
        self.assertEqual(manifest["levels"][0]["merge_node"], "FINAL_OUT")
        self.assertEqual(manifest["terminal"]["output_node"], "FINAL_OUT")
        self.assertEqual(manifest["logical_node_aliases"].get("MERGE1"), "FINAL_OUT")
        self.assert_structural_invariants(params, lines, manifest, probe_lines, probes)

    def test_topology_arrays_and_invalid_run_id_fail_closed(self):
        values = base_values()
        for key in ("QB_CB", "SJTL_COUNT", "POST_SJTL_CB"):
            invalid = dict(values)
            invalid[key] = "1"
            with self.subTest(array=key), self.assertRaises(ConfigError):
                validate_user_case(invalid)
        for mask_value in ("0", "02,01", "01,01"):
            invalid = dict(values)
            invalid["MASKS"] = mask_value
            with self.subTest(masks=mask_value), self.assertRaises(ConfigError):
                validate_user_case(invalid)
        for key, value in (("QB_CB", "0,2"), ("POST_SJTL_CB", "1,x"),
                           ("SJTL_COUNT", "1,-1"), ("OUTPUT_MODE", "T1x")):
            invalid = dict(values)
            invalid[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ConfigError):
                validate_user_case(invalid)
        for key, value in (("BVM_JM1_AREA", "0"), ("QB_LIN", "0p"),
                           ("CB_RJ1", "0"), ("SJTL_BIAS_RISE", "0p"),
                           ("BVM_RJM2", "opened"), ("NAME", "bad/name")):
            invalid = dict(values)
            invalid[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ConfigError):
                validate_user_case(invalid)
        invalid = dict(values, PROBE_PROFILE="wide")
        with self.assertRaisesRegex(ConfigError, "PROBE_PROFILE"):
            validate_user_case(invalid)
        from run_case import validate_run_id
        with self.assertRaises(ConfigError):
            validate_run_id("A1_T1_M1", "01")
        with self.assertRaises(ConfigError):
            validate_run_id("A001_T001_M10", "01")

    def test_duplicate_run_id_is_a_hard_stop(self):
        from run_case import require_new_run_dir
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "A001_T001_M01"
            target.mkdir()
            with self.assertRaises(ConfigError):
                require_new_run_dir(root, target.name)

    def test_invalid_array_fails_before_any_process_call(self):
        import contextlib
        import io
        from run_case import main
        with tempfile.TemporaryDirectory() as temp:
            bad_config = Path(temp) / "bad.env"
            values = base_values()
            values["SJTL_COUNT"] = "13"
            bad_config.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
            stderr = io.StringIO()
            with patch("run_case.subprocess.run", side_effect=AssertionError("process called")):
                with contextlib.redirect_stderr(stderr):
                    code = main(["--user-case", str(bad_config), "--mask", "01"])
            self.assertEqual(code, 2)
            self.assertIn("exactly 2", stderr.getvalue())

    def test_core_probe_counts_scale_with_array_size(self):
        cases = (
            (1, "1", "1", "3", "0"),
            (2, "01", "1,1", "3,1", "1,0"),
            (4, "0010", "1,1,1,1", "1,2,2,1", "1,1,1,0"),
        )
        counts = []
        for size, mask, qb, sjtl, post in cases:
            with self.subTest(array_size=size):
                _, _, _, lines, manifest = self.render(size, mask, qb, sjtl, post)
                self.assertEqual(manifest["profile"], "core")
                self.assertEqual(manifest["signal_count"], len(lines))
                labels = [signal["label"] for signal in manifest["signals"]]
                self.assertFalse(any(label.startswith("I(B") for label in labels))
                self.assertFalse(any(label.startswith("V(L") and "|" in label for label in labels))
                self.assertNotIn("V(R_TERM)", labels)
                counts.append(len(labels))
        self.assertTrue(all(left < right for left, right in zip(counts, counts[1:])))
        self.assertEqual(counts, [51, 97, 189])

    def test_a025_debug_preserves_legacy_labels_and_core_acc_gap_is_compact(self):
        from plot_run import build_plot_manifest

        run_dir = SERIES / "runs" / "A025_T006_M1111"
        topology = json.loads((run_dir / "topology_manifest.json").read_text())
        legacy = json.loads((run_dir / "probe_manifest.json").read_text())
        old_plots = json.loads((run_dir / "analysis" / "plot_manifest.json").read_text())
        sources = {role: run_dir / "snapshot" / "sources" / filename for role, filename in (
            ("BVM", "bvm_tunable.cir"), ("QB", "BQ_tunable.cir"),
            ("CB", "CB_tunable.cir"), ("SJTL", "sJTL_tunable.cir"),
        )}
        debug_lines, debug = generate_probes(topology, sources, profile="debug")
        core_lines, core = generate_probes(topology, sources, profile="core")
        old_labels = {item["label"] for item in legacy["signals"]}
        self.assertEqual(len(old_labels), 336)
        self.assertEqual({item["label"] for item in debug["signals"]}, old_labels)
        self.assertEqual(len(debug_lines), len(old_labels))
        self.assertLess(len(core_lines), len(debug_lines))
        self.assertEqual(len(core_lines), 189)
        core_labels = {item["label"] for item in core["signals"]}
        self.assertFalse(any(label.startswith("I(B") for label in core_labels))
        self.assertFalse(any(label.startswith("V(L") and "|" in label for label in core_labels))
        self.assertNotIn("V(R_TERM)", core_labels)

        plot_plan = build_plot_manifest(topology, core)
        old_acc_gap = next(page for page in old_plots["pages"] if page["page"] == "acc_gap")
        new_acc_gap = next(page for page in plot_plan["pages"] if page["page"] == "acc_gap")
        overview = next(page for page in plot_plan["pages"] if page["page"] == "overview")
        self.assertEqual(len(old_acc_gap["signals"]), 150)
        self.assertLess(new_acc_gap["trace_count"], len(old_acc_gap["signals"]))
        self.assertEqual(new_acc_gap["trace_count"], 35)
        self.assertTrue(set(new_acc_gap["signals"]).issubset(core_labels))
        self.assertFalse(any(label.startswith("I(B") for label in new_acc_gap["signals"]))
        self.assertFalse(any(label.startswith("V(L") and "|" in label
                             for label in new_acc_gap["signals"]))
        self.assertFalse(any(label.startswith(("P(", "I(L", "V(B_J", "I(BJ"))
                             for label in overview["signals"]))
        self.assertTrue(all(page["time_range"] == "FULL_STORED_TIME_RANGE"
                            for page in plot_plan["pages"]))

    def test_core_profile_contains_registered_component_and_boundary_signals(self):
        run_dir = SERIES / "runs" / "A025_T006_M1111"
        topology = json.loads((run_dir / "topology_manifest.json").read_text())
        sources = {role: run_dir / "snapshot" / "sources" / filename for role, filename in (
            ("BVM", "bvm_tunable.cir"), ("QB", "BQ_tunable.cir"),
            ("CB", "CB_tunable.cir"), ("SJTL", "sJTL_tunable.cir"),
        )}
        _, manifest = generate_probes(topology, sources, profile="core")
        labels = {signal["label"] for signal in manifest["signals"]}
        for index in range(1, 5):
            bvm, qb = f"XBVM{index}", f"XBQ{index}"
            for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
                for quantity in ("P", "V"):
                    self.assertIn(f"{quantity}({element}|{bvm})", labels)
            for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_SL"):
                self.assertIn(f"I({element}|{bvm})", labels)
            self.assertIn(f"V(BVM{index}_SL)", labels)
            for branch in ("WL", "BL", "SE"):
                self.assertIn(f"I(I_{branch}{index})", labels)
            for element in ("BJ1", "BJ2", "BJ3"):
                for quantity in ("P", "V"):
                    self.assertIn(f"{quantity}({element}|{qb})", labels)
            for element in ("LIN", "L1", "L2", "L3"):
                self.assertIn(f"I({element}|{qb})", labels)
            self.assertIn(f"V(BVM{index}_SL)", labels)
            output_node = topology["levels"][index - 1]["qb_raw_node"] or topology["levels"][index - 1]["merge_node"]
            self.assertIn(f"V({output_node})", labels)
        for instance in topology["instances"]:
            name = instance["instance"]
            if instance["subcircuit"] == "CB":
                for element in ("BJ1", "BJ2"):
                    for quantity in ("P", "V"):
                        self.assertIn(f"{quantity}({element}|{name})", labels)
                self.assertIn(f"I(L1|{name})", labels)
                self.assertIn(f"I(L4|{name})", labels)
                for node in instance["pins"]:
                    self.assertIn(f"V({node})", labels)
            elif instance["subcircuit"] == "sJTL":
                self.assertIn(f"P(BJ1|{name})", labels)
                self.assertIn(f"V(BJ1|{name})", labels)
                self.assertIn(f"I(L1|{name})", labels)
                self.assertIn(f"I(L2|{name})", labels)
                self.assertIn(f"V({instance['pins'][1]})", labels)
        self.assertIn("V(FINAL_OUT)", labels)
        self.assertIn("I(R_TERM)", labels)
        self.assertNotIn("V(R_TERM)", labels)


if __name__ == "__main__":
    unittest.main(verbosity=2)
