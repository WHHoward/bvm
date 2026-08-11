#!/usr/bin/env python3
"""Regression tests for josim-plot2.py -j phase scaling (M12).

Covers all five layouts (grid / stacked / combined / square / sep_comb) in
raw-rad and 2pi modes. The tests assert on the trace DATA values, so a
label-only change (the historical bug) fails them.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "josim-plot2.py"
SPEC = importlib.util.spec_from_file_location("josim_plot2", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot import {SCRIPT}")
PLOT2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLOT2)

TAU = 2.0 * math.pi
LAYOUTS = ["grid", "stacked", "combined", "square", "sep_comb"]
FUNCS = {
    "grid": "grid_layout",
    "stacked": "stacked_layout",
    "combined": "combined_layout",
    "square": "square_layout",
    "sep_comb": "seperate_combined_layout",
}


class _Args:
    """Minimal argparse.Namespace stand-in for the layout functions."""

    def __init__(self, jump: str) -> None:
        self.jump = jump
        self.subset = None


def _make_df() -> pd.DataFrame:
    t = np.linspace(0.0, 1e-11, 5)
    phase = np.array([0.0, 1.0, TAU, 2.0, 3.0])  # arbitrary rad values
    volt = np.array([1e-4, 2e-4, 3e-4, 4e-4, 5e-4])
    return pd.DataFrame({"time": t, "P(B01)": phase, "V(N1)": volt})


class PhaseScalingTests(unittest.TestCase):
    """AC1/AC3: P(...) traces scale by pfact(jump) in ALL layouts."""

    def test_phase_traces_scale_in_all_layouts(self) -> None:
        df = _make_df()
        expected = {
            "rad": df["P(B01)"].values,
            "2pi": df["P(B01)"].values / TAU,
        }
        for layout in LAYOUTS:
            for jump, want in expected.items():
                with self.subTest(layout=layout, jump=jump):
                    fig = getattr(PLOT2, FUNCS[layout])(df, _Args(jump))
                    p_traces = [tr for tr in fig.data if tr.name.startswith("P(")]
                    self.assertTrue(p_traces, f"{layout}: no P trace found")
                    for trace in p_traces:
                        np.testing.assert_allclose(
                            np.asarray(trace.y, dtype=float), want,
                            err_msg=f"{layout}/{jump} P trace not scaled correctly",
                        )

    def test_raw_rad_is_unscaled(self) -> None:
        """-j rad (default) must keep raw radians."""
        df = _make_df()
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                fig = getattr(PLOT2, FUNCS[layout])(df, _Args("rad"))
                p_traces = [tr for tr in fig.data if tr.name.startswith("P(")]
                for trace in p_traces:
                    np.testing.assert_allclose(
                        np.asarray(trace.y, dtype=float),
                        df["P(B01)"].values,
                        err_msg=f"{layout}/rad must be raw radians",
                    )


class NonPhaseScalingTests(unittest.TestCase):
    """AC1: non-phase traces must NOT be scaled by -j."""

    def test_voltage_traces_unaffected_by_jump(self) -> None:
        df = _make_df()
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                rad_fig = getattr(PLOT2, FUNCS[layout])(df, _Args("rad"))
                pi_fig = getattr(PLOT2, FUNCS[layout])(df, _Args("2pi"))
                v_rad = [tr for tr in rad_fig.data if tr.name.startswith("V(")]
                v_pi = [tr for tr in pi_fig.data if tr.name.startswith("V(")]
                self.assertTrue(v_rad, f"{layout}: no V trace found")
                for a, b in zip(v_rad, v_pi):
                    np.testing.assert_allclose(
                        np.asarray(a.y, dtype=float),
                        np.asarray(b.y, dtype=float),
                        err_msg=f"{layout}: V trace must not scale with -j",
                    )


class LabelTests(unittest.TestCase):
    """AC2: -j 2pi label states turns / rad/2pi and never SFQ count."""

    def test_2pi_label_is_turns_not_sfq(self) -> None:
        label = PLOT2.y_axis_title("P(B01)", _Args("2pi"))
        self.assertNotIn("SFQ", label)
        self.assertNotIn("sfq", label)
        self.assertIn("turns", label.lower())
        self.assertIn("2pi", label.lower().replace(" ", ""))

    def test_rad_label_is_radians(self) -> None:
        label = PLOT2.y_axis_title("P(B01)", _Args("rad"))
        self.assertIn("rad", label.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
