from __future__ import annotations

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


def config(size: int, mask: str, qb: str, sjtl: str, post: str):
    values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    values.update({
        "ARRAY_SIZE": str(size), "MASKS": mask,
        "QB_CB": qb, "SJTL_COUNT": sjtl, "POST_SJTL_CB": post,
    })
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
        values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
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
                           ("SJTL_COUNT", "1,-1"), ("OUTPUT_MODE", "T1")):
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
            values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
            values["SJTL_COUNT"] = "13"
            bad_config.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
            stderr = io.StringIO()
            with patch("run_case.subprocess.run", side_effect=AssertionError("process called")):
                with contextlib.redirect_stderr(stderr):
                    code = main(["--user-case", str(bad_config), "--mask", "01"])
            self.assertEqual(code, 2)
            self.assertIn("exactly 2", stderr.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
