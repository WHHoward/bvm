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
    def test_delta_closure_adds_a017_to_a019_after_a013_to_a016_checkpoint(self):
        self.assertEqual(submit.DELTA_RUN_IDS, (
            "A017_PAPER_1101_1101", "A018_T1_ALL_QUIET", "A019_T1_ALL_PLUSE"))
        self.assertEqual(submit.PREVIOUS_DELTA_RUN_IDS, (
            "A013_T1_ALL_QUIET", "A014_T1_ALL_CLOCK",
            "A015_T1_PAPER_QUIET", "A016_T1_PAPER_CLOCK"))
        self.assertEqual(submit.DELTA_BASE_COMMIT, "684531519dda6e0a1e8ffec24d0711ee08adf6d1")
        self.assertEqual(submit.DELTA_BASE_PACKAGE_NAME, submit.T1_A013_A016_SOURCE_NAME)
        self.assertEqual(submit.INVALID_PRESERVED_DELTA_RUN_IDS, {"A017_PAPER_1101_1101"})

    def test_historical_raw_is_referenced_not_reincluded(self):
        a007_raw = f"test/exploration/{SERIES.name}/runs/A007_BUS400_D3_N0/raw.csv"
        a009_raw = f"test/exploration/{SERIES.name}/runs/A009_paper_like/raw.csv"
        a006_raw = f"test/exploration/{SERIES.name}/runs/A006_PAPER_1101_1101/raw.csv"
        a013_raw = f"test/exploration/{SERIES.name}/runs/A013_T1_ALL_QUIET/raw.csv"
        a017_raw = f"test/exploration/{SERIES.name}/runs/A017_PAPER_1101_1101/raw.csv"
        self.assertFalse(submit.is_allowed_delta_run_path(a007_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(a009_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(a006_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(
            f"test/exploration/{SERIES.name}/runs/A010_PAPER_1101_1101/raw.csv"))
        self.assertFalse(submit.is_allowed_delta_run_path(a013_raw))
        self.assertTrue(submit.is_allowed_delta_run_path(a017_raw))
        self.assertTrue(submit.is_allowed_delta_run_path(
            f"test/exploration/{SERIES.name}/runs/A019_T1_ALL_PLUSE/raw.csv"))

    def test_new_run_sources_partition_from_shared_source_and_are_unique(self):
        sources = []
        shared = SERIES / "USER_CASE.env"
        sources.append((shared, shared.relative_to(submit.REPO).as_posix()))
        for run_id in submit.DELTA_RUN_IDS:
            for name in ("raw.csv", "result.json"):
                path = SERIES / "runs" / run_id / name
                sources.append((path, path.relative_to(submit.REPO).as_posix()))

        by_run, shared_sources = submit.partition_delta_sources(sources)

        self.assertEqual([member for _, member in shared_sources], [shared.relative_to(submit.REPO).as_posix()])
        self.assertEqual(set(by_run), set(submit.DELTA_RUN_IDS))
        for run_id, group in by_run.items():
            self.assertEqual({Path(member).name for _, member in group}, {"raw.csv", "result.json"})


if __name__ == "__main__":
    unittest.main()
