#!/usr/bin/env python3
"""Focused tests for historical sensing-line endpoint probe labels."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.probes import flatten_probe_labels  # noqa: E402
from bvmtools.sl_probes import (  # noqa: E402
    HISTORICAL_SL_ENDPOINT_JUNCTIONS,
    historical_sensing_line_endpoint_probes,
)


class HistoricalSensingLineProbeTests(unittest.TestCase):
    def test_all_bvm_first_and_last_junctions_have_pvi_labels(self) -> None:
        probes = historical_sensing_line_endpoint_probes()
        labels = flatten_probe_labels(probes)
        self.assertEqual(tuple(probes), ("BVM1", "BVM2", "BVM3", "BVM4"))
        for _, first, last in HISTORICAL_SL_ENDPOINT_JUNCTIONS:
            for junction in (first, last):
                for kind in ("P", "V", "I"):
                    self.assertIn(f"{kind}({junction})", labels)

    def test_bvm4_bvmout_is_not_mislabeled_as_an_sl_endpoint(self) -> None:
        labels = flatten_probe_labels(historical_sensing_line_endpoint_probes())
        self.assertNotIn("P(BVMOUT)", labels)
        self.assertNotIn("V(BVMOUT)", labels)
        self.assertNotIn("I(BVMOUT)", labels)


if __name__ == "__main__":
    unittest.main()
