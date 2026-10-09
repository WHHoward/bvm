from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


SERIES = Path(__file__).resolve().parents[1]
SCRIPT = SERIES / "scripts" / "submit.py"
SPEC = spec_from_file_location("bvm4x4_submit", SCRIPT)
submit = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(submit)


class DeltaPackageTests(unittest.TestCase):
    def test_delta_closure_only_adds_a009_after_verified_bus400_base(self):
        self.assertEqual(submit.DELTA_RUN_IDS, ("A009_paper_like",))
        self.assertEqual(submit.BUS400_RUN_IDS, ("A007_BUS400_D3_N0", "A008_BUS400_D3_N1"))

    def test_historical_raw_is_referenced_not_reincluded(self):
        a007_raw = f"test/exploration/{SERIES.name}/runs/A007_BUS400_D3_N0/raw.csv"
        a007_qa = f"test/exploration/{SERIES.name}/runs/A007_BUS400_D3_N0/plot_qa_responsive_v2.json"
        a009_raw = f"test/exploration/{SERIES.name}/runs/A009_paper_like/raw.csv"
        a006_raw = f"test/exploration/{SERIES.name}/runs/A006_PAPER_1101_1101/raw.csv"
        self.assertFalse(submit.is_allowed_delta_run_path(a007_raw))
        self.assertTrue(submit.is_allowed_delta_run_path(a007_qa))
        self.assertTrue(submit.is_allowed_delta_run_path(a009_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(a006_raw))


if __name__ == "__main__":
    unittest.main()
