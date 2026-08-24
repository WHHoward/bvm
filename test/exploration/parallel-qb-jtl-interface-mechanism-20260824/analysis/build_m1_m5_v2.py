#!/usr/bin/env python3
"""Re-emit the same M1-M5 topologies with the missing interface probes closed."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_m1_m5 as base  # noqa: E402


base.INPUTS = base.EXP / "inputs-v2"


if __name__ == "__main__":
    base.main()
