from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

from components import SNAPSHOT_NAMES, load_reference  # noqa: E402
from config import (ConfigError, T1_DEFAULTS, T1_KEYS, USER_CASE_KEYS,
                    load_user_case_snapshot, validate_user_case)  # noqa: E402
from evidence import _independent_t1_link_metric, plot_paths_for_mode  # noqa: E402
from plot_run import build_plot_manifest  # noqa: E402
from probes import generate_probes  # noqa: E402
from run_case import render_case, stable_env, t1_link_consistency  # noqa: E402
from submit import plot_files_for_mode  # noqa: E402
from stimulus import load_stimulus  # noqa: E402
from topology import (SOURCE_FILES, T1_CORE_INDUCTORS, T1_CORE_JUNCTIONS,
                      T1_SOURCE_FILE, parse_subcircuits)  # noqa: E402


A029 = SERIES / "runs" / "A029_T009_M1111"
T1_SOURCE = REPO / T1_SOURCE_FILE
TERMINAL_PAGES = [
    "01_overview.html", "02_bvm.html", "03_qb.html", "04_cb.html", "05_acc_gap.html",
]
T1_PAGES = TERMINAL_PAGES + ["06_t1.html"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values_from_a029(output_mode: str, profile: str = "core") -> dict[str, str]:
    values = load_user_case_snapshot(A029 / "USER_CASE.snapshot.env")
    values.update({"NAME": "t1_output_fixture", "MASKS": "1111",
                   "OUTPUT_MODE": output_mode, "PROBE_PROFILE": profile})
    values.update(T1_DEFAULTS)
    return values


def render_fixture(root: Path, mode: str, profile: str = "core") -> dict:
    values = values_from_a029(mode, profile)
    stimulus_path = A029 / "STIMULUS.snapshot.env"
    stimulus = load_stimulus(stimulus_path)
    old_user_text = (A029 / "USER_CASE.snapshot.env").read_text(encoding="utf-8")
    stimulus_text = stimulus_path.read_text(encoding="utf-8")
    if mode == "T1":
        old_user_text = stable_env(values)
    result = render_case(
        values, stimulus, "1111", root, fixture_only=True,
        user_snapshot_text=old_user_text, stimulus_snapshot_text=stimulus_text,
    )
    result["plan"] = build_plot_manifest(result["topology_manifest"], result["probe_manifest"])
    return result


def strip_fixture_banner(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    banner = "* RENDER_FIXTURE_ONLY — not JoSIM experiment evidence\n"
    if not text.startswith(banner):
        raise AssertionError(f"missing render-only banner: {path}")
    return text[len(banner):]


class T1OutputModeTests(unittest.TestCase):
    def test_source_pin_order_and_representatives_are_read_from_real_t1_source(self):
        t1 = parse_subcircuits({"T1": T1_SOURCE})["T1"]
        self.assertEqual(t1.pins, ("I", "CLK", "S", "C", "N_BIAS1", "N_BIAS2", "N_BIAS3"))
        self.assertTrue(set(T1_CORE_JUNCTIONS) <= t1.elements)
        self.assertTrue(set(T1_CORE_INDUCTORS) <= t1.elements)
        self.assertEqual(len([item for item in t1.elements if item.startswith("B_J")]), 11)
        self.assertEqual(len([item for item in t1.elements if item.startswith("L")]), 17)
        reference = load_reference()
        self.assertEqual(reference["SOURCE_T1_SHA256"], digest(T1_SOURCE))

    def test_terminal_output_is_regression_identical_to_a029(self):
        with tempfile.TemporaryDirectory(prefix="t1-terminal-regression-") as temp:
            root = Path(temp) / "terminal"
            result = render_fixture(root, "TERMINAL")
            old_deck = A029 / "actual_deck.cir"
            self.assertEqual(strip_fixture_banner(root / "actual_deck.cir"),
                             old_deck.read_text(encoding="utf-8"))
            self.assertEqual(strip_fixture_banner(root / "stimulus.inc"),
                             (A029 / "stimulus.inc").read_text(encoding="utf-8"))
            self.assertRegex((root / "actual_deck.cir").read_text(encoding="utf-8"),
                             r"(?m)^R_TERM FINAL_OUT 0 2$")
            self.assertNotRegex((root / "actual_deck.cir").read_text(encoding="utf-8"),
                                r"(?m)^(?:V_T1_LINK|XT1)\b")
            old_topology = json.loads((A029 / "topology_manifest.json").read_text(encoding="utf-8"))
            old_probes = json.loads((A029 / "probe_manifest.json").read_text(encoding="utf-8"))
            old_plots = json.loads((A029 / "analysis/plot_manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("output_mode", result["topology_manifest"])
            self.assertNotIn("receiver", result["topology_manifest"])
            self.assertEqual(result["topology_manifest"]["topology"], old_topology["topology"])
            self.assertEqual(result["topology_manifest"]["levels"], old_topology["levels"])
            self.assertEqual(result["topology_manifest"]["instances"], old_topology["instances"])
            self.assertEqual([item["label"] for item in result["probe_manifest"]["signals"]],
                             [item["label"] for item in old_probes["signals"]])
            self.assertEqual(result["probe_manifest"]["signal_count"], 168)
            self.assertEqual([page["file"] for page in result["plan"]["pages"]], TERMINAL_PAGES)
            self.assertEqual([page["signals"] for page in result["plan"]["pages"]],
                             [page["signals"] for page in old_plots["pages"]])
            for role, filename in SNAPSHOT_NAMES.items():
                self.assertEqual(
                    (root / "snapshot" / "sources" / filename).read_bytes(),
                    (A029 / "snapshot" / "sources" / filename).read_bytes(),
                    role,
                )
            self.assertEqual({item["role"] for item in result["source_manifest"]["sources"]},
                             set(SOURCE_FILES))

    def test_t1_mode_renders_direct_source_bias_link_and_loads(self):
        with tempfile.TemporaryDirectory(prefix="t1-output-render-") as temp:
            root = Path(temp) / "t1"
            result = render_fixture(root, "T1")
            deck = (root / "actual_deck.cir").read_text(encoding="utf-8")
            self.assertNotRegex(deck, r"(?mi)^\s*R_TERM\b")
            for line in (
                "V_BIAS1 N_BIAS1 0 DC 1.67m",
                "V_BIAS2 N_BIAS2 0 DC 1.67m",
                "I_BIAS3 N_BIAS3 0 DC 35u",
                "R_S S 0 12", "R_C C 0 12", "R_CLK_QUIET CLK 0 5",
                "V_T1_LINK FINAL_OUT T1_I 0",
                "XT1 T1_I CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1",
            ):
                self.assertIn(line, deck)
            self.assertNotIn("V_BIAS3", deck)
            self.assertLess(deck.index(".model jjmit"), deck.index(".include "))
            topology = result["topology_manifest"]
            self.assertEqual(topology["output_mode"], "T1")
            self.assertEqual(topology["front_end_output_node"], "FINAL_OUT")
            self.assertEqual(topology["receiver"]["input_node"], "T1_I")
            self.assertEqual(topology["receiver"]["link"], {
                "instance": "V_T1_LINK", "positive_node": "FINAL_OUT",
                "negative_node": "T1_I", "voltage": "0",
            })
            self.assertEqual(topology["receiver"]["source_pins"],
                             list(parse_subcircuits({"T1": T1_SOURCE})["T1"].pins))
            t1_source = next(item for item in result["source_manifest"]["sources"]
                             if item["role"] == "T1")
            self.assertEqual(t1_source["source_mode"], "DIRECT_CANONICAL_INCLUDE")
            self.assertEqual(t1_source["canonical_source_path"], T1_SOURCE_FILE.as_posix())
            self.assertEqual(t1_source["canonical_source_sha256"], digest(T1_SOURCE))
            self.assertEqual((root / t1_source["deck_include_path"]).resolve(), T1_SOURCE.resolve())
            self.assertEqual(t1_source["rendered_snapshot_path"], None)
            self.assertFalse(any("T1" in path.name for path in (root / "snapshot/sources").iterdir()))
            self.assertEqual(result["parameter_manifest"]["t1"], {
                key: values_from_a029("T1")[key] for key in sorted(T1_KEYS)
            })

    def test_t1_front_end_stimulus_and_first_five_pages_are_invariant(self):
        with tempfile.TemporaryDirectory(prefix="t1-topology-invariance-") as temp:
            root = Path(temp)
            terminal = render_fixture(root / "terminal", "TERMINAL")
            t1 = render_fixture(root / "t1", "T1")
            term_top = terminal["topology_manifest"]
            t1_top = t1["topology_manifest"]
            self.assertEqual(term_top["topology"], t1_top["topology"])
            self.assertEqual(term_top["levels"], t1_top["levels"])
            self.assertEqual(term_top["logical_node_aliases"], t1_top["logical_node_aliases"])
            self.assertEqual(term_top["carry_aliases"], t1_top["carry_aliases"])
            self.assertEqual(
                [item for item in term_top["instances"]],
                [item for item in t1_top["instances"] if item["subcircuit"] != "T1"],
            )
            self.assertEqual((root / "terminal/stimulus.inc").read_bytes(),
                             (root / "t1/stimulus.inc").read_bytes())
            for filename in SNAPSHOT_NAMES.values():
                self.assertEqual(
                    digest(root / "terminal/snapshot/sources" / filename),
                    digest(root / "t1/snapshot/sources" / filename),
                )
            terminal_pages = terminal["plan"]["pages"]
            t1_pages = t1["plan"]["pages"]
            self.assertEqual([page["file"] for page in terminal_pages], TERMINAL_PAGES)
            self.assertEqual([page["file"] for page in t1_pages], T1_PAGES)
            self.assertEqual([page["signals"] for page in terminal_pages],
                             [page["signals"] for page in t1_pages[:5]])

    def test_t1_core_is_compact_debug_is_source_complete_and_page_qa_is_mode_specific(self):
        with tempfile.TemporaryDirectory(prefix="t1-probe-profile-") as temp:
            core = render_fixture(Path(temp) / "core", "T1", "core")
            debug = render_fixture(Path(temp) / "debug", "T1", "debug")
            core_page = core["plan"]["pages"][-1]
            debug_page = debug["plan"]["pages"][-1]
            core_labels = set(core_page["signals"])
            debug_labels = set(debug_page["signals"])
            t1 = parse_subcircuits({"T1": T1_SOURCE})["T1"]
            junctions = [name for name in t1.elements if name.startswith("B_J")]
            inductors = [name for name in t1.elements
                         if name.startswith("L") and name[1:].isdigit()]
            self.assertEqual(len(junctions), 11)
            self.assertEqual(len(inductors), 17)
            for element in junctions:
                for quantity in ("P", "V", "I"):
                    self.assertIn(f"{quantity}({element}|XT1)", debug_labels)
                self.assertNotIn(f"I({element}|XT1)", core_labels)
            for element in inductors:
                for quantity in ("I", "V"):
                    self.assertIn(f"{quantity}({element}|XT1)", debug_labels)
                self.assertNotIn(f"V({element}|XT1)", core_labels)
            for signal in ("V(FINAL_OUT)", "V(T1_I)", "V(CLK)", "V(S)", "V(C)",
                           "I(R_S)", "I(R_C)"):
                self.assertIn(signal, core_labels)
                self.assertIn(signal, debug_labels)
            for element in T1_CORE_JUNCTIONS:
                for quantity in ("P", "V"):
                    self.assertIn(f"{quantity}({element}|XT1)", core_labels)
            for element in T1_CORE_INDUCTORS:
                self.assertIn(f"I({element}|XT1)", core_labels)
            self.assertEqual(core["probe_manifest"]["signal_count"], 186)
            self.assertGreater(debug["probe_manifest"]["signal_count"],
                               core["probe_manifest"]["signal_count"])
            self.assertEqual(core_page["trace_count"], 20)
            self.assertEqual(debug_page["trace_count"], 74)
            for fixture in (core, debug):
                labels = {item["label"] for item in fixture["probe_manifest"]["signals"]}
                for page in fixture["plan"]["pages"]:
                    self.assertEqual(len(page["signals"]), len(set(page["signals"])))
                    self.assertTrue(set(page["signals"]) <= labels)
                    self.assertEqual(page["time_range"], "FULL_STORED_TIME_RANGE")
            self.assertEqual([page["file"] for page in core["plan"]["pages"]], T1_PAGES)

    def test_output_mode_and_quiet_clock_validation_fail_closed(self):
        terminal = values_from_a029("TERMINAL")
        with self.assertRaisesRegex(ConfigError, "OUTPUT_MODE"):
            validate_user_case(dict(terminal, OUTPUT_MODE="T!"))
        with self.assertRaisesRegex(ConfigError, "T1_CLK_MODE"):
            validate_user_case(dict(values_from_a029("T1"), T1_CLK_MODE="PULSE"))
        with self.assertRaisesRegex(ConfigError, "TERM_R"):
            validate_user_case(dict(terminal, TERM_R="0"))
        self.assertEqual(validate_user_case(dict(values_from_a029("T1"), TERM_R="0"))[
                         "OUTPUT_MODE"], "T1")
        with self.assertRaisesRegex(ConfigError, "T1_BIAS3"):
            validate_user_case(dict(values_from_a029("T1"), T1_BIAS3="0u"))

    def test_link_metric_is_raw_grid_report_only_arithmetic(self):
        trace = SimpleNamespace(
            sample_count=3, time=(0.0, 1e-12, 2e-12),
            column=lambda label: {
                "V(FINAL_OUT)": (0.0, 1.0, 2.0),
                "V(T1_I)": (0.1, 0.8, 1.9),
            }[label],
        )
        metric = t1_link_consistency(trace)
        self.assertEqual(metric["status"], "MEASURED_REPORT_ONLY")
        self.assertAlmostEqual(metric["max_abs_difference_v"], 0.2)
        self.assertEqual(metric["units"], "V")
        self.assertTrue(metric["uses_exact_stored_rows"])
        self.assertFalse(metric["interpolation_or_resampling"])
        self.assertIsNone(metric["pass_fail_threshold_v"])

    def test_independent_raw_recomputation_and_mode_specific_package_page_sets(self):
        with tempfile.TemporaryDirectory(prefix="t1-link-raw-check-") as temp:
            raw = Path(temp) / "raw.csv"
            raw.write_text(
                "time,V(FINAL_OUT),V(T1_I)\n0,0,0.1\n1e-12,1,0.8\n2e-12,2,1.9\n",
                encoding="utf-8",
            )
            value, count = _independent_t1_link_metric(raw)
        self.assertAlmostEqual(value, 0.2)
        self.assertEqual(count, 3)
        self.assertEqual(len(plot_paths_for_mode("TERMINAL")), 5)
        self.assertEqual(len(plot_paths_for_mode("T1")), 6)
        self.assertEqual(plot_paths_for_mode("T1"), plot_files_for_mode("T1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
