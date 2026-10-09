from __future__ import annotations

import sys
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402


def rendered(preset: str):
    case, stimulus, t1 = platform.load_config(preset)
    return case, stimulus, t1, platform.render(case, stimulus, t1, platform.RUNS / "_TEST_PREVIEW")


class DiagonalPlatformTests(unittest.TestCase):
    def test_diagonal_map_is_exact_partition(self):
        flat = [cell for group in platform.DIAGONALS.values() for cell in group]
        self.assertEqual(len(flat), 16)
        self.assertEqual(set(flat), set(platform.CELLS))
        self.assertEqual([len(platform.DIAGONALS[f"D{i}"]) for i in range(7)], [1, 2, 3, 4, 3, 2, 1])
        for row in range(1, 5):
            for col in range(1, 5):
                cell = f"R{row}C{col}"
                diagonal = next(name for name, cells in platform.DIAGONALS.items() if cell in cells)
                self.assertEqual(int(diagonal[1]), row + 3 - col)

    def test_registered_masks_and_paper_target_vector(self):
        expected = {
            "D3_N0": [],
            "D3_N1": ["R1C1"],
            "D3_N2": ["R1C1", "R2C2"],
            "D3_N3": ["R1C1", "R2C2", "R3C3"],
            "D3_N4": ["R1C1", "R2C2", "R3C3", "R4C4"],
        }
        for name, cells in expected.items():
            case, _stim, _t1, output = rendered(name)
            self.assertEqual(platform._active_cells(case), cells)
            self.assertEqual(output["static_qa"]["status"], "PASS")
        case, _stim, _t1, output = rendered("PAPER_1101_1101")
        counts = [sum(cell in platform._active_cells(case) for cell in cells)
                  for cells in platform.DIAGONALS.values()]
        self.assertEqual(counts, [1, 1, 1, 3, 1, 1, 1])
        self.assertEqual(case["SE_ENABLE_MASK"], "ALL")
        self.assertEqual(output["static_qa"]["active_final_crosspoints"],
                         ["R1C1", "R1C2", "R1C4", "R2C1", "R2C2", "R2C4", "R4C1", "R4C2", "R4C4"])

    def test_render_has_shared_rows_columns_independent_cell_se_and_serial_chains(self):
        case, _stim, _t1, output = rendered("D3_N4")
        deck = output["deck"].splitlines()
        self.assertEqual(len([line for line in deck if line.startswith("XBVM_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XBQ_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XSJTL_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XCB_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("R_TERM_")]), 7)
        self.assertIn("XBVM_R1C1 WL_R1 BL_C1 SE_R1C1 SL_R1C1 BVM", deck)
        self.assertIn("XBVM_R4C4 WL_R4 BL_C4 SE_R4C4 SL_R4C4 BVM", deck)
        self.assertIn("XBQ_R1C1 SL_R1C1 MERGE_D3_L1 BQ", deck)
        self.assertIn("XCB_D3_L1 SJTL_OUT_D3_L1 MERGE_D3_L2 CB", deck)
        self.assertIn("XCB_D3_L4 SJTL_OUT_D3_L4 DOUT_D3 CB", deck)
        self.assertFalse(any("MERGE_D3" in line and "MERGE_D2" in line for line in deck))
        self.assertEqual(output["static_qa"]["driver_count_by_branch"], {"WL": 4, "BL": 4, "SE": 16})
        self.assertTrue(output["static_qa"]["unique_outputs"])

    def test_registered_d3_cases_only_change_final_read_se_mask(self):
        outputs = {name: rendered(name)[3] for name in ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4")}
        stimuli = {name: {line.split()[0]: line for line in outputs[name]["stimulus_text"].splitlines()
                          if line.startswith("I_")} for name in outputs}
        base_non_se = {source: line for source, line in stimuli["D3_N0"].items()
                       if not source.startswith("I_SE_")}
        targets = {
            "D3_N0": set(),
            "D3_N1": {"R1C1"},
            "D3_N2": {"R1C1", "R2C2"},
            "D3_N3": {"R1C1", "R2C2", "R3C3"},
            "D3_N4": set(platform.DIAGONALS["D3"]),
        }
        def knots(line: str):
            tokens=line.split("PWL(",1)[1].removesuffix(")").split()
            return list(zip(tokens[0::2],tokens[1::2]))
        for name, lines in stimuli.items():
            self.assertEqual({src: line for src,line in lines.items() if not src.startswith("I_SE_")}, base_non_se)
            self.assertEqual(len([src for src in lines if src.startswith("I_SE_")]), 16)
            for cell in platform.CELLS:
                points=knots(lines[f"I_SE_{cell}"])
                baseline=knots(stimuli["D3_N0"][f"I_SE_{cell}"])
                self.assertEqual([point for point in points if point[0] != "111p" and point[0] != "120p" and point[0] != "121p"],
                                 [point for point in baseline if point[0] != "111p" and point[0] != "120p" and point[0] != "121p"])
                final_value=dict(points).get("111p")
                self.assertEqual(final_value, "100u" if cell in targets[name] else "0")
            self.assertEqual(outputs[name]["static_qa"]["status"], "PASS")
        self.assertEqual(outputs["D3_N0"]["probes"]["signal_count"], 242)

    def test_canonical_sources_and_t1_off_isolation(self):
        source = platform.verify_sources()
        case, stimulus, t1, output = rendered("PAPER_1101_1101")
        self.assertEqual({k: v["sha256"] for k, v in source.items()}, platform.SOURCE_SHA256)
        self.assertEqual(output["static_qa"]["status"], "PASS")
        self.assertNotIn("t1_cell.cir", output["deck"])
        self.assertFalse(any(line.startswith(("XT1", "V_BIAS", "V_TRIG_CLK", "XCBU", "XDFF"))
                             for line in output["deck"].splitlines()))
        changed_t1 = dict(t1)
        changed_t1["T1_J1_AREA"] = "99"
        changed_t1["T1_L1"] = "99p"
        self.assertEqual(output["deck"], platform.render(case, stimulus, changed_t1,
                                                           platform.RUNS / "_TEST_PREVIEW")["deck"])
        with self.assertRaisesRegex(platform.ConfigError, "only DIAGONAL_TERMINAL"):
            platform.validate_config({**case, "OUTPUT_MODE": "DIAGONAL_T1_CHAIN"}, stimulus, t1)

    def test_probe_profile_stays_under_raw_limit_and_keeps_required_boundaries(self):
        case, _stim, _t1, output = rendered("D3_N4")
        labels = {item["label"] for item in output["probes"]["signals"]}
        self.assertEqual(output["probes"]["profile"], "diagonal_focus")
        self.assertEqual(output["probes"]["signal_count"], 242)
        self.assertLess(platform.estimate_raw_bytes(output["probes"]["signal_count"]), 100_000_000)
        for cell in platform.CELLS:
            for branch, element in (("WL", "R_WL"), ("BL", "R_BL"), ("SE", "R_SE")):
                self.assertIn(f"I({element}|XBVM_{cell})", labels)
            self.assertIn(f"V(SL_{cell})", labels)
        for diagonal in platform.DIAGONALS:
            self.assertIn(f"V(DOUT_{diagonal})", labels)
        for level in range(1, 5):
            self.assertIn(f"V(MERGE_D3_L{level})", labels)
            self.assertIn(f"V(SJTL_OUT_D3_L{level})", labels)
            self.assertIn(f"P(BJ1|XSJTL_D3_L{level})", labels)
            self.assertIn(f"P(BJ1|XCB_D3_L{level})", labels)


if __name__ == "__main__":
    unittest.main()
