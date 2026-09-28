from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

from components import (SNAPSHOT_NAMES, load_reference, render_components,
                        verify_reference_sources)  # noqa: E402
from config import COMPONENT_KEYS, ConfigError, USER_CASE_KEYS, load_env  # noqa: E402
from topology import SOURCE_FILES  # noqa: E402
from config import load_user_case_snapshot  # noqa: E402
from run_case import render_case  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_netlist_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("*")]


class ComponentRenderTests(unittest.TestCase):
    def setUp(self):
        self.values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
        reference = load_reference()
        self.values.update({key: reference[key] for key in COMPONENT_KEYS})
        self.values.update({
            "NAME": "component_render_fixture", "ARRAY_SIZE": "2",
            "MASKS": "00,01,10,11", "QB_CB": "0,1", "SJTL_COUNT": "13,2",
            "POST_SJTL_CB": "1,0", "OUTPUT_MODE": "TERMINAL", "TERM_R": "2",
            "DT": "0.01p", "STOP": "200p",
        })
        self.source_hashes = {role: digest(REPO / path) for role, path in SOURCE_FILES.items()}

    def render(self, root: Path, values: dict[str, str] | None = None):
        return render_components(values or self.values, root / "snapshot" / "sources")

    def test_default_snapshots_are_electrically_exact_and_source_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources, records = self.render(Path(tmp))
            for role, relative in SOURCE_FILES.items():
                self.assertEqual(sources[role].read_bytes(), (REPO / relative).read_bytes())
                record = next(item for item in records if item["role"] == role)
                self.assertEqual(record["canonical_source_sha256"], self.source_hashes[role])
                self.assertEqual(record["rendered_snapshot_sha256"], digest(sources[role]))
                self.assertTrue(record["rendered_snapshot_path"].endswith(SNAPSHOT_NAMES[role]))
            shared_model = (
                ".model jjmit jj(rtype=1, vg=2.8mV, cap=0.07pF, "
                "r0=160, rN=16, icrit=0.1mA)"
            )
            for role in ("QB", "CB", "SJTL"):
                self.assertIn(shared_model, sources[role].read_text())
        self.assertEqual({role: digest(REPO / path) for role, path in SOURCE_FILES.items()},
                         self.source_hashes)

    def test_0928_sources_freeze_a030_working_electrical_body_without_copying_other_roles(self):
        self.assertEqual(SOURCE_FILES["BVM"], Path("circuits/bvm/bvm_cell_0923.cir"))
        self.assertEqual(SOURCE_FILES["QB"], Path("circuits/qb/BQ_0928.cir"))
        self.assertEqual(SOURCE_FILES["CB"], Path("circuits/CB/CB_0928.cir"))
        self.assertEqual(SOURCE_FILES["SJTL"], Path("circuits/sJTL_0923.cir"))
        a030 = SERIES / "runs" / "A030_T010_M1111" / "snapshot" / "sources"
        with tempfile.TemporaryDirectory() as tmp:
            values = load_user_case_snapshot(SERIES / "runs" / "A030_T010_M1111" /
                                             "USER_CASE.snapshot.env")
            rendered, _ = self.render(Path(tmp), values)
            for role, filename in (("QB", "BQ_tunable.cir"), ("CB", "CB_tunable.cir")):
                self.assertEqual(active_netlist_lines(rendered[role]),
                                 active_netlist_lines(a030 / filename))
        self.assertEqual((REPO / SOURCE_FILES["BVM"]).read_bytes(),
                         (a030 / "bvm_tunable.cir").read_bytes())
        self.assertEqual((REPO / SOURCE_FILES["SJTL"]).read_bytes(),
                         (a030 / "sJTL_tunable.cir").read_bytes())
        self.assertNotEqual(SOURCE_FILES["QB"], Path("circuits/qb/BQ_0923.cir"))
        self.assertNotEqual(SOURCE_FILES["CB"], Path("circuits/CB/CB_0923.cir"))

    def test_qb_area_override_changes_only_the_selected_junction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline, _ = self.render(root / "baseline")
            changed_values = dict(self.values, QB_BJ3_AREA="2.2")
            changed, _ = self.render(root / "changed", changed_values)
            before = (REPO / SOURCE_FILES["QB"]).read_text().splitlines()
            after = changed["QB"].read_text().splitlines()
            differences = [(left, right) for left, right in zip(before, after) if left != right]
            self.assertEqual(len(differences), 1)
            self.assertEqual(differences[0][0].split()[0], "BJ3")
            self.assertIn("area=2.2", differences[0][1])
            for role in ("BVM", "CB", "SJTL"):
                self.assertEqual(baseline[role].read_bytes(), changed[role].read_bytes())

    def test_open_and_numeric_resistor_branches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline, _ = self.render(root / "baseline", dict(self.values, CB_RJ2="OPEN"))
            bvm_open = baseline["BVM"].read_text()
            cb_open = baseline["CB"].read_text()
            self.assertRegex(bvm_open, r"(?m)^\* R_JM2\s+3\s+4\s+8$")
            self.assertRegex(cb_open, r"(?m)^\* RJ2\s+2\s+3\s+6$")

            bvm_active, _ = self.render(root / "bvm-active", dict(self.values, BVM_RJM2="8"))
            cb_active, _ = self.render(root / "cb-active", dict(self.values, CB_RJ2="14"))
            self.assertRegex(bvm_active["BVM"].read_text(), r"(?m)^R_JM2\s+3\s+4\s+8$")
            self.assertRegex(cb_active["CB"].read_text(), r"(?m)^RJ2\s+2\s+3\s+14$")

    def test_open_output_resistor_removes_its_probe_without_invalidating_the_render(self):
        values = dict(self.values, BVM_RSL="OPEN")
        stimulus = load_stimulus(SERIES / "STIMULUS.env")
        with tempfile.TemporaryDirectory() as tmp:
            result = render_case(values, stimulus, "00", Path(tmp) / "case", fixture_only=True)
            self.assertEqual(result["status"], "RENDER_FIXTURE_ONLY")
            probes = result["probe_manifest"]["signals"]
            self.assertFalse(any(item["label"] == "I(R_SL|XBVM1)" for item in probes))

    def test_bias_pwl_and_sjtl_overrides_render(self):
        values = dict(self.values, QB_IB="270u", QB_BIAS_RISE="6p",
                      CB_IB="210u", CB_BIAS_RISE="7p", SJTL_L1="3p",
                      SJTL_IB="205u", SJTL_BIAS_RISE="8p")
        with tempfile.TemporaryDirectory() as tmp:
            sources, _ = self.render(Path(tmp), values)
            self.assertIn("pwl(0 0 6p 270u)", sources["QB"].read_text())
            self.assertIn("pwl(0 0 7p 210u)", sources["CB"].read_text())
            sjtl = sources["SJTL"].read_text()
            self.assertRegex(sjtl, r"(?m)^L1 IN 1 3p$")
            self.assertIn("pwl(0 0 8p 205u)", sjtl)

    def test_core_and_debug_profiles_render_without_circuit_or_source_changes(self):
        historical = SERIES / "runs" / "A025_T006_M1111" / "USER_CASE.snapshot.env"
        values = load_user_case_snapshot(historical)
        self.assertEqual(values["PROBE_PROFILE"], "debug")
        values["PROBE_PROFILE"] = "core"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stimulus = load_stimulus(SERIES / "STIMULUS.env")
            core_result = render_case(values, stimulus, "1111", root / "core", fixture_only=True)
            debug_values = dict(values, PROBE_PROFILE="debug")
            debug_result = render_case(debug_values, stimulus, "1111", root / "debug", fixture_only=True)
            core_deck = (root / "core" / "actual_deck.cir").read_text()
            debug_deck = (root / "debug" / "actual_deck.cir").read_text()
            for source in SOURCE_FILES:
                self.assertEqual(core_result["source_manifest"]["sources"]
                                 [list(SOURCE_FILES).index(source)]["rendered_snapshot_sha256"],
                                 debug_result["source_manifest"]["sources"]
                                 [list(SOURCE_FILES).index(source)]["rendered_snapshot_sha256"])
            self.assertIn("PROBE_PROFILE=core", (root / "core" / "USER_CASE.snapshot.env").read_text())
            core_probe = core_result["probe_manifest"]
            debug_probe = debug_result["probe_manifest"]
            old_probe = json.loads((SERIES / "runs" / "A025_T006_M1111" / "probe_manifest.json").read_text())
            self.assertEqual(core_probe["profile"], "core")
            self.assertEqual(debug_probe["profile"], "debug")
            self.assertEqual({item["label"] for item in debug_probe["signals"]},
                             {item["label"] for item in old_probe["signals"]})
            self.assertLess(core_probe["signal_count"], debug_probe["signal_count"])
            strip_prints = lambda deck: "\n".join(
                line for line in deck.splitlines() if not line.startswith(".print ")
            )
            self.assertEqual(strip_prints(core_deck), strip_prints(debug_deck))

    def test_changed_canonical_hash_hard_stops_for_human_reference_review(self):
        reference = load_reference()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in SOURCE_FILES.values():
                source = REPO / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            changed = root / SOURCE_FILES["QB"]
            changed.write_bytes(changed.read_bytes() + b"* unreviewed local edit\n")
            with self.assertRaisesRegex(ConfigError, "REFERENCE_SOURCE_CHANGED"):
                verify_reference_sources(reference, root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
