from __future__ import annotations

import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))

from config import (ConfigError, STIMULUS_KEYS, USER_CASE_KEYS, load_env,
                    parse_quantity, validate_user_case)  # noqa: E402
from stimulus import load_stimulus, render_stimulus  # noqa: E402


def default_params(mask: str):
    values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    values["MASKS"] = ",".join(("00", "01", "10", "11"))
    params = validate_user_case(values)
    params["MASK"] = mask
    return params


def parse_source(line: str) -> list[tuple[Decimal, Decimal]]:
    match = re.search(r"pwl\((.*)\)$", line)
    if not match:
        raise AssertionError(f"no PWL found in {line}")
    tokens = match.group(1).split()
    if len(tokens) % 2:
        raise AssertionError(f"odd PWL token count in {line}")
    return [(parse_quantity(tokens[index], label="time"),
             parse_quantity(tokens[index + 1], label="current"))
            for index in range(0, len(tokens), 2)]


def at(points: list[tuple[Decimal, Decimal]], time_s: Decimal) -> Decimal:
    if time_s <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if time_s <= t1:
            if time_s == t1:
                return v1
            return v0 + (v1 - v0) * (time_s - t0) / (t1 - t0)
    return points[-1][1]


class StimulusRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stimulus = load_stimulus(SERIES / "STIMULUS.env")

    def signal_points(self, mask: str, label: str):
        deck = render_stimulus(self.stimulus, default_params(mask), mask)
        line = next(line for line in deck.splitlines() if line.startswith(f"{label} "))
        return parse_source(line)

    def test_mask_only_controls_final_read(self):
        for mask in ("00", "01", "10", "11"):
            for index in (1, 2):
                active = mask[index - 1] == "1"
                for branch, write0, read0, write1, final_active, final_inactive in (
                    ("WL", Decimal("-100e-6"), Decimal("100e-6"), Decimal("100e-6"), Decimal("100e-6"), Decimal(0)),
                    ("BL", Decimal("-100e-6"), Decimal(0), Decimal("100e-6"), Decimal(0), Decimal(0)),
                    ("SE", Decimal(0), Decimal("100e-6"), Decimal(0), Decimal("100e-6"), Decimal(0)),
                ):
                    points = self.signal_points(mask, f"I_{branch}{index}")
                    self.assertEqual(at(points, Decimal("55e-12")), write0)
                    self.assertEqual(at(points, Decimal("75e-12")), read0)
                    self.assertEqual(at(points, Decimal("95e-12")), write1)
                    self.assertEqual(at(points, Decimal("115e-12")), final_active if active else final_inactive)

    def test_each_mask_generates_all_three_sources_per_bvm(self):
        for mask in ("00", "01", "10", "11"):
            deck = render_stimulus(self.stimulus, default_params(mask), mask)
            sources = [line.split()[0] for line in deck.splitlines() if line.startswith("I_")]
            self.assertEqual(sources, ["I_WL1", "I_BL1", "I_SE1", "I_WL2", "I_BL2", "I_SE2"])

    def test_user_edits_drive_rendered_timing_and_amplitude(self):
        custom = dict(self.stimulus)
        custom["WRITE0_START"] = "48p"
        custom["WRITE0_WL"] = "-80u"
        deck = render_stimulus(custom, default_params("00"), "00")
        self.assertIn("48p 0 49p -80u", deck)
        points = parse_source(next(line for line in deck.splitlines() if line.startswith("I_WL1 ")))
        self.assertEqual(at(points, Decimal("53e-12")), Decimal("-80e-6"))

    def test_empty_or_unknown_stimulus_config_fails(self):
        with self.assertRaises(ConfigError):
            load_env(SERIES / "STIMULUS.env", STIMULUS_KEYS - {"READ_ACTIVE_WL"})
        bad = dict(self.stimulus)
        bad["READ_START"] = "70p"
        with self.assertRaises(ConfigError):
            render_stimulus(bad, default_params("01"), "01")


if __name__ == "__main__":
    unittest.main(verbosity=2)
