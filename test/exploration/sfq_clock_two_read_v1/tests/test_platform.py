from __future__ import annotations

import contextlib
import base64
import csv
import importlib.util
import io
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sfq_clock_platform", SERIES / "scripts" / "platform.py"
)
assert SPEC and SPEC.loader
platform = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = platform
SPEC.loader.exec_module(platform)


def configured(**changes: str) -> dict[str, str]:
    values, _ = platform.read_config()
    values.update(changes)
    return values


class PlatformConfigTests(unittest.TestCase):
    def test_default_80_68_configuration(self):
        values, _ = platform.read_config()
        checked = platform.validate_config(values)
        self.assertEqual(checked["read_starts_ps"], ["110", "190", "270"])
        self.assertEqual(checked["clock_pwl_starts_ps"], ["178", "258", "338"])
        self.assertEqual(checked["amplitudes"]["SE_READ_AMPLITUDE"], "375u")
        self.assertEqual(values["PROTOCOL"], "V9_SHARED_ROW_SE_BL")

    def test_one_by_one_and_eleven_by_thirteen_render(self):
        one = platform.build_case(configured(A="1", B="1", CASE_NAME="TEST_1X1"))
        self.assertEqual(one["checked"]["row_bits_R1_lsb_first"], "1000")
        self.assertEqual(one["checked"]["column_bits_C1_msb_first"], "0001")
        self.assertEqual(one["topology_qa"]["stimulus"]["source_count"], 20)
        self.assertEqual(one["probes"], list(platform.DEFAULT_PROBES))
        self.assertEqual(len(one["probes"]), 8)

        eleven = platform.build_case(configured(A="11", B="13", CASE_NAME="TEST_11X13"))
        self.assertEqual(eleven["checked"]["row_bits_R1_lsb_first"], "1101")
        self.assertEqual(eleven["checked"]["column_bits_C1_msb_first"], "1101")
        self.assertEqual(eleven["checked"]["read_starts_ps"], ["110", "190", "270"])
        self.assertEqual(eleven["checked"]["clock_pwl_starts_ps"], ["178", "258", "338"])

    def test_se_amplitude_is_rendered_from_config(self):
        ctx = platform.build_case(configured(SE_READ_AMPLITUDE="360u"))
        self.assertIn("360u", ctx["stimulus"])
        self.assertNotEqual(ctx["config"]["SE_READ_AMPLITUDE"], "375u")
        self.assertTrue(ctx["topology_qa"]["stimulus"]["configuration_matches_generated_pwl"])

    def test_invalid_protocol_cannot_fall_back(self):
        values = configured(PROTOCOL="LEGACY_WL_PLUS_SE")
        with self.assertRaisesRegex(platform.PlatformError, "legacy WL\\+SE mode"):
            platform.validate_config(values)

    def test_custom_probes_are_exactly_additive_and_resolved(self):
        values = configured(
            CASE_NAME="TEST_CUSTOM",
            PROBE_PROFILE="CUSTOM",
            CUSTOM_PROBES_FILE="tests/fixtures/custom_probes_sample.txt",
        )
        ctx = platform.build_case(values)
        self.assertEqual(len(ctx["probes"]), 10)
        self.assertEqual(ctx["probes"][:8], list(platform.DEFAULT_PROBES))
        self.assertEqual(ctx["probes"][8:], ["V(CLK_D0)", "P(B_JM1|XBVM_R1C1)"])
        self.assertEqual(
            [line.split(None, 1)[1] for line in ctx["deck"].splitlines()
             if line.lower().startswith(".print ")],
            ctx["probes"],
        )

    def test_unknown_custom_probe_is_rejected_before_solver(self):
        tests_dir = SERIES / "tests"
        tests_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tests_dir) as temp:
            probe_file = Path(temp) / "bad_probe.txt"
            probe_file.write_text("V(NODE_THAT_DOES_NOT_EXIST)\n", encoding="utf-8")
            rel = probe_file.relative_to(SERIES).as_posix()
            values = configured(
                CASE_NAME="TEST_BAD_PROBE",
                PROBE_PROFILE="CUSTOM",
                CUSTOM_PROBES_FILE=rel,
            )
            with self.assertRaisesRegex(platform.PlatformError, "unknown top-level node"):
                platform.build_case(values)

    def test_dry_run_never_calls_subprocess_or_creates_run(self):
        before = {p.name for p in (SERIES / "runs").iterdir() if p.is_dir()}
        stdout = io.StringIO()
        with patch.object(platform.subprocess, "run", side_effect=AssertionError("subprocess called")):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(platform.main(["--dry-run"]), 0)
        self.assertIn("solver_invoked=false", stdout.getvalue())
        after = {p.name for p in (SERIES / "runs").iterdir() if p.is_dir()}
        self.assertEqual(before, after)

    def test_unavailable_drive_target_stops_before_any_solver_command(self):
        ctx = platform.build_case(configured(CASE_NAME="TEST_DRIVE_BLOCKED"))
        _, config_bytes = platform.read_config()
        index_path = SERIES / "runs" / "run_index.json"
        index_before = index_path.read_bytes()
        with patch.object(platform, "_drive_write_probe", return_value=(False, "test blocked")):
            with patch.object(platform.subprocess, "run", side_effect=AssertionError("solver invoked")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(platform.execute(ctx, config_bytes), 2)
        self.assertEqual(index_path.read_bytes(), index_before)

    def test_drive_write_probe_only_leaves_no_file_in_temporary_target(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            ok, message = platform._drive_write_probe(target)
            self.assertTrue(ok, message)
            self.assertEqual(list(target.iterdir()), [])


class TopologyAndStimulusTests(unittest.TestCase):
    def test_rendered_circuit_body_matches_v9_actual_deck_except_probe_and_tran(self):
        reference = SERIES / "final_runs" / "V9_analysis" / "deck.cir"
        template = SERIES / "template" / "deck_v9_shared_row_se_bl.cir"
        self.assertTrue(
            platform._normalized_body(reference.read_text(encoding="utf-8"))
            == platform._normalized_body(template.read_text(encoding="utf-8")),
            "template circuit body differs from the V9 actual deck",
        )
        ctx = platform.build_case(configured(A="11", B="13"))
        self.assertTrue(
            platform._normalized_body(reference.read_text(encoding="utf-8"))
            == platform._normalized_body(ctx["deck"]),
            "rendered circuit body differs from the V9 actual deck",
        )

    def test_all_frozen_sources_are_byte_identical_to_v9_and_v10(self):
        manifest = json.loads(
            (SERIES / "template" / "source_manifest.json").read_text(encoding="utf-8")
        )
        for row in manifest["source_closure"]:
            copied = SERIES / "template" / "sources_frozen" / row["file"]
            v9 = SERIES / "final_runs" / "V9_analysis" / "sources_frozen" / row["file"]
            v10 = SERIES / "final_runs" / "V10_analysis" / "sources_frozen" / row["file"]
            self.assertEqual(platform.sha256_file(copied), row["sha256"])
            self.assertEqual(platform.sha256_file(copied), platform.sha256_file(v9))
            self.assertEqual(platform.sha256_file(copied), platform.sha256_file(v10))
        bvm = (
            SERIES / "template" / "sources_frozen" / "01_bvm_cell_0923.cir"
        ).read_text(encoding="utf-8")
        self.assertRegex(bvm, r"(?m)^\s*B_SE\s+SE\s+SE_IN\s+jjmit")
        self.assertRegex(bvm, r"(?m)^\s*R_BSE\s+SE\s+SE_IN\s+")

    def test_v10_template_is_not_used_as_v9_topology_authority(self):
        v9 = (SERIES / "final_runs" / "V9_analysis" / "deck.cir").read_text(encoding="utf-8")
        v10 = (SERIES / "final_runs" / "V10_analysis" / "deck.template.cir").read_text(encoding="utf-8")
        v9_bvm = next(line for line in v9.splitlines() if line.startswith("XBVM_R1C1 "))
        v10_bvm = next(line for line in v10.splitlines() if line.startswith("XBVM_R1C1 "))
        self.assertIn("SE_R1 ", v9_bvm)
        self.assertIn("SE_R1C1 ", v10_bvm)
        v9_d4 = len(re.findall(r"(?m)^XSJTL_CARRY_D4(?:_S\d+)?\s", v9))
        v10_d4 = len(re.findall(r"(?m)^XSJTL_CARRY_D4(?:_S\d+)?\s", v10))
        self.assertEqual((v9_d4, v10_d4), (2, 1))

    def test_stimulus_names_and_read_gating(self):
        config = configured(A="11", B="13")
        checked = platform.validate_config(config)
        stimulus, _ = platform._generate_stimulus(config, checked)
        qa = platform.validate_stimulus(config, checked, stimulus)
        self.assertEqual(qa["source_counts"], {"WL": 4, "BL": 4, "SE": 4, "CLK": 8})
        self.assertNotIn("product=", stimulus)
        self.assertEqual(len(platform._source_lines(stimulus)), 20)


class ArtifactAndArchiveTests(unittest.TestCase):
    def test_raw_basic_integrity_checks_only_schema_and_time(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "raw.csv"
            raw.write_text(
                "time," + ",".join(platform.DEFAULT_PROBES) + "\n"
                "0," + ",".join("0" for _ in platform.DEFAULT_PROBES) + "\n"
                "0.01," + ",".join("0" for _ in platform.DEFAULT_PROBES) + "\n",
                encoding="utf-8",
            )
            qa = platform._raw_integrity(raw, list(platform.DEFAULT_PROBES))
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["sample_count"], 2)
            raw.write_text(
                "time," + ",".join(platform.DEFAULT_PROBES) + "\n"
                "0," + ",".join("0" for _ in platform.DEFAULT_PROBES) + "\n"
                "0," + ",".join("0" for _ in platform.DEFAULT_PROBES) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(platform.PlatformError, "strictly increasing"):
                platform._raw_integrity(raw, list(platform.DEFAULT_PROBES))

    def test_run_ids_advance_and_do_not_reuse_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            (runs / "run_index.json").write_text(json.dumps({
                "schema": "sfq-clock-two-read-run-index-v1",
                "historical_id_floor": 0,
                "next_sequence": 1,
                "reserved": [],
            }), encoding="utf-8")
            first, first_dir = platform._reserve_run_id("CASE", runs)
            second, _ = platform._reserve_run_id("CASE", runs)
            self.assertEqual(first, "V9R001_CASE")
            self.assertEqual(second, "V9R002_CASE")
            self.assertTrue(first_dir.is_dir())

    def test_archive_integrity_in_temporary_folder_not_drive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "runs" / "V9R001_TEST"
            run.mkdir(parents=True)
            (run / "sources_frozen").mkdir()
            (run / "manifest.json").write_text(json.dumps({
                "run_id": "V9R001_TEST",
                "case_name": "TEST",
            }), encoding="utf-8")
            (run / "deck.cir").write_text(".tran 0.01p 400p\n", encoding="utf-8")
            (run / "stimulus.inc").write_text("* synthetic only\n", encoding="utf-8")
            (run / "USER_CASE.snapshot.env").write_text("A=1\n", encoding="utf-8")
            (run / "PREFLIGHT.md").write_text("synthetic archive test\n", encoding="utf-8")
            (run / "probe_manifest.json").write_text("{}\n", encoding="utf-8")
            (run / "raw.csv").write_text(
                "time," + ",".join(platform.DEFAULT_PROBES) + "\n"
                "0," + ",".join("0" for _ in platform.DEFAULT_PROBES) + "\n",
                encoding="utf-8",
            )
            (run / "run.log").write_text("synthetic only; no JoSIM\n", encoding="utf-8")
            (run / "res.html").write_text("<html><script>standalone</script></html>\n", encoding="utf-8")
            (run / "sources_frozen" / "example.cir").write_text("synthetic\n", encoding="utf-8")
            target = root / "drivefs-test"
            target.mkdir()
            result = platform.create_archive(run, target, folder_id="TEST_FOLDER")
            self.assertTrue(result["crc_verified"])
            self.assertTrue(result["member_sha256_verified"])
            self.assertEqual(result["status"], "DRIVEFS_PATH_SHA_VERIFIED_CLOUD_SYNC_UNCONFIRMED")
            archives = list(target.glob("*.zip"))
            self.assertEqual(len(archives), 1)
            with zipfile.ZipFile(archives[0]) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertTrue(any(name.endswith("/raw.csv") for name in names))
                self.assertTrue(any(name.endswith("/res.html") for name in names))
                self.assertTrue(any(name.endswith("/ARCHIVE_MANIFEST.json") for name in names))
            with self.assertRaisesRegex(platform.PlatformError, "refusing to overwrite"):
                platform.create_archive(run, target, folder_id="TEST_FOLDER")

    def test_classic_plot_keeps_synthetic_short_pulse_and_is_standalone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "synthetic.csv"
            headers = ["time", *platform.DEFAULT_PROBES]
            rows = []
            for index, t in enumerate((0.0, 0.01, 0.02, 0.03, 0.04)):
                values = [0.0] * len(platform.DEFAULT_PROBES)
                if index == 2:
                    values[0] = 0.123456789
                rows.append([t, *values])
            with raw.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerows(rows)
            html = root / "res.html"
            cmd = [
                sys.executable, str(platform.PLOTTER), str(raw),
                "-t", "stacked", "-c", "dark", "-j", "2pi",
                "-s", *platform.DEFAULT_PROBES, "-x", str(html),
            ]
            result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            body = html.read_text(encoding="utf-8", errors="replace")
            for probe in platform.DEFAULT_PROBES:
                self.assertIn(probe, body)
            self.assertNotRegex(body, r"(?is)<script\b[^>]*\bsrc\s*=")
            # Plotly 3 serializes numeric arrays as base64 typed arrays. Decode the
            # first trace's Y values and verify the one-row synthetic pulse survived.
            tail = body.split('"name":"V(S_D0_OUT)"', 1)[1]
            arrays = re.findall(r'"bdata":"([^"\\]*(?:\\.[^"\\]*)*)"', tail[:1200])
            self.assertGreaterEqual(len(arrays), 2, "first trace X/Y arrays not found in HTML")
            y_b64 = arrays[1].replace(r"\u002f", "/")
            y_values = struct.unpack("<5d", base64.b64decode(y_b64))
            self.assertEqual(y_values[2], 0.123456789)


if __name__ == "__main__":
    unittest.main()
