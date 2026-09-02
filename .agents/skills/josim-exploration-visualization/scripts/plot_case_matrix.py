#!/usr/bin/env python3
"""Compatibility launcher; maintained implementation lives in josim-viz."""

from pathlib import Path
import runpy


TARGET = Path(__file__).resolve().parents[2] / "josim-viz" / "scripts" / Path(__file__).name
runpy.run_path(str(TARGET), run_name="__main__")
