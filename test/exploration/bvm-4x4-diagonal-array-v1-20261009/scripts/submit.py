#!/usr/bin/env python3
"""Scoped source/package/push workflow for the new 4x4 diagonal experiment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
HANDOFF = SERIES / "handoff"
MIRROR_DEFAULT = Path("/mnt/d/BVM_Backages")
ROOT_SUBMIT_PATH = REPO / "scripts" / "submit.py"
BUS400_PARENT_HEAD = "3de08ba0fd5997b253269849dbc1a535786c8fd6"
BUS400_RUN_IDS = ("A007_BUS400_D3_N0", "A008_BUS400_D3_N1")
A009_RUN_IDS = ("A009_paper_like",)
BUS400_DELTA_NAME = f"{SERIES.name}_delta_BVM4X4_BUS400_20261009.zip"
BUS400_DELTA_SHA256 = "2c7747d5fcff639985880af4c8c6cc4e9f54bd0ecfbac95daa4787dbc58e1bf1"
BUS400_DELTA_HEAD = "9e1070f85b3e7fcfdc1357f3e9e7bf64f834a29d"
A009_DELTA_NAME = f"{SERIES.name}_delta_A009_RESPONSIVE_20261009.zip"
A009_DELTA_SHA256 = "a852fa8453ca5d7315767958a96c35dce3465956e1b8a964035af4bc071a2a91"
A009_DELTA_HEAD = "617311779e996494194ef1aa9bb172295158ea81"
A010_A012_TAG = "A010_A012_20261009"
A010_A012_SOURCE_NAME = f"{SERIES.name}_delta_{A010_A012_TAG}_source.zip"
A010_A012_SOURCE_SHA256 = "a1d8871e8e015e1c58608582c57097233780baf90462e1db8459741dcc966ba9"
A010_A012_SOURCE_HEAD = "a2a9e6211975454c12f1f17d7c94446a37d1a06c"
A010_A012_RUN_PACKAGES = {
    "A010_PAPER_1101_1101": ("f4d2c24862629f9579912e2e12098d42ab9933de5793d1a60aeabcf3464c3e55",
                             "12e875f8dff37bdb3c94555a71ed3ef2f87cf986973e24d48b927a88433a3cb8"),
    "A011_PAPER_1101_1101": ("0a9ae3386fd2cb66c5ee2b6edc547e9c5ec0af36ba8e3091d356ef3d82bdca15",
                             "2e961bbabc5b1db35a6a97d4fa4ed409df8b706688d877fc1bc2f4a3ae1f961e"),
    "A012_PAPER_1101_1101": ("960e1325dbcf89331425a482cd78b1f83341922532cf72ac61efe2e5ee3f1d30",
                             "b5d96f8191506ccce430396458d1dbb7313e9860c39d4984c472b3a34e9a4f0a"),
}
A010_A012_RUN_IDS = tuple(A010_A012_RUN_PACKAGES)
T1_A013_A016_TAG = "T1_7WAY_20261009"
T1_A013_A016_SOURCE_NAME = f"{SERIES.name}_delta_{T1_A013_A016_TAG}_source.zip"
T1_A013_A016_SOURCE_SHA256 = "2e18febe15b39a926484cf53bd4242ac51d261710ef41c2543f4fc656411af2e"
T1_A013_A016_SOURCE_HEAD = "1c2e2e913c690cc613b2f232d3877e7c1b0b58cb"
T1_A013_A016_RUN_PACKAGES = {
    "A013_T1_ALL_QUIET": ("541fe5d9e5fbc86bf91cd49ccd52ade34af08e49e376c2528d0e157439ea96cb",
                          "447bc455892109221a8931a02de4e846f5ae764824a343bce9e2918e02c5153f"),
    "A014_T1_ALL_CLOCK": ("65aed4d7f05f24df9fe9a2cb813ff66027ccacd2f58db0f42e65aa0a901be0ae",
                          "fade41f8071be1db53ad5ba9299c6274dbaf69b2b40d24d37af3c07b59782f03"),
    "A015_T1_PAPER_QUIET": ("199ef479f85863617385e69e2d497a71d7f53f0e8603792fa7f2988c01b2caa8",
                            "6d0d63b72aa12332fd2d2f53313b2f244f78013ffbd0d50740b6bd2c9905c0df"),
    "A016_T1_PAPER_CLOCK": ("210ac40931a721e1d9c3c443613737f3572e46fc778988637373edb5f6db8b6c",
                            "a7a4c9d87c07bc6fc02e66090dc64168e88c80c9d937824842210c785b8cc864"),
}
T1_A013_A016_RUN_IDS = tuple(T1_A013_A016_RUN_PACKAGES)
DELTA_BASE_COMMIT = "684531519dda6e0a1e8ffec24d0711ee08adf6d1"
DELTA_BASE_PACKAGE_NAME = T1_A013_A016_SOURCE_NAME
DELTA_BASE_PACKAGE_SHA256 = T1_A013_A016_SOURCE_SHA256
DELTA_BASE_PACKAGE_SOURCE_HEAD = T1_A013_A016_SOURCE_HEAD
PREVIOUS_DELTA_RUN_IDS = T1_A013_A016_RUN_IDS
DELTA_RUN_IDS = ("A017_PAPER_1101_1101", "A018_T1_ALL_QUIET", "A019_T1_ALL_PLUSE")
INVALID_PRESERVED_DELTA_RUN_IDS = {"A017_PAPER_1101_1101"}
T1_CHAIN_BASE_COMMIT = "64b4e18e2d944fd982f5b200490f7b7575339b46"
T1_CHAIN_BASE_SOURCE_NAME = f"{SERIES.name}_delta_T1_A017_A019_20261009_source.zip"
T1_CHAIN_BASE_SOURCE_SHA256 = "0a6274c3fb28bb9cafab41336b542daf25cd37e6adad5c4871c0050a9f4dcd2a"
T1_CHAIN_BASE_SOURCE_HEAD = "d6104470e2159baa0a7ce8da748f7e4acd340600"
T1_CHAIN_BASE_RUN_PACKAGES = {
    "A017_PAPER_1101_1101": ("8b819f531cb0a1837d30c2acddba40da72dc5e5ee015ede29ff01b20286c9273",
                              "59e4ae993860061735cf6b78319512fe3d3cb20d1e8359fa89f32d12047c4023", "INVALID"),
    "A018_T1_ALL_QUIET": ("6179a2f75afb8001782275f78080c5155046b1b6cfc5188fe0062ac6dbd3d2c9",
                          "9a17cfe79805b16c7977aa23a766be9e2a7101a5553da6162f26d4a141123a1f", "VALID"),
    "A019_T1_ALL_PLUSE": ("c80a149449b14c3c9e4d6df699cbc40162205fce5358a2b9af644850b4b464cf",
                          "3cabda93970826369616d1749cb242f6e9a59576b49e55822126c2fb81212ecf", "VALID"),
}
T1_CHAIN_BASE_RUN_IDS = tuple(T1_CHAIN_BASE_RUN_PACKAGES)
T1_CHAIN_DELTA_RUN_IDS = ("A020_CHAIN_ALL_QUIET", "A021_CHAIN_ALL_GLOBAL_CLOCK",
                          "A022_CHAIN_PAPER_GLOBAL_CLOCK")
CB_DIRECT_D1_BASE_COMMIT = "6364256321eb7c7437ef20ec14a3ba604e7b4d15"
CB_DIRECT_D1_BASE_SOURCE_NAME = f"{SERIES.name}_delta_T1_CHAIN_A020_A022_20261009_source.zip"
CB_DIRECT_D1_BASE_SOURCE_SHA256 = "52425d327a7d0b58a9e664f19eb95658b16aaca385321b651bb6153c751aef5c"
CB_DIRECT_D1_BASE_RUN_PACKAGES = {
    "A020_CHAIN_ALL_QUIET": ("bf978aa2e9061dc7cbe5eabfe8643a494dd09dc37d4416b519408d4dd01d22e6",
                              "ab13d65c671065fbfcd628ff7e4ffc0a9dc0506105bcd2a5bdefd91488aa763d"),
    "A021_CHAIN_ALL_GLOBAL_CLOCK": ("21477be494024eb224c2fd4aec919638ab85fc03bf4cc80396d92aa127533f12",
                                    "85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e"),
    "A022_CHAIN_PAPER_GLOBAL_CLOCK": ("8e18c88bf37d327b3d8e7064fc9b62a2d4a2f783dbc46c9234b45e08fec0cfb8",
                                      "2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb"),
}
CB_DIRECT_D1_BASE_METADATA_NAME = f"{SERIES.name}_delta_T1_CHAIN_A020_A022_20261009_runs_metadata.zip"
CB_DIRECT_D1_BASE_METADATA_SHA256 = "5f4132cb8ff7a702a52caa77704866551b6ee7cedbf5d77d9f0a472951e8bdc6"
CB_DIRECT_D1_RUN_IDS = ("A023_CB_DIRECT_D1_ALL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK")
CB_DIRECT_D1_BASE_PACKAGE_GROUPS = (
    ("source", CB_DIRECT_D1_BASE_SOURCE_NAME, CB_DIRECT_D1_BASE_SOURCE_SHA256),
    ("runs_metadata", CB_DIRECT_D1_BASE_METADATA_NAME, CB_DIRECT_D1_BASE_METADATA_SHA256),
    ("A020_CHAIN_ALL_QUIET_raw",
     f"{SERIES.name}_delta_T1_CHAIN_A020_A022_20261009_A020_CHAIN_ALL_QUIET_raw.zip",
     CB_DIRECT_D1_BASE_RUN_PACKAGES["A020_CHAIN_ALL_QUIET"][0]),
    ("A021_CHAIN_ALL_GLOBAL_CLOCK_raw",
     f"{SERIES.name}_delta_T1_CHAIN_A020_A022_20261009_A021_CHAIN_ALL_GLOBAL_CLOCK_raw.zip",
     CB_DIRECT_D1_BASE_RUN_PACKAGES["A021_CHAIN_ALL_GLOBAL_CLOCK"][0]),
    ("A022_CHAIN_PAPER_GLOBAL_CLOCK_raw",
     f"{SERIES.name}_delta_T1_CHAIN_A020_A022_20261009_A022_CHAIN_PAPER_GLOBAL_CLOCK_raw.zip",
     CB_DIRECT_D1_BASE_RUN_PACKAGES["A022_CHAIN_PAPER_GLOBAL_CLOCK"][0]),
)
CB_CARRY_BUFFER_D1_BASE_COMMIT = "e0155de0c19e95d8c909550c67097db65695c842"
CB_CARRY_BUFFER_D1_BASE_SOURCE_HEAD = "0d7095fc395f464b7ec797ef2963afb652fe04c8"
CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME = f"{SERIES.name}_delta_CB_DIRECT_D1_20261009_source.zip"
CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256 = "e2838461d7dd5f4ed0b6478abf39e80ff1741e87484b0637dec67c3b7ce23a51"
CB_CARRY_BUFFER_D1_BASE_PACKAGES = (
    ("source", CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME, CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256),
    ("runs_metadata", f"{SERIES.name}_delta_CB_DIRECT_D1_20261009_runs_metadata.zip",
     "882b3266d2d641cecc0f9b3008517547f245a147675ff6d8fe8c6193bde8e54a"),
    ("A023_CB_DIRECT_D1_ALL_CLOCK_raw",
     f"{SERIES.name}_delta_CB_DIRECT_D1_20261009_A023_CB_DIRECT_D1_ALL_CLOCK_raw.zip",
     "87212488292ac5d0dd1f82ca4c6620e57fedcd99a8b93db8f4bddf705ec7b768"),
    ("A024_CB_DIRECT_D1_PAPER_CLOCK_raw",
     f"{SERIES.name}_delta_CB_DIRECT_D1_20261009_A024_CB_DIRECT_D1_PAPER_CLOCK_raw.zip",
     "efce60315ad48c53afd13f253f6164c755143b9f81660316dcf064d83b84876b"),
)
CB_CARRY_BUFFER_D1_RUN_IDS = ("A025_CARRY_CB_D1_ALL_CLOCK", "A026_CARRY_CB_D1_PAPER_CLOCK")
CB_CARRY_BUFFER_D1_TASK = SERIES / "analysis" / "cb-carry-buffer-d1-20261009"
LEGACY_RUN_IDS = tuple(f"A{i:03d}_{case}" for i, case in enumerate(
    ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4", "PAPER_1101_1101"), start=1))
BASE_METADATA_NAME = f"{SERIES.name}_metadata_v2_BVM4X4_20261009.zip"
BASE_METADATA_QA = HANDOFF / f"{Path(BASE_METADATA_NAME).stem}_PACKAGE_QA.json"
BASE_METADATA_SHA256 = "19af77800333d2c596b25606c26ac84fbd0ae4101b5b14f83fefc121c5975be1"
BASE_METADATA_SOURCE_COMMIT = "364dd2b6dc0589f1ca1de614a16583a32331a51d"
BASE_RUN_PACKAGE_SHA256 = {
    "A001_D3_N0": "a720b89bfc318937c22e8c456cad80000b5aa47527d1470e4577b2413c851585",
    "A002_D3_N1": "8e3d18c8ca9d24c4c88a2cd7bb34826154a2556d8d4b034a81d3bdf78c7ee063",
    "A003_D3_N2": "a41e44a10b6021560a329047490b2b79b18a2f49d5d6bef145d81b46bba8a306",
    "A004_D3_N3": "b8af1acc2241e56c77374734336f49719f1e476717c5b1337592c1409bb874f9",
    "A005_D3_N4": "83e7d33b8ea44af3e80a7254596a93bf2b73ce51315add066a3f14a8dde1ec4d",
    "A006_PAPER_1101_1101": "c3cd4bd7477b3b5b43b78313a9392808d78da9949d3a8feb593ca72bfbf28c46",
}
BASE_RUN_RAW_SHA256 = {
    "A001_D3_N0": "af13bc5105c12919b7d93817d21ebd4a3f31123fb18f1e1d39b6a90958199c4d",
    "A002_D3_N1": "f977347a31d24a932262d2a87a145d344b96b56393bce99ebf592cf6dd7a2be2",
    "A003_D3_N2": "62301133c8faa92e078032270091920710ff361ba052450c4c006092308e9ec4",
    "A004_D3_N3": "79357f4a5401f11cae7fc5ec1ba496b81a30fec24c6d426982f42c6fcbb56908",
    "A005_D3_N4": "3b8cb325ed025ae83c3be83226284473357d5e7ec3a472dda6c75fcdd4050060",
    "A006_PAPER_1101_1101": "a318d8c09a958886ab1b3ec8ed636bf42c7b46b7fc9055353cff47ae0432b9cc",
}
DELTA_GLOBAL_PATHS = {
    "AGENTS.md", "CLAUDE.md", ".agents/skills/josim-experiment/SKILL.md",
    ".agents/skills/josim-experiment/agents/openai.yaml",
    "docs/EXPERIMENT_CONTRACT.md", "docs/research/EXPERIMENT_WORKFLOW_V1.md",
    "docs/research/COMPACT_WORKFLOW_V2.md", "memory/EXECUTOR_NOW.md",
    "memory/BVM_CURRENT_CONTEXT.md", "memory/LUNA_EXECUTOR_MEMORY.md",
    "memory/skill-usage.md", "scripts/README.md", "scripts/submit.py",
}


def load_root_submit() -> Any:
    spec = importlib.util.spec_from_file_location("josim_root_submit", ROOT_SUBMIT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load repository submit helper: {ROOT_SUBMIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=REPO, text=True,
                          capture_output=True, check=check).stdout.strip()


def included_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(SERIES)
        if (not path.is_file() or path.is_symlink() or "handoff" in relative.parts
                or "__pycache__" in relative.parts or path.suffix.lower() in {".html", ".pyc", ".tmp"}):
            continue
        files.append(path)
    return files


def base_records(root: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify prior package identities from QA sidecars without reopening old raw or ZIP members."""
    metadata = json.loads(BASE_METADATA_QA.read_text(encoding="utf-8"))
    metadata_path = HANDOFF / BASE_METADATA_NAME
    if (metadata.get("status") != "PASS" or metadata.get("package_sha256") != BASE_METADATA_SHA256 or
            metadata.get("source_commit") != BASE_METADATA_SOURCE_COMMIT or
            not metadata_path.is_file() or root.sha256(metadata_path) != BASE_METADATA_SHA256 or
            metadata.get("package_bytes") != metadata_path.stat().st_size):
        raise RuntimeError("bound metadata-v2 base identity/QA does not match the registered checkpoint")
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    recorded_raw = {item.get("run_id"): item.get("raw_sha256") for item in manifest.get("runs", [])}
    records = []
    for run_id in LEGACY_RUN_IDS:
        package_name = f"{SERIES.name}_raw_handoff_{run_id}_BVM4X4_20261009.zip"
        package = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        raw_sha = qa.get("raw_sha256_by_run", {}).get(run_id)
        expected_package_sha = BASE_RUN_PACKAGE_SHA256[run_id]
        expected_raw_sha = BASE_RUN_RAW_SHA256[run_id]
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("package_bytes") != package.stat().st_size or
                root.sha256(package) != expected_package_sha or raw_sha != expected_raw_sha or
                recorded_raw.get(run_id) != expected_raw_sha):
            raise RuntimeError(f"registered legacy package/raw identity mismatch: {run_id}")
        records.append({"run_id": run_id,
                        "raw_path": f"runs/{run_id}/raw.csv",
                        "raw_sha256": expected_raw_sha,
                        "source_package_name": package_name,
                        "source_package_sha256": expected_package_sha})
    return metadata, records


def _excluded_delta_path(path: Path) -> bool:
    parts = path.parts
    return ("handoff" in parts or "plots" in parts or "__pycache__" in parts or
            path.suffix.lower() in {".html", ".pyc", ".tmp"})


def is_allowed_delta_run_path(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    if len(parts) < 6 or parts[:4] != ("test", "exploration", SERIES.name, "runs"):
        return False
    run_id = parts[4]
    if run_id in DELTA_RUN_IDS:
        return True
    return False


def verify_prior_bus400_delta(root: Any, legacy_refs: list[dict[str, Any]]) -> tuple[
        dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    package = HANDOFF / BUS400_DELTA_NAME
    qa_path = HANDOFF / f"{Path(BUS400_DELTA_NAME).stem}_PACKAGE_QA.json"
    qa = root.verify_existing_bundle(package, qa_path)
    if (qa.get("status") != "PASS" or qa.get("package_sha256") != BUS400_DELTA_SHA256 or
            qa.get("source_commit") != BUS400_DELTA_HEAD or
            qa.get("base_package_name") != BASE_METADATA_NAME or
            qa.get("base_package_sha256") != BASE_METADATA_SHA256):
        raise RuntimeError("registered A007/A008 delta package identity or QA mismatch")
    with zipfile.ZipFile(package, "r") as archive:
        prior_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (prior_manifest.get("head_commit") != BUS400_DELTA_HEAD or
            prior_manifest.get("base_package_name") != BASE_METADATA_NAME or
            prior_manifest.get("base_package_sha256") != BASE_METADATA_SHA256):
        raise RuntimeError("registered A007/A008 delta manifest lineage mismatch")
    manifest_raw = prior_manifest.get("raw_sha256_by_run", {})
    if set(manifest_raw) != set(BUS400_RUN_IDS):
        raise RuntimeError("registered A007/A008 delta raw closure is incomplete")
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    added_refs = []
    for run_id in BUS400_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        raw = RUNS / run_id / "raw.csv"
        if (manifest_raw.get(run_id) != result.get("raw_sha256") or
                not manifest_rows.get(run_id) or
                manifest_rows[run_id].get("raw_sha256") != result.get("raw_sha256") or
                root.sha256(raw) != result.get("raw_sha256")):
            raise RuntimeError(f"A007/A008 raw identity no longer matches its delta base: {run_id}")
        added_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256": result["raw_sha256"],
                           "source_package_name": BUS400_DELTA_NAME,
                           "source_package_sha256": BUS400_DELTA_SHA256})
    return qa, prior_manifest, legacy_refs + added_refs


def verify_prior_a009_delta(root: Any, prior_refs: list[dict[str, Any]]) -> tuple[
        dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    expected_prior_refs = list(prior_refs)
    package = HANDOFF / A009_DELTA_NAME
    qa_path = HANDOFF / f"{Path(A009_DELTA_NAME).stem}_PACKAGE_QA.json"
    qa = root.verify_existing_bundle(package, qa_path)
    if (qa.get("status") != "PASS" or qa.get("package_sha256") != A009_DELTA_SHA256 or
            qa.get("source_commit") != A009_DELTA_HEAD or
            qa.get("base_package_name") != BUS400_DELTA_NAME or
            qa.get("base_package_sha256") != BUS400_DELTA_SHA256):
        raise RuntimeError("registered A009 delta package identity or QA mismatch")
    with zipfile.ZipFile(package, "r") as archive:
        prior_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (prior_manifest.get("head_commit") != A009_DELTA_HEAD or
            prior_manifest.get("base_package_name") != BUS400_DELTA_NAME or
            prior_manifest.get("base_package_sha256") != BUS400_DELTA_SHA256):
        raise RuntimeError("registered A009 delta manifest lineage mismatch")
    recorded_prior_refs = prior_manifest.get("referenced_existing_raw_sha256", [])
    prior_identities = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                         item.get("source_package_sha256")) for item in recorded_prior_refs}
    expected_identities = {(item["run_id"], item["raw_sha256"], item["source_package_name"],
                            item["source_package_sha256"]) for item in expected_prior_refs}
    if len(prior_identities) != len(recorded_prior_refs) or prior_identities != expected_identities:
        raise RuntimeError("registered A009 delta existing-raw references are malformed")
    raw_map = prior_manifest.get("raw_sha256_by_run", {})
    if set(raw_map) != set(A009_RUN_IDS):
        raise RuntimeError("registered A009 delta raw closure is incomplete")
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    added_refs = []
    for run_id in A009_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        raw = RUNS / run_id / "raw.csv"
        if (raw_map.get(run_id) != result.get("raw_sha256") or
                not manifest_rows.get(run_id) or
                manifest_rows[run_id].get("raw_sha256") != result.get("raw_sha256") or
                root.sha256(raw) != result.get("raw_sha256")):
            raise RuntimeError(f"A009 raw identity no longer matches its delta base: {run_id}")
        added_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256": result["raw_sha256"],
                           "source_package_name": A009_DELTA_NAME,
                           "source_package_sha256": A009_DELTA_SHA256})
    return qa, prior_manifest, recorded_prior_refs + added_refs


def verify_prior_a010_a012_checkpoint(root: Any, prior_refs: list[dict[str, Any]]) -> tuple[
        list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Verify the complete source + A010/A011/A012 checkpoint without repackaging its raw."""
    expected_prior = {(item["run_id"], item["raw_sha256"], item["source_package_name"],
                       item["source_package_sha256"]) for item in prior_refs}
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    package_items = [("source", A010_A012_SOURCE_NAME, A010_A012_SOURCE_SHA256)]
    for run_id, (package_sha, _raw_sha) in A010_A012_RUN_PACKAGES.items():
        package_items.append((run_id, f"{SERIES.name}_delta_{A010_A012_TAG}_{run_id}.zip", package_sha))

    package_set = []
    combined_hashes: dict[str, str] = {}
    prior_run_refs: list[dict[str, Any]] = []
    for group, package_name, expected_package_sha in package_items:
        package = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = root.verify_existing_bundle(package, qa_path)
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("source_commit") != A010_A012_SOURCE_HEAD or
                qa.get("package_bytes") != package.stat().st_size):
            raise RuntimeError(f"A010-A012 checkpoint package identity/QA mismatch: {package_name}")
        with zipfile.ZipFile(package, "r") as archive:
            manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
        if (manifest.get("head_commit") != A010_A012_SOURCE_HEAD or
                manifest.get("base_commit") != A009_DELTA_HEAD or
                manifest.get("base_package_name") != A009_DELTA_NAME or
                manifest.get("base_package_sha256") != A009_DELTA_SHA256 or
                manifest.get("package_group") != group):
            raise RuntimeError(f"A010-A012 checkpoint manifest lineage mismatch: {package_name}")
        included = manifest.get("included_files", [])
        member_hashes = manifest.get("included_file_sha256", {})
        if {item.get("archive_path"): item.get("sha256") for item in included} != member_hashes:
            raise RuntimeError(f"A010-A012 checkpoint member/hash closure mismatch: {package_name}")
        for member, digest in member_hashes.items():
            previous = combined_hashes.setdefault(member, digest)
            if previous != digest:
                raise RuntimeError(f"A010-A012 checkpoint has conflicting member hashes: {member}")
        recorded_refs = manifest.get("referenced_existing_raw_sha256", [])
        identities = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                       item.get("source_package_sha256")) for item in recorded_refs}
        if identities != expected_prior or len(identities) != len(recorded_refs):
            raise RuntimeError(f"A010-A012 checkpoint existing-raw references mismatch: {package_name}")

        if group in A010_A012_RUN_PACKAGES:
            expected_raw_sha = A010_A012_RUN_PACKAGES[group][1]
            raw_map = manifest.get("raw_sha256_by_run", {})
            result = json.loads((RUNS / group / "result.json").read_text(encoding="utf-8"))
            raw = RUNS / group / "raw.csv"
            row = manifest_rows.get(group)
            qa_raw = qa.get("raw_sha256_by_run", {}).get(group)
            if (set(raw_map) != {group} or raw_map.get(group) != expected_raw_sha or
                    result.get("raw_sha256") != expected_raw_sha or qa_raw != expected_raw_sha or
                    not row or row.get("raw_sha256") != expected_raw_sha or
                    root.sha256(raw) != expected_raw_sha):
                raise RuntimeError(f"A010-A012 raw/package identity mismatch: {group}")
            prior_run_refs.append({"run_id": group, "raw_path": f"runs/{group}/raw.csv",
                                   "raw_sha256": expected_raw_sha,
                                   "source_package_name": package_name,
                                   "source_package_sha256": expected_package_sha})
        elif manifest.get("raw_sha256_by_run") != {}:
            raise RuntimeError("A010-A012 source checkpoint unexpectedly includes a run raw")
        package_set.append({"package_name": package_name, "package_sha256": expected_package_sha,
                            "source_commit": A010_A012_SOURCE_HEAD, "package_group": group})

    if {item["run_id"] for item in prior_run_refs} != set(A010_A012_RUN_IDS):
        raise RuntimeError("A010-A012 raw reference closure is incomplete")
    return package_set, prior_refs + prior_run_refs, combined_hashes


def verify_prior_t1_a013_a016_checkpoint(root: Any,
                                         prior_packages: list[dict[str, Any]],
                                         prior_refs: list[dict[str, Any]],
                                         prior_hashes: dict[str, str]) -> tuple[
        list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Verify the five-package A013-A016 checkpoint and extend exact raw/member closure."""
    expected_prior = {(item["run_id"], item["raw_sha256"], item["source_package_name"],
                       item["source_package_sha256"]) for item in prior_refs}
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    package_items = [("source", T1_A013_A016_SOURCE_NAME, T1_A013_A016_SOURCE_SHA256)]
    for run_id, (package_sha, _raw_sha) in T1_A013_A016_RUN_PACKAGES.items():
        package_items.append((run_id, f"{SERIES.name}_delta_{T1_A013_A016_TAG}_{run_id}.zip", package_sha))

    checkpoint_packages = []
    checkpoint_hashes: dict[str, str] = {}
    added_raw_refs = []
    for group, package_name, expected_package_sha in package_items:
        package = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = root.verify_existing_bundle(package, qa_path)
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("source_commit") != T1_A013_A016_SOURCE_HEAD or
                qa.get("package_bytes") != package.stat().st_size):
            raise RuntimeError(f"A013-A016 checkpoint package identity/QA mismatch: {package_name}")
        with zipfile.ZipFile(package, "r") as archive:
            manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
        if (manifest.get("head_commit") != T1_A013_A016_SOURCE_HEAD or
                manifest.get("base_commit") != "c42ad75d39cf796cfe863b836f6f8154388a048a" or
                manifest.get("base_package_name") != A010_A012_SOURCE_NAME or
                manifest.get("base_package_sha256") != A010_A012_SOURCE_SHA256 or
                manifest.get("package_group") != group or
                manifest.get("base_delta_packages") != prior_packages):
            raise RuntimeError(f"A013-A016 checkpoint lineage mismatch: {package_name}")

        included = manifest.get("included_files", [])
        member_hashes = manifest.get("included_file_sha256", {})
        if {item.get("archive_path"): item.get("sha256") for item in included} != member_hashes:
            raise RuntimeError(f"A013-A016 checkpoint member/hash closure mismatch: {package_name}")
        for member, digest in member_hashes.items():
            previous = checkpoint_hashes.setdefault(member, digest)
            if previous != digest:
                raise RuntimeError(f"A013-A016 checkpoint has conflicting member hashes: {member}")

        recorded_refs = manifest.get("referenced_existing_raw_sha256", [])
        identities = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                       item.get("source_package_sha256")) for item in recorded_refs}
        if identities != expected_prior or len(identities) != len(recorded_refs):
            raise RuntimeError(f"A013-A016 checkpoint existing-raw references mismatch: {package_name}")
        if manifest.get("base_run_packages") != prior_refs:
            raise RuntimeError(f"A013-A016 checkpoint base-run package references mismatch: {package_name}")

        if group in T1_A013_A016_RUN_PACKAGES:
            expected_raw_sha = T1_A013_A016_RUN_PACKAGES[group][1]
            raw_map = manifest.get("raw_sha256_by_run", {})
            result = json.loads((RUNS / group / "result.json").read_text(encoding="utf-8"))
            raw = RUNS / group / "raw.csv"
            row = manifest_rows.get(group)
            qa_raw = qa.get("raw_sha256_by_run", {}).get(group)
            raw_member = f"test/exploration/{SERIES.name}/runs/{group}/raw.csv"
            if (set(raw_map) != {group} or raw_map.get(group) != expected_raw_sha or
                    result.get("raw_sha256") != expected_raw_sha or qa_raw != expected_raw_sha or
                    not row or row.get("raw_sha256") != expected_raw_sha or
                    member_hashes.get(raw_member) != expected_raw_sha or
                    root.sha256(raw) != expected_raw_sha):
                raise RuntimeError(f"A013-A016 raw/package identity mismatch: {group}")
            added_raw_refs.append({"run_id": group, "raw_path": f"runs/{group}/raw.csv",
                                   "raw_sha256": expected_raw_sha,
                                   "source_package_name": package_name,
                                   "source_package_sha256": expected_package_sha})
        elif manifest.get("raw_sha256_by_run") != {}:
            raise RuntimeError("A013-A016 source checkpoint unexpectedly includes a run raw")

        checkpoint_packages.append({"package_name": package_name, "package_sha256": expected_package_sha,
                                    "source_commit": T1_A013_A016_SOURCE_HEAD, "package_group": group})

    if {item["run_id"] for item in added_raw_refs} != set(T1_A013_A016_RUN_IDS):
        raise RuntimeError("A013-A016 raw reference closure is incomplete")
    combined_hashes = {**prior_hashes, **checkpoint_hashes}
    return checkpoint_packages, prior_refs + added_raw_refs, combined_hashes


def verify_t1_a017_a019_checkpoint(root: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Verify the latest immutable A017-A019 source/raw checkpoint and exact raw lineage."""
    metadata, legacy_refs = base_records(root)
    _bus400_qa, _bus400_manifest, bus400_refs = verify_prior_bus400_delta(root, legacy_refs)
    _a009_qa, _a009_manifest, a009_refs = verify_prior_a009_delta(root, bus400_refs)
    a010_packages, a012_refs, a012_hashes = verify_prior_a010_a012_checkpoint(root, a009_refs)
    a013_packages, a013_refs, prior_hashes = verify_prior_t1_a013_a016_checkpoint(
        root, a010_packages, a012_refs, a012_hashes)
    source_path = HANDOFF / T1_CHAIN_BASE_SOURCE_NAME
    source_qa_path = HANDOFF / f"{Path(T1_CHAIN_BASE_SOURCE_NAME).stem}_PACKAGE_QA.json"
    source_qa = root.verify_existing_bundle(source_path, source_qa_path)
    if (source_qa.get("status") != "PASS" or
            source_qa.get("package_sha256") != T1_CHAIN_BASE_SOURCE_SHA256 or
            source_qa.get("source_commit") != T1_CHAIN_BASE_SOURCE_HEAD or
            source_qa.get("package_bytes") != source_path.stat().st_size):
        raise RuntimeError("A017-A019 source checkpoint ZIP/QA identity mismatch")
    with zipfile.ZipFile(source_path, "r") as archive:
        source_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (source_manifest.get("head_commit") != T1_CHAIN_BASE_SOURCE_HEAD or
            source_manifest.get("base_package_name") != T1_A013_A016_SOURCE_NAME or
            source_manifest.get("base_package_sha256") != T1_A013_A016_SOURCE_SHA256 or
            source_manifest.get("package_group") != "source" or
            source_manifest.get("raw_sha256_by_run") != {}):
        raise RuntimeError("A017-A019 source checkpoint lineage mismatch")
    member_hashes = source_manifest.get("included_file_sha256", {})
    if {item.get("archive_path"): item.get("sha256")
            for item in source_manifest.get("included_files", [])} != member_hashes:
        raise RuntimeError("A017-A019 source checkpoint member/hash map mismatch")
    prior_refs = source_manifest.get("referenced_existing_raw_sha256", [])
    if {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
         item.get("source_package_sha256")) for item in prior_refs} != {
            (item["run_id"], item["raw_sha256"], item["source_package_name"], item["source_package_sha256"])
            for item in a013_refs} or len(prior_refs) != len(a013_refs):
        raise RuntimeError("A017-A019 checkpoint historical raw-reference closure mismatch")
    checkpoint_hashes = dict(prior_hashes)
    # The latest checkpoint legitimately replaces member identities that its
    # own manifest marks modified relative to A013-A016.
    checkpoint_hashes.update(member_hashes)

    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    added_refs = []
    packages = list(source_manifest.get("base_delta_packages", []))
    packages.append({"package_name": T1_CHAIN_BASE_SOURCE_NAME,
                     "package_sha256": T1_CHAIN_BASE_SOURCE_SHA256,
                     "source_commit": T1_CHAIN_BASE_SOURCE_HEAD, "package_group": "source"})
    for run_id, (expected_package_sha, expected_raw_sha, expected_artifact) in T1_CHAIN_BASE_RUN_PACKAGES.items():
        package_name = f"{SERIES.name}_delta_T1_A017_A019_20261009_{run_id}.zip"
        package = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = root.verify_existing_bundle(package, qa_path)
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("source_commit") != T1_CHAIN_BASE_SOURCE_HEAD or
                qa.get("package_bytes") != package.stat().st_size):
            raise RuntimeError(f"A017-A019 run package identity/QA mismatch: {run_id}")
        with zipfile.ZipFile(package, "r") as archive:
            manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
        if (manifest.get("head_commit") != T1_CHAIN_BASE_SOURCE_HEAD or
                manifest.get("package_group") != run_id or
                manifest.get("base_package_name") != T1_A013_A016_SOURCE_NAME or
                manifest.get("base_package_sha256") != T1_A013_A016_SOURCE_SHA256):
            raise RuntimeError(f"A017-A019 run package lineage mismatch: {run_id}")
        raw_map = manifest.get("raw_sha256_by_run", {})
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        raw = RUNS / run_id / "raw.csv"
        row = manifest_rows.get(run_id)
        raw_member = f"test/exploration/{SERIES.name}/runs/{run_id}/raw.csv"
        qa_raw = qa.get("raw_sha256_by_run", {}).get(run_id)
        if (set(raw_map) != {run_id} or raw_map.get(run_id) != expected_raw_sha or
                result.get("raw_sha256") != expected_raw_sha or qa_raw != expected_raw_sha or
                not row or row.get("raw_sha256") != expected_raw_sha or
                manifest.get("included_file_sha256", {}).get(raw_member) != expected_raw_sha or
                root.sha256(raw) != expected_raw_sha or result.get("artifact_status") != expected_artifact):
            raise RuntimeError(f"A017-A019 raw identity/status mismatch: {run_id}")
        added_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256": expected_raw_sha,
                           "source_package_name": package_name,
                           "source_package_sha256": expected_package_sha})
        packages.append({"package_name": package_name, "package_sha256": expected_package_sha,
                         "source_commit": T1_CHAIN_BASE_SOURCE_HEAD, "package_group": run_id})
        for member, digest in manifest.get("included_file_sha256", {}).items():
            if member in checkpoint_hashes and checkpoint_hashes[member] != digest:
                raise RuntimeError(f"A017-A019 checkpoint has conflicting member hash: {member}")
            checkpoint_hashes[member] = digest
    expected_runs = set(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                        T1_A013_A016_RUN_IDS + T1_CHAIN_BASE_RUN_IDS)
    if {item["run_id"] for item in prior_refs + added_refs} != expected_runs:
        raise RuntimeError("A017-A019 checkpoint raw closure is not exactly A001-A019")
    return packages, prior_refs + added_refs, checkpoint_hashes


def partition_delta_sources(sources: list[tuple[Path, str]]) -> tuple[
        dict[str, list[tuple[Path, str]]], list[tuple[Path, str]]]:
    by_run = {run_id: [] for run_id in DELTA_RUN_IDS}
    shared = []
    for item in sources:
        parts = Path(item[1]).parts
        if len(parts) >= 5 and parts[:4] == ("test", "exploration", SERIES.name, "runs") and parts[4] in by_run:
            by_run[parts[4]].append(item)
        else:
            shared.append(item)
    members = [member for _source, member in shared]
    members.extend(member for group in by_run.values() for _source, member in group)
    if len(members) != len(sources) or len(members) != len(set(members)):
        raise RuntimeError("delta source partition is incomplete or contains duplicate members")
    missing = [run_id for run_id, group in by_run.items()
               if not any(Path(member).name == "raw.csv" for _source, member in group)]
    if missing:
        raise RuntimeError(f"delta partition is missing run raw files: {missing}")
    if not shared:
        raise RuntimeError("delta has no shared source/config/manifest files")
    return by_run, shared


def _delta_sources(root: Any) -> tuple[list[tuple[Path, str]], list[str], list[str]]:
    changes = dict(root.committed_changes(DELTA_BASE_COMMIT, git("rev-parse", "HEAD")))
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    sources: dict[str, Path] = {}
    excluded_html: set[str] = set()
    changed_paths: set[str] = set()
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if not (root.in_scope(rel_path, [SERIES]) or rel_path in DELTA_GLOBAL_PATHS):
            continue
        if status == "D":
            raise RuntimeError(f"delta submission refuses file deletion: {rel_path}")
        if path.parts[:2] == ("test", "exploration") and path.parts[2:3] == (SERIES.name,):
            if len(path.parts) >= 4 and path.parts[3] == "runs":
                if not is_allowed_delta_run_path(rel_path):
                    raise RuntimeError(f"delta submission detected a historical run edit: {rel_path}")
        if _excluded_delta_path(path):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        source = REPO / path
        if source.is_file() and not source.is_symlink():
            sources[rel_path] = source
            changed_paths.add(rel_path)

    # Run evidence may be ignored by Git until the submission explicitly stages it.
    for run_id in DELTA_RUN_IDS:
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"new authorized run directory is missing: {run_id}")
        for path in included_files(run_dir):
            rel_path = path.relative_to(REPO).as_posix()
            sources[rel_path] = path
            changed_paths.add(rel_path)

    for path in SERIES.rglob("*.html"):
        if path.is_file():
            excluded_html.add(path.relative_to(REPO).as_posix())

    # The repository globally ignores JSON outputs, so explicitly inventory the
    # new task's preregistration, static QA, batch closure and derived summary.
    task_analysis = SERIES / "analysis" / "t1-array-20261009"
    for path in sorted(task_analysis.rglob("*")):
        if not path.is_file() or _excluded_delta_path(path.relative_to(REPO)):
            continue
        rel_path = path.relative_to(REPO).as_posix()
        sources[rel_path] = path
        changed_paths.add(rel_path)

    required_valid_run_files = {"deck.cir", "raw.csv", "run.log", "stdout.txt", "stderr.txt",
                                "USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
                                "stimulus.inc", "case_manifest.json", "metadata.json", "provenance.json",
                                "source_manifest.json", "topology_manifest.json", "probe_manifest.json",
                                "static_qa.json", "stimulus_manifest.json", "metrics.json", "raw_qa.json",
                                "qa.json", "t1_array_qa.json", "plot_manifest.json", "plot_qa.json",
                                "result.json", "RESULT_BRIEF.md"}
    required_invalid_run_files = {"deck.cir", "raw.csv", "run.log", "stdout.txt", "stderr.txt",
                                  "USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
                                  "stimulus.inc", "case_manifest.json", "source_manifest.json",
                                  "topology_manifest.json", "probe_manifest.json", "static_qa.json",
                                  "stimulus_manifest.json", "result.json"}
    for run_id in DELTA_RUN_IDS:
        run_prefix = ("test", "exploration", SERIES.name, "runs", run_id)
        run_members = {item for item in sources if Path(item).parts[:5] == run_prefix}
        have = {Path(item).name for item in run_members}
        required = (required_invalid_run_files if run_id in INVALID_PRESERVED_DELTA_RUN_IDS
                    else required_valid_run_files)
        missing = required - have
        if (run_id in INVALID_PRESERVED_DELTA_RUN_IDS and
                f"test/exploration/{SERIES.name}/runs/{run_id}/sources/t1_cell_tunable.cir" not in run_members):
            missing.add("sources/t1_cell_tunable.cir")
        if missing:
            raise RuntimeError(f"{run_id} delta evidence is incomplete: {sorted(missing)}")

    # Every existing, non-HTML change from the registered Git base must appear.
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if status == "D" or _excluded_delta_path(path):
            continue
        if root.in_scope(rel_path, [SERIES]) or rel_path in DELTA_GLOBAL_PATHS:
            if path.parts[:2] == ("test", "exploration") and path.parts[2:3] == (SERIES.name,):
                if len(path.parts) >= 4 and path.parts[3] == "runs":
                    continue
            if (REPO / path).is_file() and rel_path not in sources:
                raise RuntimeError(f"changed evidence/source omitted from delta inventory: {rel_path}")
    ordered = [(sources[key], key) for key in sorted(sources)]
    return ordered, sorted(changed_paths), sorted(excluded_html)


def _t1_chain_delta_sources(root: Any) -> tuple[list[tuple[Path, str]], dict[str, str], list[str]]:
    head = git("rev-parse", "HEAD")
    changes = dict(root.committed_changes(T1_CHAIN_BASE_COMMIT, head))
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    sources: dict[str, Path] = {}
    excluded_html: set[str] = set()
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if not root.in_scope(rel_path, [SERIES]):
            raise RuntimeError(f"chain delta found a changed path outside this series: {rel_path}")
        if status == "D":
            raise RuntimeError(f"chain delta refuses deletions: {rel_path}")
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            if len(path.parts) < 5 or path.parts[4] not in T1_CHAIN_DELTA_RUN_IDS:
                raise RuntimeError(f"chain delta detected an edit to historical run evidence: {rel_path}")
            continue
        if _excluded_delta_path(path):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        source = REPO / path
        if source.is_file() and not source.is_symlink():
            sources[rel_path] = source

    # New run trees and ignored task-analysis JSON are explicitly inventoried.
    for run_id in T1_CHAIN_DELTA_RUN_IDS:
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"chain delta run directory is missing: {run_id}")
        for path in included_files(run_dir):
            sources[path.relative_to(REPO).as_posix()] = path
    task_analysis = SERIES / "analysis" / "t1-chain-20261009"
    if not task_analysis.is_dir():
        raise RuntimeError("chain work-unit analysis directory is missing")
    for path in sorted(task_analysis.rglob("*")):
        if path.is_file() and not _excluded_delta_path(path.relative_to(REPO)):
            sources[path.relative_to(REPO).as_posix()] = path

    for path in SERIES.rglob("*.html"):
        if path.is_file():
            excluded_html.add(path.relative_to(REPO).as_posix())

    # Every in-scope changed, non-HTML file must be represented in the source or
    # one of the new run groups; no recent-edit-only packaging is permitted.
    members = set(sources)
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if status == "D" or _excluded_delta_path(path):
            continue
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            continue
        if root.in_scope(rel_path, [SERIES]) and (REPO / path).is_file() and rel_path not in members:
            raise RuntimeError(f"changed source/evidence omitted from chain delta: {rel_path}")
    return [(sources[key], key) for key in sorted(sources)], changes, sorted(excluded_html)


def verify_cb_direct_d1_base_checkpoint(root: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Verify the committed A020-A022 five-package checkpoint and close A001-A022 raw references."""
    prior_packages, prior_refs, member_hashes = verify_t1_a017_a019_checkpoint(root)
    expected_prior_ids = {item["run_id"] for item in prior_refs}
    if len(prior_refs) != 19 or expected_prior_ids != {
            *LEGACY_RUN_IDS, *BUS400_RUN_IDS, *A009_RUN_IDS, *A010_A012_RUN_IDS,
            *T1_A013_A016_RUN_IDS, *T1_CHAIN_BASE_RUN_IDS}:
        raise RuntimeError("A017-A019 checkpoint did not close exactly A001-A019")

    experiment = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    manifest_rows = {row.get("run_id"): row for row in experiment.get("runs", [])}
    base_run_refs = list(prior_refs)
    package_records = list(prior_packages)
    a020_refs = []
    raw_by_run = {run_id: raw_sha for run_id, (_package_sha, raw_sha) in
                  CB_DIRECT_D1_BASE_RUN_PACKAGES.items()}
    for group, package_name, expected_package_sha in CB_DIRECT_D1_BASE_PACKAGE_GROUPS:
        package_path = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = root.verify_existing_bundle(package_path, qa_path)
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("source_commit") != CB_DIRECT_D1_BASE_COMMIT or
                qa.get("package_bytes") != package_path.stat().st_size):
            raise RuntimeError(f"A020-A022 checkpoint package identity/QA mismatch: {package_name}")
        with zipfile.ZipFile(package_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"A020-A022 checkpoint ZIP CRC failure: {package_name}/{bad}")
            delta = json.loads(archive.read("DELTA_MANIFEST.json"))
            members = set(archive.namelist())
            included = delta.get("included_files", [])
            hashes = delta.get("included_file_sha256", {})
            if {item.get("archive_path"): item.get("sha256") for item in included} != hashes:
                raise RuntimeError(f"A020-A022 checkpoint file/hash manifest mismatch: {package_name}")
            for member, digest in hashes.items():
                if member not in members or hashlib.sha256(archive.read(member)).hexdigest() != digest:
                    raise RuntimeError(f"A020-A022 checkpoint member hash mismatch: {package_name}/{member}")
        if (delta.get("head_commit") != CB_DIRECT_D1_BASE_COMMIT or
                delta.get("base_commit") != T1_CHAIN_BASE_COMMIT or
                delta.get("base_package_name") != T1_CHAIN_BASE_SOURCE_NAME or
                delta.get("base_package_sha256") != T1_CHAIN_BASE_SOURCE_SHA256 or
                delta.get("package_group") != group):
            raise RuntimeError(f"A020-A022 checkpoint lineage mismatch: {package_name}")
        refs = delta.get("referenced_existing_raw_sha256", [])
        if {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
             item.get("source_package_sha256")) for item in refs} != {
                (item["run_id"], item["raw_sha256"], item["source_package_name"], item["source_package_sha256"])
                for item in prior_refs} or len(refs) != len(prior_refs):
            raise RuntimeError(f"A020-A022 checkpoint A001-A019 raw closure mismatch: {package_name}")

        for member, digest in hashes.items():
            member_hashes[member] = digest

        expected_runs = set(T1_CHAIN_DELTA_RUN_IDS)
        if group == "source":
            if delta.get("raw_sha256_by_run") != {}:
                raise RuntimeError("A020-A022 source checkpoint unexpectedly contains a raw")
        elif group == "runs_metadata":
            if (delta.get("raw_sha256_by_run") != {} or
                    delta.get("associated_raw_sha256_by_run") != raw_by_run or
                    set(delta.get("associated_raw_sha256_by_run", {})) != expected_runs):
                raise RuntimeError("A020-A022 metadata checkpoint raw association is incomplete")
        else:
            run_id = group.removesuffix("_raw")
            expected_raw_sha = raw_by_run[run_id]
            member = f"test/exploration/{SERIES.name}/runs/{run_id}/raw.csv"
            result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
            raw = RUNS / run_id / "raw.csv"
            qa_raw = qa.get("raw_sha256_by_run", {}).get(run_id)
            if (delta.get("raw_sha256_by_run") != {run_id: expected_raw_sha} or
                    hashes.get(member) != expected_raw_sha or qa_raw != expected_raw_sha or
                    root.sha256(raw) != expected_raw_sha or result.get("raw_sha256") != expected_raw_sha):
                raise RuntimeError(f"A020-A022 raw/package identity mismatch: {run_id}")
            row = manifest_rows.get(run_id)
            if not row or row.get("raw_sha256") != expected_raw_sha:
                raise RuntimeError(f"A020-A022 experiment manifest raw SHA mismatch: {run_id}")
            a020_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                              "raw_sha256": expected_raw_sha, "source_package_name": package_name,
                              "source_package_sha256": expected_package_sha})
        package_records.append({"package_name": package_name, "package_sha256": expected_package_sha,
                                "source_commit": CB_DIRECT_D1_BASE_COMMIT, "package_group": group})
    if {item["run_id"] for item in a020_refs} != expected_runs:
        raise RuntimeError("A020-A022 checkpoint raw package closure is incomplete")
    existing_refs = base_run_refs + a020_refs
    expected_all = expected_prior_ids | set(T1_CHAIN_DELTA_RUN_IDS)
    if len(existing_refs) != 22 or {item["run_id"] for item in existing_refs} != expected_all:
        raise RuntimeError("verified base raw reference closure is not exactly A001-A022")
    return package_records, existing_refs, member_hashes


def _cb_direct_d1_delta_sources(root: Any) -> tuple[list[tuple[Path, str]], dict[str, str], list[str]]:
    head = git("rev-parse", "HEAD")
    changes = dict(root.committed_changes(CB_DIRECT_D1_BASE_COMMIT, head))
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    sources: dict[str, Path] = {}
    excluded_html: set[str] = set()
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if not root.in_scope(rel_path, [SERIES]):
            raise RuntimeError(f"CB_DIRECT D1 DELTA found an out-of-scope change: {rel_path}")
        if status == "D":
            raise RuntimeError(f"CB_DIRECT D1 DELTA refuses deletions: {rel_path}")
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            if len(path.parts) < 5 or path.parts[4] not in CB_DIRECT_D1_RUN_IDS:
                raise RuntimeError(f"CB_DIRECT D1 DELTA detected historical run edit: {rel_path}")
            continue
        if _excluded_delta_path(path):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        source = REPO / path
        if source.is_file() and not source.is_symlink():
            sources[rel_path] = source

    for run_id in CB_DIRECT_D1_RUN_IDS:
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"new authorized run directory is missing: {run_id}")
        for path in included_files(run_dir):
            sources[path.relative_to(REPO).as_posix()] = path

    task_analysis = SERIES / "analysis" / "cb-direct-d1-20261009"
    for path in sorted(task_analysis.rglob("*")):
        if not path.is_file() or _excluded_delta_path(path.relative_to(REPO)):
            continue
        sources[path.relative_to(REPO).as_posix()] = path

    for path in SERIES.rglob("*.html"):
        if path.is_file():
            excluded_html.add(path.relative_to(REPO).as_posix())

    for rel_path, status in changes.items():
        path = Path(rel_path)
        if status == "D" or _excluded_delta_path(path):
            continue
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            continue
        if root.in_scope(rel_path, [SERIES]) and (REPO / path).is_file() and rel_path not in sources:
            raise RuntimeError(f"changed source/evidence omitted from CB_DIRECT D1 DELTA: {rel_path}")
    return [(sources[key], key) for key in sorted(sources)], changes, sorted(excluded_html)


def validate_cb_direct_d1_scope(root: Any) -> dict[str, Any]:
    if git("branch", "--show-current") != "master":
        raise RuntimeError("CB_DIRECT D1 DELTA expects the existing master branch")
    if subprocess.run(["git", "merge-base", "--is-ancestor", CB_DIRECT_D1_BASE_COMMIT,
                       git("rev-parse", "HEAD")], cwd=REPO, check=False).returncode != 0:
        raise RuntimeError("CB_DIRECT D1 HEAD is not descended from the A020-A022 source checkpoint")
    expected_run_dirs = list(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                             T1_A013_A016_RUN_IDS + T1_CHAIN_BASE_RUN_IDS + T1_CHAIN_DELTA_RUN_IDS +
                             CB_DIRECT_D1_RUN_IDS)
    actual_run_dirs = sorted(path.name for path in RUNS.iterdir()
                             if path.is_dir() and re.fullmatch(r"A\d{3}_.+", path.name))
    if actual_run_dirs != expected_run_dirs:
        raise RuntimeError(f"CB_DIRECT D1 run closure mismatch: expected {expected_run_dirs}, found {actual_run_dirs}")

    base_packages, existing_raw_refs, base_member_hashes = verify_cb_direct_d1_base_checkpoint(root)
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    manifest_rows = {item.get("run_id"): item for item in manifest.get("runs", [])}
    if int(manifest.get("physical_solve_count", -1)) != 24:
        raise RuntimeError(f"experiment_manifest physical_solve_count should be 24, got {manifest.get('physical_solve_count')}")
    auth = [item for item in manifest.get("authorization_batches", [])
            if item.get("batch_id") == "BVM4X4_CB_DIRECT_D1_20261009"]
    if (len(auth) != 1 or auth[0].get("authorized_physical_solve_count") != 2 or
            auth[0].get("physical_solve_count_completed") != 2 or
            auth[0].get("run_ids") != list(CB_DIRECT_D1_RUN_IDS) or
            auth[0].get("execution_preflight_attempt") != 2):
        raise RuntimeError("CB_DIRECT D1 authorization completion is not exactly A023/A024")

    task_root = SERIES / "analysis" / "cb-direct-d1-20261009"
    attempt = task_root / "attempts" / "002"
    batch = json.loads((attempt / "BATCH_MANIFEST.json").read_text(encoding="utf-8"))
    comparison = json.loads((task_root / "CB_DIRECT_D1_COMPARISON.json").read_text(encoding="utf-8"))
    comparison_qa = json.loads((task_root / "COMPARISON_PLOT_QA.json").read_text(encoding="utf-8"))
    if (batch.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            batch.get("authorized_run_ids") != list(CB_DIRECT_D1_RUN_IDS) or
            [item.get("run_id") for item in batch.get("runs", [])] != list(CB_DIRECT_D1_RUN_IDS) or
            batch.get("physical_solve_count_completed") != 2 or
            comparison.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            comparison.get("physical_solve_count") != 2 or comparison_qa.get("status") != "PASS"):
        raise RuntimeError("CB_DIRECT D1 batch, comparison, or plot QA is not mechanically closed")

    handoff = json.loads((task_root / "RAW_ANALYSIS_HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    handoff_refs = handoff.get("existing_raw_references", [])
    expected_refs = {(item["run_id"], item["raw_sha256"], item["source_package_name"], item["source_package_sha256"])
                     for item in existing_raw_refs}
    actual_refs = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                    item.get("source_package_sha256")) for item in handoff_refs}
    if len(existing_raw_refs) != 22 or len(actual_refs) != len(handoff_refs) or actual_refs != expected_refs:
        raise RuntimeError("CB_DIRECT D1 raw handoff manifest does not bind exactly A001-A022")

    incident = json.loads((task_root / "GATE_INCIDENT_001.json").read_text(encoding="utf-8"))
    first_attempt = json.loads((task_root / "BATCH_MANIFEST.json").read_text(encoding="utf-8"))
    if (incident.get("physical_solve_count") != 0 or incident.get("transient_solver_invoked") is not False or
            first_attempt.get("status") != "STOPPED_BEFORE_PHYSICAL_SOLVE" or
            first_attempt.get("physical_solve_count_completed") != 0):
        raise RuntimeError("attempt-1 gate stop/zero-solve incident is not preserved")

    raw_sha_by_run, run_status = {}, {}
    for run_id in CB_DIRECT_D1_RUN_IDS:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        raw_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
        source = json.loads((run_dir / "source_manifest.json").read_text(encoding="utf-8"))
        topology = json.loads((run_dir / "topology_manifest.json").read_text(encoding="utf-8"))
        case = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8")).get("case", {})
        plot = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        digest = root.sha256(raw)
        row = manifest_rows.get(run_id)
        expected_bits = ("1111", "1111") if run_id == CB_DIRECT_D1_RUN_IDS[0] else ("1101", "1101")
        if (result.get("run_id") != run_id or result.get("artifact_status") != "VALID" or
                result.get("physical_solve_count") != 1 or result.get("raw_sha256") != digest or
                qa.get("status") != "PASS" or qa.get("raw_sha256_before_analysis") != digest or
                qa.get("raw_sha256_after_analysis") != digest or raw_qa.get("status") != "PASS" or
                raw_qa.get("raw_sha256_after_analysis") != digest or metrics.get("raw_sha256") != digest or
                provenance.get("raw_sha256") != digest or plot.get("status") != "PASS" or
                plot.get("raw_sha256_after") != digest or not row or row.get("raw_sha256") != digest or
                raw.stat().st_size >= root.MAX_GIT_FILE_BYTES or
                (result.get("row_bits"), result.get("column_bits")) != expected_bits):
            raise RuntimeError(f"A023/A024 run raw/provenance/mechanical identity failed: {run_id}")
        if (source.get("sources", {}).get("CBU_D1_DIRECT", {}).get("sha256") !=
                "70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370" or
                topology.get("cbu_type_by_stage", {}).get("D1") != "CB" or
                topology.get("cbu_type_by_stage", {}).get("D2") != "THmitll_MERGE" or
                case.get("CBU_OVERRIDE_D1") != "CB_DIRECT"):
            raise RuntimeError(f"D1 direct CB source/topology provenance mismatch: {run_id}")
        for page in plot.get("pages", []):
            page_path = SERIES / page["path"]
            if not page_path.is_file() or root.sha256(page_path) != page.get("sha256"):
                raise RuntimeError(f"A023/A024 standalone plot identity mismatch: {run_id}/{page.get('path')}")
        raw_sha_by_run[run_id] = digest
        run_status[run_id] = {"status": result.get("status"), "artifact_status": result.get("artifact_status"),
                              "physical_solve_count": result.get("physical_solve_count"),
                              "qa_status": qa.get("status"), "raw_bytes": raw.stat().st_size}
    for page in comparison_qa.get("pages", []):
        page_path = SERIES / page["path"]
        if not page_path.is_file() or root.sha256(page_path) != page.get("sha256"):
            raise RuntimeError(f"paired comparison plot hash mismatch: {page.get('path')}")

    sources, changes, excluded_html = _cb_direct_d1_delta_sources(root)
    run_prefix = {run_id: ("test", "exploration", SERIES.name, "runs", run_id)
                  for run_id in CB_DIRECT_D1_RUN_IDS}
    run_files = {run_id: [(source, member) for source, member in sources
                          if Path(member).parts[:5] == run_prefix[run_id]]
                 for run_id in CB_DIRECT_D1_RUN_IDS}
    for run_id, files in run_files.items():
        if not files or not any(Path(member).name == "raw.csv" for _source, member in files):
            raise RuntimeError(f"CB_DIRECT D1 DELTA inventory is incomplete for {run_id}")
    shared = [(source, member) for source, member in sources
              if Path(member).parts[:4] != ("test", "exploration", SERIES.name, "runs")]
    if not shared:
        raise RuntimeError("CB_DIRECT D1 DELTA has no source or analysis evidence")
    return {"base_packages": base_packages, "existing_raw_refs": existing_raw_refs,
            "base_member_hashes": base_member_hashes, "raw_sha256_by_run": raw_sha_by_run,
            "run_artifact_status_by_run": run_status, "sources": sources,
            "run_files": run_files, "shared_sources": shared,
            "changes": changes, "excluded_html": excluded_html,
            "batch": batch, "comparison": comparison}


def validate_cb_direct_d1_scope(root: Any) -> dict[str, Any]:
    if git("branch", "--show-current") != "master":
        raise RuntimeError("CB_DIRECT D1 DELTA expects the existing master branch")
    if subprocess.run(["git", "merge-base", "--is-ancestor", CB_DIRECT_D1_BASE_COMMIT,
                       git("rev-parse", "HEAD")], cwd=REPO, check=False).returncode != 0:
        raise RuntimeError("CB_DIRECT D1 HEAD is not descended from the A020-A022 package source commit")
    expected_run_dirs = list(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                             T1_A013_A016_RUN_IDS + T1_CHAIN_BASE_RUN_IDS + T1_CHAIN_DELTA_RUN_IDS +
                             CB_DIRECT_D1_RUN_IDS)
    actual_run_dirs = sorted(path.name for path in RUNS.iterdir()
                             if path.is_dir() and re.fullmatch(r"A\d{3}_.+", path.name))
    if actual_run_dirs != expected_run_dirs:
        raise RuntimeError(f"CB_DIRECT D1 run closure mismatch: expected {expected_run_dirs}, found {actual_run_dirs}")

    base_packages, existing_raw_refs, base_member_hashes = verify_cb_direct_d1_base_checkpoint(root)
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    run_rows = {item.get("run_id"): item for item in manifest.get("runs", [])}
    if int(manifest.get("physical_solve_count", -1)) != 24:
        raise RuntimeError(f"experiment manifest physical_solve_count should be 24, got {manifest.get('physical_solve_count')}")
    auth = [item for item in manifest.get("authorization_batches", [])
            if item.get("batch_id") == "BVM4X4_CB_DIRECT_D1_20261009"]
    if (len(auth) != 1 or auth[0].get("authorized_physical_solve_count") != 2 or
            auth[0].get("physical_solve_count_completed") != 2 or
            auth[0].get("run_ids") != list(CB_DIRECT_D1_RUN_IDS) or
            auth[0].get("execution_preflight_attempt") != 2):
        raise RuntimeError("CB_DIRECT D1 authorization completion record is not exactly A023/A024")

    attempt = SERIES / "analysis" / "cb-direct-d1-20261009" / "attempts" / "002"
    preflight_path = attempt / "PREFLIGHT.md"
    static_qa_path = attempt / "STATIC_QA.json"
    probes_path = attempt / "PROBE_MANIFEST.json"
    work_unit = json.loads((attempt / "WORK_UNIT.json").read_text(encoding="utf-8"))
    static_qa = json.loads(static_qa_path.read_text(encoding="utf-8"))
    batch = json.loads((attempt / "BATCH_MANIFEST.json").read_text(encoding="utf-8"))
    comparison = json.loads((SERIES / "analysis/cb-direct-d1-20261009/CB_DIRECT_D1_COMPARISON.json").read_text(encoding="utf-8"))
    plot_qa = json.loads((SERIES / "analysis/cb-direct-d1-20261009/COMPARISON_PLOT_QA.json").read_text(encoding="utf-8"))
    numerical_recheck_path = SERIES / "analysis/cb-direct-d1-20261009/NUMERICAL_RECHECK.json"
    numerical_recheck = json.loads(numerical_recheck_path.read_text(encoding="utf-8"))
    if (batch.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            batch.get("authorized_run_ids") != list(CB_DIRECT_D1_RUN_IDS) or
            [row.get("run_id") for row in batch.get("runs", [])] != list(CB_DIRECT_D1_RUN_IDS) or
            batch.get("physical_solve_count_completed") != 2 or
            static_qa.get("status") != "PASS" or static_qa.get("physical_solve_count") != 0 or
            work_unit.get("authorized_run_ids") != list(CB_DIRECT_D1_RUN_IDS) or
            work_unit.get("preflight_sha256") != root.sha256(preflight_path) or
            work_unit.get("static_qa_sha256") != root.sha256(static_qa_path) or
            work_unit.get("probe_manifest_sha256") != root.sha256(probes_path) or
            batch.get("preflight_sha256") != root.sha256(preflight_path) or
            batch.get("static_qa_sha256") != root.sha256(static_qa_path) or
            batch.get("probe_manifest_sha256") != root.sha256(probes_path) or
            comparison.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            comparison.get("physical_solve_count") != 2 or plot_qa.get("status") != "PASS" or
            numerical_recheck.get("status") != "PASS_RAW_RECOMPUTATION_MATCHES_METRICS" or
            numerical_recheck.get("physical_solve_count") != 0 or
            numerical_recheck.get("same_jj_window_checks") != 80 or
            batch.get("numerical_recheck_sha256") != root.sha256(numerical_recheck_path)):
        raise RuntimeError("CB_DIRECT D1 batch/comparison/plot QA is not mechanically closed")
    raw_handoff = json.loads((SERIES / "analysis/cb-direct-d1-20261009/RAW_ANALYSIS_HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    handoff_refs = raw_handoff.get("existing_raw_references", [])
    expected_ref_ids = {item["run_id"] for item in existing_raw_refs}
    handoff_identities = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                           item.get("source_package_sha256")) for item in handoff_refs}
    expected_identities = {(item["run_id"], item["raw_sha256"], item["source_package_name"],
                            item["source_package_sha256"]) for item in existing_raw_refs}
    if (len(existing_raw_refs) != 22 or {item.get("run_id") for item in handoff_refs} != expected_ref_ids or
            len(handoff_identities) != len(handoff_refs) or handoff_identities != expected_identities):
        raise RuntimeError("raw handoff manifest does not reference exactly A001-A022")
    for incident_file in (SERIES / "analysis/cb-direct-d1-20261009/GATE_INCIDENT_001.json",
                          SERIES / "analysis/cb-direct-d1-20261009/BATCH_MANIFEST.json"):
        if not incident_file.is_file():
            raise RuntimeError("pre-solver gate incident history is not preserved")
    failed_gate = json.loads((SERIES / "analysis/cb-direct-d1-20261009/GATE_INCIDENT_001.json").read_text(encoding="utf-8"))
    first_batch = json.loads((SERIES / "analysis/cb-direct-d1-20261009/BATCH_MANIFEST.json").read_text(encoding="utf-8"))
    if (failed_gate.get("physical_solve_count") != 0 or failed_gate.get("transient_solver_invoked") is not False or
            first_batch.get("status") != "STOPPED_BEFORE_PHYSICAL_SOLVE" or
            first_batch.get("physical_solve_count_completed") != 0):
        raise RuntimeError("attempt-1 gate incident does not clearly record zero transient solves")

    raw_sha_by_run, run_status = {}, {}
    for run_id in CB_DIRECT_D1_RUN_IDS:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        chain_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
        source = json.loads((run_dir / "source_manifest.json").read_text(encoding="utf-8"))
        topology = json.loads((run_dir / "topology_manifest.json").read_text(encoding="utf-8"))
        case_manifest = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8"))
        case = case_manifest.get("case", {})
        probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
        plot = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        digest = root.sha256(raw)
        row = run_rows.get(run_id)
        expected_bits = ("1111", "1111") if run_id == CB_DIRECT_D1_RUN_IDS[0] else ("1101", "1101")
        if (result.get("run_id") != run_id or result.get("artifact_status") != "VALID" or
                result.get("physical_solve_count") != 1 or result.get("raw_sha256") != digest or
                qa.get("status") != "PASS" or qa.get("raw_sha256_before_analysis") != digest or
                qa.get("raw_sha256_after_analysis") != digest or chain_qa.get("status") != "PASS" or
                chain_qa.get("raw_sha256_after_analysis") != digest or metrics.get("raw_sha256") != digest or
                provenance.get("raw_sha256") != digest or
                provenance.get("preflight_sha256") != root.sha256(preflight_path) or
                provenance.get("metric_spec_sha256") != root.sha256(SERIES / "analysis/cb-direct-d1-20261009/METRIC_SPEC.json") or
                plot.get("status") != "PASS" or
                plot.get("raw_sha256_after") != digest or not row or row.get("raw_sha256") != digest or
                raw.stat().st_size >= root.MAX_GIT_FILE_BYTES or
                (result.get("row_bits"), result.get("column_bits")) != expected_bits):
            raise RuntimeError(f"A023/A024 run raw/provenance/mechanical identity failed: {run_id}")
        if (source.get("sources", {}).get("CBU_D1_DIRECT", {}).get("sha256") !=
                "70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370" or
                topology.get("cbu_type_by_stage", {}).get("D1") != "CB" or
                topology.get("cbu_type_by_stage", {}).get("D2") != "THmitll_MERGE" or
                case.get("CBU_OVERRIDE_D1") != "CB_DIRECT"):
            raise RuntimeError(f"D1 direct CB source/topology provenance mismatch: {run_id}")
        for page in plot.get("pages", []):
            plot_path = SERIES / page["path"]
            if not plot_path.is_file() or root.sha256(plot_path) != page.get("sha256"):
                raise RuntimeError(f"A023/A024 standalone plot identity mismatch: {run_id}/{page.get('path')}")
        raw_sha_by_run[run_id] = digest
        run_status[run_id] = {"status": result.get("status"), "artifact_status": result.get("artifact_status"),
                              "physical_solve_count": result.get("physical_solve_count"),
                              "qa_status": qa.get("status"), "raw_bytes": raw.stat().st_size}
    for page in plot_qa.get("pages", []):
        page_path = SERIES / page["path"]
        if not page_path.is_file() or root.sha256(page_path) != page.get("sha256"):
            raise RuntimeError(f"paired comparison plot hash mismatch: {page.get('path')}")

    sources, changes, excluded_html = _cb_direct_d1_delta_sources(root)
    run_dir_prefixes = {run_id: ("test", "exploration", SERIES.name, "runs", run_id)
                        for run_id in CB_DIRECT_D1_RUN_IDS}
    run_files = {run_id: [(source, member) for source, member in sources
                          if Path(member).parts[:5] == run_dir_prefixes[run_id]]
                 for run_id in CB_DIRECT_D1_RUN_IDS}
    for run_id, files in run_files.items():
        if not files or not any(Path(member).name == "raw.csv" for _source, member in files):
            raise RuntimeError(f"DELTA inventory lacks raw/evidence for {run_id}")
    shared = [(source, member) for source, member in sources
              if Path(member).parts[:4] != ("test", "exploration", SERIES.name, "runs")]
    if not shared:
        raise RuntimeError("CB_DIRECT D1 DELTA has no source/analysis evidence")
    return {"base_packages": base_packages, "existing_raw_refs": existing_raw_refs,
            "base_member_hashes": base_member_hashes, "raw_sha256_by_run": raw_sha_by_run,
            "run_artifact_status_by_run": run_status, "sources": sources,
            "run_files": run_files, "shared_sources": shared,
            "changes": changes, "excluded_html": excluded_html,
            "batch": batch, "comparison": comparison}


def validate_t1_chain_scope(root: Any) -> dict[str, Any]:
    if git("branch", "--show-current") != "master":
        raise RuntimeError("chain DELTA expects the existing master branch")
    if git("rev-parse", "--is-inside-work-tree") != "true":
        raise RuntimeError("not in a Git worktree")
    if subprocess.run(["git", "merge-base", "--is-ancestor", T1_CHAIN_BASE_COMMIT,
                       git("rev-parse", "HEAD")], cwd=REPO, check=False).returncode != 0:
        raise RuntimeError("chain DELTA HEAD is not descended from the A017-A019 package checkpoint")
    if not (RUNS / T1_CHAIN_DELTA_RUN_IDS[-1]).is_dir():
        raise RuntimeError("A020-A022 chain batch is incomplete")
    all_run_dirs = sorted(path.name for path in RUNS.iterdir()
                          if path.is_dir() and re.fullmatch(r"A\d{3}_.+", path.name))
    expected = list(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                    T1_A013_A016_RUN_IDS + T1_CHAIN_BASE_RUN_IDS + T1_CHAIN_DELTA_RUN_IDS)
    if all_run_dirs != expected:
        raise RuntimeError(f"chain run closure mismatch; expected {expected}, found {all_run_dirs}")
    base_packages, existing_refs, base_member_hashes = verify_t1_a017_a019_checkpoint(root)
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    run_rows = {item.get("run_id"): item for item in manifest.get("runs", [])}
    batch = json.loads((SERIES / "analysis/t1-chain-20261009/BATCH_MANIFEST.json").read_text(encoding="utf-8"))
    results = json.loads((SERIES / "analysis/t1-chain-20261009/T1_CHAIN_RESULTS.json").read_text(encoding="utf-8"))
    if (batch.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            batch.get("authorized_run_ids") != list(T1_CHAIN_DELTA_RUN_IDS) or
            batch.get("physical_solve_count_completed") != 3 or
            results.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            results.get("physical_solve_count") != 3):
        raise RuntimeError("A020-A022 batch/summary is not mechanically closed")
    chain_refs = []
    raw_sha_by_run = {}
    run_status = {}
    for run_id in T1_CHAIN_DELTA_RUN_IDS:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        raw_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
        provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
        plot_qa = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        raw_sha = root.sha256(raw)
        if (result.get("run_id") != run_id or result.get("artifact_status") != "VALID" or
                result.get("physical_solve_count") != 1 or result.get("raw_sha256") != raw_sha or
                qa.get("status") != "PASS" or qa.get("raw_sha256_before_analysis") != raw_sha or
                raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != raw_sha or
                plot_qa.get("status") != "PASS" or plot_qa.get("raw_sha256_after") != raw_sha or
                provenance.get("raw_sha256") != raw_sha or
                not run_rows.get(run_id) or run_rows[run_id].get("raw_sha256") != raw_sha):
            raise RuntimeError(f"A020-A022 raw/provenance/mechanical QA identity failed: {run_id}")
        for page in plot_qa.get("pages", []):
            plot_path = SERIES / page["path"]
            if not plot_path.is_file() or root.sha256(plot_path) != page.get("sha256"):
                raise RuntimeError(f"chain visualization QA/raw link mismatch: {run_id}/{page.get('path')}")
        raw_sha_by_run[run_id] = raw_sha
        run_status[run_id] = {"status": result.get("status"), "artifact_status": result.get("artifact_status"),
                              "physical_solve_count": result.get("physical_solve_count"), "qa_status": qa.get("status")}
        chain_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv", "raw_sha256": raw_sha,
                           "source_package_name": "THIS_DELTA", "source_package_sha256": "BOUND_AFTER_ARCHIVE"})
    sources, changes, excluded_html = _t1_chain_delta_sources(root)
    return {"base_packages": base_packages, "existing_raw_refs": existing_refs,
            "base_member_hashes": base_member_hashes, "raw_sha256_by_run": raw_sha_by_run,
            "run_artifact_status_by_run": run_status, "chain_raw_refs": chain_refs,
            "sources": sources, "changes": changes, "excluded_html": excluded_html,
            "batch": batch, "results": results}


def t1_chain_delta_specs(tag: str, root: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not root.TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid chain DELTA tag: {tag!r}")
    context = validate_t1_chain_scope(root)
    changes = context["changes"]
    sources = context["sources"]
    experiment_manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    limit_audit = {
        "recorded_physical_solve_count": experiment_manifest.get("physical_solve_count"),
        "declared_maximum_physical_solve_count": experiment_manifest.get("maximum_physical_solve_count"),
        "status": ("EXCEEDED_PRESERVED" if int(experiment_manifest.get("physical_solve_count", 0)) >
                   int(experiment_manifest.get("maximum_physical_solve_count", 0)) else "WITHIN_DECLARED_MAXIMUM"),
        "manifest_modified_by_packaging": False,
    }
    shared = [(source, member) for source, member in sources
              if Path(member).parts[:4] != ("test", "exploration", SERIES.name, "runs")]
    run_files = {run_id: [(source, member) for source, member in sources
                          if Path(member).parts[:5] == ("test", "exploration", SERIES.name, "runs", run_id)]
                 for run_id in T1_CHAIN_DELTA_RUN_IDS}
    if not shared or any(not group for group in run_files.values()):
        raise RuntimeError("chain DELTA must have source metadata and one evidence group per new raw")
    groups = [("source", "source", shared, None, 0)]
    all_run_evidence = []
    for run_id in T1_CHAIN_DELTA_RUN_IDS:
        evidence = [(source, member) for source, member in run_files[run_id]
                    if Path(member).name != "raw.csv"]
        raw = [(source, member) for source, member in run_files[run_id]
               if Path(member).name == "raw.csv"]
        if len(raw) != 1 or not evidence:
            raise RuntimeError(f"chain run must split into one raw and non-empty metadata: {run_id}")
        all_run_evidence.extend(evidence)
    groups.append(("runs_metadata", "evidence", all_run_evidence, None, 3))
    for run_id in T1_CHAIN_DELTA_RUN_IDS:
        groups.append((f"{run_id}_raw", "raw", [item for item in run_files[run_id]
                                                       if Path(item[1]).name == "raw.csv"], run_id, 0))
    specs, package_plans = [], []
    for group_name, group_kind, group_sources, run_id, solve_count in groups:
        source_records = root.file_records(group_sources)
        source_bytes = sum(record["bytes"] for record in source_records)
        included_hashes = {record["archive_path"]: record["sha256"] for record in source_records}
        new_files, modified_files = [], []
        for record in source_records:
            member = record["archive_path"]
            status = changes.get(member, "??")
            if status in {"A", "??"} or member not in context["base_member_hashes"]:
                new_files.append(member)
            else:
                modified_files.append(member)
        package_name = f"{SERIES.name}_delta_T1_CHAIN_A020_A022_{tag}_{group_name}.zip"
        target = HANDOFF / package_name
        qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable chain DELTA package: {package_name}")
        raw_map = ({run_id: context["raw_sha256_by_run"][run_id]} if group_kind == "raw" and run_id else {})
        associated_raw = ({run_id: context["raw_sha256_by_run"][run_id]
                           for run_id in T1_CHAIN_DELTA_RUN_IDS} if group_kind == "evidence" else {})
        base_refs = context["existing_raw_refs"]
        manifest = {
            "schema": "bvm-4x4-t1-chain-evidence-delta-v1",
            "package_type": "directory_snapshot_delta",
            "package_group": group_name,
            "base_commit": T1_CHAIN_BASE_COMMIT,
            "head_commit": "PENDING_EVIDENCE_COMMIT",
            "base_package_name": T1_CHAIN_BASE_SOURCE_NAME,
            "base_package_sha256": T1_CHAIN_BASE_SOURCE_SHA256,
            "base_package_source_commit": T1_CHAIN_BASE_SOURCE_HEAD,
            "base_delta_packages": context["base_packages"],
            "referenced_existing_cases": base_refs,
            "referenced_existing_raw_sha256": base_refs,
            "included_files": source_records,
            "included_file_sha256": included_hashes,
            "new_files": sorted(new_files),
            "modified_files": sorted(modified_files),
            "deleted_files": [],
            "new_physical_solve_count": solve_count,
            "reused_point_count": 0,
            "raw_sha256_by_run": raw_map,
            "associated_raw_sha256_by_run": associated_raw,
            "paired_evidence_package_name": (f"{SERIES.name}_delta_T1_CHAIN_A020_A022_{tag}_runs_metadata.zip"
                                             if group_kind == "raw" and run_id else None),
            "run_artifact_status_by_run": ({run_id: context["run_artifact_status_by_run"][run_id]}
                                            if run_id else context["run_artifact_status_by_run"]),
            "preexisting_experiment_manifest_limit_audit": limit_audit,
            "excluded_html": context["excluded_html"],
            "generated_from_head": git("rev-parse", "HEAD"),
            "scientific_interpretation_performed": False,
        }
        extra = {"DELTA_MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")}
        if source_bytes + sum(len(value) for value in extra.values()) >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"{group_name} chain DELTA exceeds the 100MB uncompressed guard: {source_bytes}")
        spec = {"name": package_name, "kind": "bvm_4x4_t1_chain_delta_v1", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": group_sources,
                "extra_members": extra,
                "readme": (f"Incremental evidence DELTA for {SERIES.name}; tag={tag}; group={group_name}.\n"
                           f"Base checkpoint: {T1_CHAIN_BASE_SOURCE_NAME} ({T1_CHAIN_BASE_SOURCE_SHA256})\n"
                           "A001-A019 raw is referenced by exact package/raw SHA; it is not recopied.\n"
                           "This package contains only new source/config, run metadata, or one raw file.\n"
                           "Large raw files are split from their run metadata so each uncompressed group stays below the ordinary Git file guard.\n"
                           "Generated HTML is excluded; no scientific interpretation.\n").encode(),
                "base_name": T1_CHAIN_BASE_SOURCE_NAME, "base_sha": T1_CHAIN_BASE_SOURCE_SHA256,
                "raw_by_run": raw_map, "delta_manifest": manifest, "group_kind": group_kind,
                "run_id": run_id}
        specs.append(spec)
        package_plans.append({"package": package_name, "group": group_name,
                              "group_kind": group_kind,
                              "new_raw_files": [f"runs/{run_id}/raw.csv"] if group_kind == "raw" else [],
                              "raw_sha256_by_run": raw_map, "new_physical_solve_count": solve_count,
                              "source_file_count": len(group_sources), "uncompressed_source_bytes": source_bytes,
                              "raw_bytes": sum(record["bytes"] for record in source_records
                                               if Path(record["archive_path"]).name == "raw.csv"),
                              "new_files": sorted(new_files), "modified_files": sorted(modified_files),
                              "qa": qa_target.relative_to(REPO).as_posix()})
    plan = {"base_commit": T1_CHAIN_BASE_COMMIT,
            "generated_from_head": git("rev-parse", "HEAD"),
            "base_package_name": T1_CHAIN_BASE_SOURCE_NAME,
            "base_package_sha256": T1_CHAIN_BASE_SOURCE_SHA256,
            "base_package_source_commit": T1_CHAIN_BASE_SOURCE_HEAD,
            "base_delta_packages": context["base_packages"],
            "referenced_existing_cases": context["existing_raw_refs"],
            "new_physical_solve_count": 3, "reused_point_count": 0,
            "html_included": False, "excluded_html_count": len(context["excluded_html"]),
            "total_uncompressed_source_bytes": sum(item["uncompressed_source_bytes"] for item in package_plans),
            "package_count": len(specs), "packages": package_plans,
            "run_artifact_status_by_run": context["run_artifact_status_by_run"]}
    return specs, {"plan": plan, "source_paths": [member for _source, member in sources],
                   "total_new_physical_solve_count": 3,
                   "referenced_existing_cases": context["existing_raw_refs"]}


def cb_direct_d1_delta_specs(tag: str, root: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not root.TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid CB_DIRECT D1 DELTA tag: {tag!r}")
    context = validate_cb_direct_d1_scope(root)
    sources = context["sources"]
    changes = context["changes"]
    shared = context["shared_sources"]
    run_files = context["run_files"]
    if not shared or any(not group for group in run_files.values()):
        raise RuntimeError("CB_DIRECT D1 DELTA requires source metadata and both run evidence groups")

    groups: list[tuple[str, str, list[tuple[Path, str]], str | None, int]] = [
        ("source", "source", shared, None, 0)]
    run_metadata = []
    for run_id in CB_DIRECT_D1_RUN_IDS:
        evidence = [(source, member) for source, member in run_files[run_id]
                    if Path(member).name != "raw.csv"]
        raw = [(source, member) for source, member in run_files[run_id]
               if Path(member).name == "raw.csv"]
        if len(raw) != 1 or not evidence:
            raise RuntimeError(f"run delta must contain one immutable raw and non-empty metadata: {run_id}")
        run_metadata.extend(evidence)
    groups.append(("runs_metadata", "evidence", run_metadata, None, 2))
    for run_id in CB_DIRECT_D1_RUN_IDS:
        groups.append((f"{run_id}_raw", "raw", [item for item in run_files[run_id]
                                                     if Path(item[1]).name == "raw.csv"], run_id, 0))

    specs: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    for group_name, group_kind, group_sources, run_id, solve_count in groups:
        records = root.file_records(group_sources)
        source_bytes = sum(item["bytes"] for item in records)
        included_hashes = {item["archive_path"]: item["sha256"] for item in records}
        new_files, modified_files = [], []
        for record in records:
            member, digest = record["archive_path"], record["sha256"]
            if member not in context["base_member_hashes"]:
                new_files.append(member)
            elif context["base_member_hashes"][member] != digest:
                modified_files.append(member)
        package_name = f"{SERIES.name}_delta_CB_DIRECT_D1_{tag}_{group_name}.zip"
        target = HANDOFF / package_name
        qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable CB_DIRECT D1 DELTA package: {package_name}")
        raw_map = ({run_id: context["raw_sha256_by_run"][run_id]}
                   if group_kind == "raw" and run_id else {})
        associated_raw = ({item: context["raw_sha256_by_run"][item]
                           for item in CB_DIRECT_D1_RUN_IDS} if group_kind == "evidence" else {})
        manifest = {
            "schema": "bvm-4x4-cb-direct-d1-evidence-delta-v1",
            "package_type": "directory_snapshot_delta",
            "package_group": group_name,
            "base_commit": CB_DIRECT_D1_BASE_COMMIT,
            "head_commit": "PENDING_EVIDENCE_COMMIT",
            "base_package_name": CB_DIRECT_D1_BASE_SOURCE_NAME,
            "base_package_sha256": CB_DIRECT_D1_BASE_SOURCE_SHA256,
            "base_package_source_commit": CB_DIRECT_D1_BASE_COMMIT,
            "base_delta_packages": context["base_packages"],
            "base_run_packages": context["existing_raw_refs"],
            "referenced_existing_cases": context["existing_raw_refs"],
            "referenced_existing_raw_sha256": context["existing_raw_refs"],
            "included_files": records,
            "included_file_sha256": included_hashes,
            "new_files": sorted(new_files),
            "modified_files": sorted(modified_files),
            "deleted_files": [],
            "new_physical_solve_count": solve_count,
            "reused_point_count": 0,
            "raw_sha256_by_run": raw_map,
            "associated_raw_sha256_by_run": associated_raw,
            "paired_evidence_package_name": (f"{SERIES.name}_delta_CB_DIRECT_D1_{tag}_runs_metadata.zip"
                                             if group_kind == "raw" else None),
            "run_artifact_status_by_run": ({run_id: context["run_artifact_status_by_run"][run_id]}
                                            if run_id else context["run_artifact_status_by_run"]),
            "excluded_html": context["excluded_html"],
            "generated_from_head": git("rev-parse", "HEAD"),
            "scientific_interpretation_performed": False,
        }
        extra = {"DELTA_MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")}
        if source_bytes + sum(len(value) for value in extra.values()) >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"{group_name} CB_DIRECT D1 package exceeds the 100MB uncompressed guard: {source_bytes}")
        spec = {"name": package_name, "kind": "bvm_4x4_cb_direct_d1_delta_v1", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": group_sources,
                "extra_members": extra, "delta_manifest": manifest,
                "readme": (f"Incremental CB_DIRECT D1 evidence for {SERIES.name}; tag={tag}; group={group_name}.\n"
                           f"Base checkpoint source: {CB_DIRECT_D1_BASE_SOURCE_NAME} ({CB_DIRECT_D1_BASE_SOURCE_SHA256})\n"
                           "A001-A022 raw is referenced by exact package/raw SHA and is not recopied.\n"
                           "Only A023/A024 are new physical solves. Generated HTML is excluded.\n"
                           "Mechanical evidence only; no event classification or scientific interpretation.\n").encode(),
                "base_name": CB_DIRECT_D1_BASE_SOURCE_NAME,
                "base_sha": CB_DIRECT_D1_BASE_SOURCE_SHA256,
                "raw_by_run": raw_map, "group_kind": group_kind, "run_id": run_id}
        specs.append(spec)
        plans.append({"package": package_name, "group": group_name, "group_kind": group_kind,
                      "source_file_count": len(group_sources), "uncompressed_source_bytes": source_bytes,
                      "raw_bytes": sum(item["bytes"] for item in records if Path(item["archive_path"]).name == "raw.csv"),
                      "raw_sha256_by_run": raw_map, "new_physical_solve_count": solve_count,
                      "new_files": sorted(new_files), "modified_files": sorted(modified_files),
                      "qa": qa_target.relative_to(REPO).as_posix()})
    plan = {"base_commit": CB_DIRECT_D1_BASE_COMMIT,
            "generated_from_head": git("rev-parse", "HEAD"),
            "base_package_name": CB_DIRECT_D1_BASE_SOURCE_NAME,
            "base_package_sha256": CB_DIRECT_D1_BASE_SOURCE_SHA256,
            "base_delta_packages": context["base_packages"],
            "referenced_existing_raw_count": len(context["existing_raw_refs"]),
            "referenced_existing_raw_sha256": context["existing_raw_refs"],
            "new_physical_solve_count": 2, "reused_point_count": 0,
            "html_included": False, "excluded_html_count": len(context["excluded_html"]),
            "total_uncompressed_source_bytes": sum(item["uncompressed_source_bytes"] for item in plans),
            "package_count": len(specs), "packages": plans,
            "run_artifact_status_by_run": context["run_artifact_status_by_run"]}
    return specs, {"plan": plan, "source_paths": [member for _source, member in sources],
                   "new_physical_solve_count": 2,
                   "referenced_existing_raw": context["existing_raw_refs"]}


def delta_specs(tag: str, root: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not root.TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid delta tag: {tag!r}")
    metadata, legacy_raw_refs = base_records(root)
    bus400_qa, _bus400_manifest, bus400_refs = verify_prior_bus400_delta(root, legacy_raw_refs)
    _prior_delta_qa, _prior_delta_manifest, a009_raw_refs = verify_prior_a009_delta(root, bus400_refs)
    a010_packages, a012_raw_refs, a012_hashes = verify_prior_a010_a012_checkpoint(root, a009_raw_refs)
    checkpoint_packages, existing_raw_refs, prior_hashes = verify_prior_t1_a013_a016_checkpoint(
        root, a010_packages, a012_raw_refs, a012_hashes)
    if git("rev-parse", "HEAD") != DELTA_BASE_COMMIT:
        raise RuntimeError(f"T1 delta requires exact checkpoint HEAD {DELTA_BASE_COMMIT}")
    sources, changed_paths, excluded_html = _delta_sources(root)
    current_sources = []
    for source, member in sources:
        digest = root.sha256(source)
        if prior_hashes.get(member) != digest:
            current_sources.append((source, member))
    if not current_sources:
        raise RuntimeError("delta has no source or evidence changes since the A013-A016 checkpoint")
    per_run_sources, shared_sources = partition_delta_sources(current_sources)
    current_head = git("rev-parse", "HEAD")
    run_raw_sha = {}
    run_artifact_status = {}
    for run_id in DELTA_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        run_raw_sha[run_id] = result["raw_sha256"]
        run_artifact_status[run_id] = {"status": result.get("status"),
                                       "artifact_status": result.get("artifact_status"),
                                       "physical_solve_count": result.get("physical_solve_count")}
    experiment_manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    manifest_limit_audit = {
        "recorded_physical_solve_count": experiment_manifest.get("physical_solve_count"),
        "declared_maximum_physical_solve_count": experiment_manifest.get("maximum_physical_solve_count"),
        "status": ("EXCEEDED_PRESERVED" if
                   int(experiment_manifest.get("physical_solve_count", 0)) >
                   int(experiment_manifest.get("maximum_physical_solve_count", 0)) else "WITHIN_DECLARED_MAXIMUM"),
        "manifest_modified_by_packaging": False,
    }
    groups = [("source", shared_sources, None)] + [
        (run_id, per_run_sources[run_id], run_id) for run_id in DELTA_RUN_IDS]
    specs, plans = [], []
    for label, group_sources, run_id in groups:
        if not group_sources:
            raise RuntimeError(f"delta package group is empty: {label}")
        source_records = root.file_records(group_sources)
        source_bytes = sum(record["bytes"] for record in source_records)
        included_hashes = {record["archive_path"]: record["sha256"] for record in source_records}
        new_files, modified_files = [], []
        for record in source_records:
            member, digest = record["archive_path"], record["sha256"]
            if member not in prior_hashes:
                new_files.append(member)
            elif prior_hashes[member] != digest:
                modified_files.append(member)
        package_name = f"{SERIES.name}_delta_{tag}_{label}.zip"
        target = HANDOFF / package_name
        qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable delta package: {package_name}")
        package_raw_sha = {run_id: run_raw_sha[run_id]} if run_id else {}
        solve_count = 1 if run_id else 0
        manifest = {
            "schema": "bvm-4x4-incremental-evidence-delta-v3",
            "package_type": "directory_snapshot_delta",
            "package_group": label,
            "base_commit": DELTA_BASE_COMMIT,
            "head_commit": "PENDING_EVIDENCE_COMMIT",
            "base_package_name": DELTA_BASE_PACKAGE_NAME,
            "base_package_sha256": DELTA_BASE_PACKAGE_SHA256,
            "base_package_source_commit": DELTA_BASE_PACKAGE_SOURCE_HEAD,
            "base_delta_packages": checkpoint_packages,
            "base_metadata_package_name": BASE_METADATA_NAME,
            "base_metadata_package_sha256": metadata["package_sha256"],
            "base_metadata_source_commit": metadata["source_commit"],
            "base_run_packages": existing_raw_refs,
            "included_files": source_records,
            "included_file_sha256": included_hashes,
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": [],
            "referenced_existing_cases": existing_raw_refs,
            "referenced_existing_raw_sha256": existing_raw_refs,
            "new_physical_solve_count": solve_count,
            "reused_point_count": 0,
            "raw_sha256_by_run": package_raw_sha,
            "run_artifact_status_by_run": ({run_id: run_artifact_status[run_id]} if run_id else
                                            run_artifact_status),
            "preexisting_experiment_manifest_limit_audit": manifest_limit_audit,
            "excluded_html": excluded_html,
            "generated_from_head": current_head,
        }
        extra = {"DELTA_MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}
        if source_bytes + sum(len(value) for value in extra.values()) >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"{label} delta exceeds the 100MB uncompressed archive guard: {source_bytes}")
        spec = {"name": package_name, "kind": "bvm_4x4_evidence_delta_v1", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": group_sources,
                "extra_members": extra, "delta_manifest": manifest,
                "readme": (f"Incremental evidence delta for {SERIES.name}; tag={tag}; group={label}.\n"
                           f"Base delta: {DELTA_BASE_PACKAGE_NAME} ({DELTA_BASE_PACKAGE_SHA256})\n"
                           f"Base source HEAD: {DELTA_BASE_COMMIT}\n"
                           f"Batch additions: {', '.join(DELTA_RUN_IDS)}.\n"
                           "A001-A016 raw is referenced by exact package/raw SHA; no previous raw is copied again.\n"
                           "A017 postprocess-invalid raw is preserved and clearly tagged INVALID in the manifest.\n"
                           "Generated HTML is excluded. No scientific interpretation.\n").encode(),
                "excluded_files": excluded_html, "base_name": DELTA_BASE_PACKAGE_NAME,
                "base_sha": DELTA_BASE_PACKAGE_SHA256, "raw_by_run": package_raw_sha}
        specs.append(spec)
        plans.append({"package": package_name, "group": label,
                      "new_raw_files": [f"runs/{run_id}/raw.csv"] if run_id else [],
                      "raw_sha256_by_run": package_raw_sha,
                      "run_artifact_status_by_run": ({run_id: run_artifact_status[run_id]} if run_id else
                                                      run_artifact_status),
                      "raw_bytes_by_run": {run_id: (RUNS / run_id / "raw.csv").stat().st_size} if run_id else {},
                      "new_physical_solve_count": solve_count,
                      "source_file_count": len(group_sources),
                      "uncompressed_source_bytes": source_bytes,
                      "new_files": new_files, "modified_files": modified_files,
                      "qa": qa_target.relative_to(REPO).as_posix()})
    plan = {"base_commit": DELTA_BASE_COMMIT,
            "generated_from_head": current_head,
            "base_package_name": DELTA_BASE_PACKAGE_NAME,
            "base_package_sha256": DELTA_BASE_PACKAGE_SHA256,
            "base_delta_packages": checkpoint_packages,
            "base_metadata_package": BASE_METADATA_NAME,
            "base_metadata_sha256": metadata["package_sha256"],
            "packages": plans,
            "run_artifact_status_by_run": run_artifact_status,
            "referenced_existing_cases": existing_raw_refs,
            "new_physical_solve_count": len(DELTA_RUN_IDS),
            "reused_point_count": 0,
            "experiment_manifest_limit_audit": manifest_limit_audit,
            "excluded_html_count": len(excluded_html), "html_included": False,
            "total_uncompressed_source_bytes": sum(item["uncompressed_source_bytes"] for item in plans),
            "package_count": len(specs)}
    return specs, {"plan": plan, "source_paths": [rel for _, rel in sources],
                   "total_new_physical_solve_count": len(DELTA_RUN_IDS),
                   "referenced_existing_cases": existing_raw_refs}


def validate_scope(*, delta: bool = False) -> None:
    root = load_root_submit()
    if delta and git("rev-parse", "HEAD") != DELTA_BASE_COMMIT:
        raise RuntimeError(f"T1 delta requires exact checkpoint HEAD {DELTA_BASE_COMMIT}")
    changes = dict(root.committed_changes(DELTA_BASE_COMMIT, git("rev-parse", "HEAD"))) if delta else {}
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    allowed = lambda path: root.in_scope(path, [SERIES]) or path in DELTA_GLOBAL_PATHS
    outside = sorted(path for path in changes if not allowed(path))
    if outside:
        raise RuntimeError("unrelated worktree changes outside this experiment: " + ", ".join(outside))
    if not RUNS.is_dir():
        raise RuntimeError("runs/ is missing; no completed physical batch found")
    run_dirs = sorted(path for path in RUNS.iterdir() if path.is_dir() and path.name.startswith("A"))
    expected = (list(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                     PREVIOUS_DELTA_RUN_IDS + DELTA_RUN_IDS) if delta else list(LEGACY_RUN_IDS))
    if [path.name for path in run_dirs] != expected:
        raise RuntimeError(f"run closure mismatch; expected {expected}, found {[p.name for p in run_dirs]}")
    check_dirs = [RUNS / run_id for run_id in DELTA_RUN_IDS] if delta else run_dirs
    for path in check_dirs:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        if result.get("run_id") != path.name:
            raise RuntimeError(f"run/result identity mismatch: {path.name}")
        if int(result.get("physical_solve_count", 0)) != 1:
            raise RuntimeError(f"run physical_solve_count is not one: {path.name}")
        raw = path / "raw.csv"
        if not raw.is_file() or root.sha256(raw) != result.get("raw_sha256"):
            raise RuntimeError(f"new raw does not match its result identity: {path.name}")
        if path.name in INVALID_PRESERVED_DELTA_RUN_IDS:
            static_qa = json.loads((path / "static_qa.json").read_text(encoding="utf-8"))
            probe = json.loads((path / "probe_manifest.json").read_text(encoding="utf-8"))
            log_text = (path / "run.log").read_text(encoding="utf-8")
            if (result.get("status") != "POSTPROCESS_FAILURE_RAW_PRESERVED" or
                    result.get("artifact_status") != "INVALID" or
                    "raw is missing required probes" not in result.get("error", "") or
                    static_qa.get("status") != "PASS" or
                    probe.get("profile") != "focus" or
                    "I(R_TERM_D0)" not in {item.get("label") for item in probe.get("signals", [])} or
                    "solver_exit_code=0" not in log_text or
                    f"raw_sha256={result['raw_sha256']}" not in log_text):
                raise RuntimeError("A017 invalid raw is not the expected preserved postprocess-failure artifact")
        else:
            qa = json.loads((path / "qa.json").read_text(encoding="utf-8"))
            t1_qa = json.loads((path / "t1_array_qa.json").read_text(encoding="utf-8"))
            if (result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                    t1_qa.get("status") != "PASS" or
                    qa.get("raw_sha256_before_analysis") != result.get("raw_sha256") or
                    t1_qa.get("raw_sha256_after_analysis") != result.get("raw_sha256") or
                    raw.stat().st_size != result.get("raw_bytes")):
                raise RuntimeError(f"run is not mechanically valid: {path.name}")
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    recorded = {item.get("run_id"): item for item in manifest.get("runs", [])}
    for path in check_dirs:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        row = recorded.get(path.name)
        if not row or row.get("raw_sha256") != result.get("raw_sha256"):
            raise RuntimeError(f"experiment_manifest raw identity missing/mismatched: {path.name}")
    if delta:
        batch = json.loads((SERIES / "analysis/t1-array-20261009/BATCH_MANIFEST.json").read_text(encoding="utf-8"))
        if (batch.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
                batch.get("authorized_run_ids") != list(T1_A013_A016_RUN_IDS) or
                batch.get("physical_solve_count_completed") != len(T1_A013_A016_RUN_IDS)):
            raise RuntimeError("registered A013-A016 T1 batch checkpoint is not closed")


def package_specs(tag: str, root: Any, *, dry_run: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_dirs = sorted(path for path in RUNS.iterdir() if path.is_dir() and path.name.startswith("A"))
    meta_paths = [path for path in included_files(SERIES)
                  if path.relative_to(SERIES).parts[0] not in {"runs", "plots"}]
    specs = []
    plan = []
    all_raw: dict[str, str] = {}
    for run_dir in run_dirs:
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        raw_hash = result.get("raw_sha256")
        if not isinstance(raw_hash, str) or len(raw_hash) != 64 or raw.stat().st_size == 0:
            raise RuntimeError(f"run result/raw identity is incomplete: {run_dir.name}")
        if result.get("raw_bytes") != raw.stat().st_size:
            raise RuntimeError(f"raw byte count disagrees with result manifest: {run_dir.name}")
        all_raw[run_dir.name] = raw_hash
        paths = included_files(run_dir)
        sources = [(path, path.relative_to(SERIES).as_posix()) for path in paths]
        uncompressed = sum(path.stat().st_size for path in paths)
        if uncompressed >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"single run bundle exceeds 100MB guard: {run_dir.name} ({uncompressed} bytes)")
        name = f"{SERIES.name}_raw_handoff_{run_dir.name}_{tag}.zip"
        target = HANDOFF / name
        qa_target = HANDOFF / f"{Path(name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable package {name}")
        raw_map = {run_dir.name: raw_hash}
        spec = {"name": name, "kind": "directory_snapshot", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": sources,
                "extra_members": {}, "excluded_files": [],
                "readme": (f"One-run evidence snapshot for {run_dir.name}.\n"
                           f"Raw SHA-256: {raw_hash}\n"
                           "Generated HTML is intentionally excluded and remains local.\n"
                           "Mechanical artifact QA only; no scientific interpretation.\n").encode(),
                "base_name": None, "base_sha": None, "raw_by_run": raw_map}
        specs.append(spec)
        plan.append({"name": name, "file_count": len(paths), "uncompressed_bytes": uncompressed,
                     "raw_bytes": raw.stat().st_size, "new_physical_solve_count": result["physical_solve_count"]})

    metadata_sources = [(path, path.relative_to(SERIES).as_posix()) for path in meta_paths]
    metadata_bytes = sum(path.stat().st_size for path in meta_paths)
    if metadata_bytes >= root.MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"shared metadata bundle exceeds 100MB guard: {metadata_bytes} bytes")
    metadata_name = f"{SERIES.name}_metadata_{tag}.zip"
    metadata_target = HANDOFF / metadata_name
    metadata_qa = HANDOFF / f"{Path(metadata_name).stem}_PACKAGE_QA.json"
    if metadata_target.exists() or metadata_qa.exists():
        raise FileExistsError(f"refusing to overwrite immutable package {metadata_name}")
    metadata_spec = {"name": metadata_name, "kind": "directory_snapshot", "scope": SERIES,
                     "target": metadata_target, "qa_path": metadata_qa,
                     "sources": metadata_sources, "extra_members": {}, "excluded_files": [],
                     "readme": (f"Shared metadata snapshot for {SERIES.name}.\n"
                                f"Authorized runs: {', '.join(all_raw)}\n"
                                "Per-run raw files are stored only in their own handoff archives.\n"
                                "Generated HTML/Plotly JS and historical artifacts are excluded.\n"
                                "No new physical solve or scientific interpretation by packaging.\n").encode(),
                     "base_name": None, "base_sha": None, "raw_by_run": all_raw}
    specs.append(metadata_spec)
    plan.append({"name": metadata_name, "file_count": len(meta_paths),
                 "uncompressed_bytes": metadata_bytes, "raw_bytes": 0,
                 "new_physical_solve_count": 0})
    excluded_html = [p.relative_to(SERIES).as_posix() for p in SERIES.rglob("*.html") if p.is_file()]
    if dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "head": git("rev-parse", "HEAD"),
                          "package_count": len(specs), "raw_references_not_copied": [],
                          "excluded_html_count": len(excluded_html),
                          "html_included": False, "new_physical_solve_count_in_package": 6,
                          "packages": plan,
                          "notes": ["New experiment has no previous archive base; run archives are standalone snapshots.",
                                    "Shared metadata archive contains no raw.csv; each raw is included once in its run archive."]},
                         ensure_ascii=False, indent=2))
    return specs, {"plan": plan, "excluded_html": excluded_html, "raw_sha256_by_run": all_raw}


def update_summary_with_packages(results: list[dict[str, Any]], package_table_marker: str = "<!-- PACKAGE_TABLE -->") -> None:
    summary = SERIES / "BATCH_SUMMARY.md"
    text = summary.read_text(encoding="utf-8")
    rows = ["| Archive | Bytes | SHA-256 |", "|---|---:|---|"]
    for item in results:
        name = Path(item["path"]).name
        rows.append(f"| `{name}` | {item['bytes']} | `{item['sha256']}` |")
    total = sum(int(item["bytes"]) for item in results)
    replacement = (f"{package_table_marker}\n" + "\n".join(rows) +
                   f"\n\nSix per-run ZIP total: **{total:,} bytes**.\n"
                   "<!-- METADATA_PACKAGE -->\n"
                   "The metadata ZIP carries this run-package table; its own identity is appended below after creation.\n"
                   "Each ZIP's detached PACKAGE_QA.json is the member/CRC/SHA authority.\n")
    if package_table_marker not in text:
        raise RuntimeError("BATCH_SUMMARY package table marker is missing")
    summary.write_text(text.replace(package_table_marker, replacement), encoding="utf-8")


def submit_metadata_v2(args: argparse.Namespace, root: Any) -> int:
    summary = SERIES / "BATCH_SUMMARY.md"
    package_name = f"{SERIES.name}_metadata_v2_{args.tag}.zip"
    target = HANDOFF / package_name
    qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
    if target.exists() or qa_target.exists():
        raise FileExistsError(f"refusing to overwrite immutable metadata-v2 package {package_name}")
    metadata_paths = [path for path in included_files(SERIES)
                      if path.relative_to(SERIES).parts[0] not in {"runs", "plots"}]
    source_bytes = sum(path.stat().st_size for path in metadata_paths)
    if source_bytes >= root.MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"metadata-v2 input exceeds 100MB guard: {source_bytes}")
    rel_paths = [path.relative_to(REPO).as_posix() for path in metadata_paths]
    if rel_paths:
        subprocess.run(["git", "add", "-A", "-f", "--", *rel_paths], cwd=REPO, check=True)
    staged_empty = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                   cwd=REPO, check=False).returncode == 0
    if not staged_empty:
        subprocess.run(["git", "commit", "-m", "docs: supersede unbound 4x4 metadata archive"],
                       cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")
    raw_by_run = {d.name: json.loads((d / "result.json").read_text(encoding="utf-8"))["raw_sha256"]
                  for d in sorted(RUNS.iterdir()) if d.is_dir() and d.name.startswith("A")}
    sources = [(path, path.relative_to(SERIES).as_posix()) for path in metadata_paths]
    spec = {"name": package_name, "kind": "directory_snapshot", "scope": SERIES,
            "target": target, "qa_path": qa_target, "sources": sources,
            "extra_members": {}, "excluded_files": [],
            "readme": (f"Bound shared metadata v2 for {SERIES.name}.\n"
                       f"Source commit: {source_commit}\n"
                       "Supersedes only the unbound first metadata snapshot; all six raw-run ZIPs are unchanged.\n"
                       "No new physical solve or scientific interpretation.\n").encode(),
            "base_name": None, "base_sha": None, "raw_by_run": raw_by_run}
    result = root.archive_bundle(spec, source_commit)
    subprocess.run(["git", "add", "-f", "--", result["path"], result["qa_path"]], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", "package: add bound 4x4 metadata v2"], cwd=REPO, check=True)
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
    mirror = root.copy_mirror([target], Path(args.mirror_dir).expanduser().resolve())
    print(json.dumps({"status": "METADATA_V2_COMPLETE", "source_commit": source_commit,
                      "final_commit": git("rev-parse", "HEAD"), "push": "SKIPPED" if args.no_push else "PASS",
                      "supersedes": "metadata_BVM4X4_20261009.zip",
                      "package": result, "mirror": mirror}, ensure_ascii=False, indent=2))
    return 0


def submit_delta(args: argparse.Namespace, root: Any) -> int:
    validate_scope(delta=True)
    specs, context = delta_specs(args.tag, root)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if not mirror_dir.is_dir():
        raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
    collisions = [str(mirror_dir / spec["name"]) for spec in specs
                  if (mirror_dir / spec["name"]).exists()]
    if collisions:
        raise FileExistsError("same-name mirror target already exists: " + ", ".join(collisions))
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "package_mode": "DELTA",
                          **context["plan"],
                          "push": "SKIPPED" if args.no_push else "bvm/master",
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    stage_paths = context["source_paths"]
    if stage_paths:
        subprocess.run(["git", "add", "-A", "-f", "--", *stage_paths], cwd=REPO, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO, check=False).returncode != 0:
        subprocess.run(["git", "commit", "-m", args.message or "experiment: record BVM4x4 T1 A017-A019 evidence"],
                       cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")

    # Bind each precomputed, hash-listed source group to the evidence commit.
    package_results = []
    for spec in specs:
        manifest = spec["delta_manifest"]
        if spec.get("group_kind") == "raw":
            evidence_name = manifest.get("paired_evidence_package_name")
            evidence_result = next((item for item in package_results
                                    if Path(item["path"]).name == evidence_name), None)
            if evidence_result is None:
                raise RuntimeError(f"paired run metadata package must be created before raw: {evidence_name}")
            manifest["paired_evidence_package_sha256"] = evidence_result["sha256"]
        manifest["head_commit"] = source_commit
        manifest["generated_from_head"] = source_commit
        spec["extra_members"]["DELTA_MANIFEST.json"] = (
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        package_result = root.archive_bundle(spec, source_commit)
        qa_path = REPO / package_result["qa_path"]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"package_mode": "DELTA_SPLIT_BY_RUN", "base_commit": manifest["base_commit"],
                   "head_commit": source_commit, "base_package_name": manifest["base_package_name"],
                   "base_package_sha256": manifest["base_package_sha256"],
                   "base_package_source_commit": manifest["base_package_source_commit"],
                   "base_delta_packages": manifest["base_delta_packages"],
                   "delta_included_files": manifest["included_files"],
                   "delta_included_file_sha256": manifest["included_file_sha256"],
                   "new_files": manifest["new_files"], "modified_files": manifest["modified_files"],
                   "referenced_existing_cases": manifest["referenced_existing_cases"],
                   "referenced_existing_raw_sha256": manifest["referenced_existing_raw_sha256"],
                   "new_physical_solve_count": manifest["new_physical_solve_count"],
                   "reused_point_count": manifest["reused_point_count"],
                   "html_included": False,
                   "package_group": manifest["package_group"],
                   "run_artifact_status_by_run": manifest["run_artifact_status_by_run"],
                   "preexisting_experiment_manifest_limit_audit": manifest["preexisting_experiment_manifest_limit_audit"],
                   "raw_sha256_by_run": manifest["raw_sha256_by_run"]})
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != root.sha256(spec["target"]) or
                qa.get("package_bytes") != spec["target"].stat().st_size):
            raise RuntimeError(f"delta PACKAGE_QA identity failed: {spec['name']}")
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package_results.append(package_result)

    package_paths = [path for result in package_results for path in (result["path"], result["qa_path"])]
    subprocess.run(["git", "add", "-f", "--", *package_paths], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"package: archive BVM4x4 T1 A017-A019 delta {args.tag}"],
                   cwd=REPO, check=True)
    push_status = "SKIPPED"
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        push_status = "PASS"
    mirror = root.copy_mirror([spec["target"] for spec in specs], mirror_dir)
    print(json.dumps({"status": "DELTA_SUBMIT_COMPLETE", "source_commit": source_commit,
                      "final_commit": git("rev-parse", "HEAD"), "push": push_status,
                      "packages": package_results,
                      "base_commit": specs[0]["delta_manifest"]["base_commit"],
                      "base_package": specs[0]["delta_manifest"]["base_package_name"],
                      "referenced_existing_raw_count": len(context["referenced_existing_cases"]),
                      "new_physical_solve_count": context["total_new_physical_solve_count"],
                      "mirror": mirror},
                     ensure_ascii=False, indent=2))
    return 0


def submit_t1_chain_delta(args: argparse.Namespace, root: Any) -> int:
    specs, context = t1_chain_delta_specs(args.tag, root)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if not mirror_dir.is_dir():
        raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
    collisions = [str(mirror_dir / spec["name"]) for spec in specs
                  if (mirror_dir / spec["name"]).exists()]
    if collisions:
        raise FileExistsError("same-name chain DELTA mirror target already exists: " + ", ".join(collisions))
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "package_mode": "T1_CHAIN_DELTA", **context["plan"],
                          "push": "SKIPPED" if args.no_push else git("rev-parse", "--abbrev-ref", "@{upstream}"),
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    source_paths = context["source_paths"]
    if source_paths:
        subprocess.run(["git", "add", "-A", "-f", "--", *source_paths], cwd=REPO, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO, check=False).returncode != 0:
        subprocess.run(["git", "commit", "-m", args.message or
                        "experiment: record BVM4x4 T1 chain A020-A022 evidence"], cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")

    package_results = []
    for spec in specs:
        manifest = spec["delta_manifest"]
        manifest["head_commit"] = source_commit
        manifest["generated_from_head"] = source_commit
        spec["extra_members"]["DELTA_MANIFEST.json"] = (
            json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
        package_result = root.archive_bundle(spec, source_commit)
        package_path = REPO / package_result["path"]
        qa_path = REPO / package_result["qa_path"]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"package_mode": "T1_CHAIN_DELTA_SPLIT_BY_RUN",
                   "base_commit": manifest["base_commit"], "head_commit": source_commit,
                   "base_package_name": manifest["base_package_name"],
                   "base_package_sha256": manifest["base_package_sha256"],
                   "base_package_source_commit": manifest["base_package_source_commit"],
                   "base_delta_packages": manifest["base_delta_packages"],
                   "delta_included_files": manifest["included_files"],
                   "delta_included_file_sha256": manifest["included_file_sha256"],
                   "new_files": manifest["new_files"], "modified_files": manifest["modified_files"],
                   "referenced_existing_cases": manifest["referenced_existing_cases"],
                   "referenced_existing_raw_sha256": manifest["referenced_existing_raw_sha256"],
                   "new_physical_solve_count": manifest["new_physical_solve_count"],
                   "reused_point_count": manifest["reused_point_count"],
                   "html_included": False, "package_group": manifest["package_group"],
                   "run_artifact_status_by_run": manifest["run_artifact_status_by_run"],
                   "raw_sha256_by_run": manifest["raw_sha256_by_run"],
                   "associated_raw_sha256_by_run": manifest.get("associated_raw_sha256_by_run", {}),
                   "paired_evidence_package_name": manifest.get("paired_evidence_package_name"),
                   "paired_evidence_package_sha256": manifest.get("paired_evidence_package_sha256")})
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != root.sha256(package_path) or
                qa.get("package_bytes") != package_path.stat().st_size):
            raise RuntimeError(f"chain DELTA PACKAGE_QA identity failed: {spec['name']}")
        with zipfile.ZipFile(package_path, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"chain DELTA archive CRC failure in {spec['name']}: {bad}")
            archived_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
            names = set(archive.namelist())
            for member, expected_sha in archived_manifest.get("included_file_sha256", {}).items():
                if member not in names:
                    raise RuntimeError(f"chain DELTA is missing declared archive member {member}")
                actual_sha = hashlib.sha256(archive.read(member)).hexdigest()
                if actual_sha != expected_sha:
                    raise RuntimeError(f"chain DELTA member SHA mismatch: {member}")
        if archived_manifest.get("head_commit") != source_commit:
            raise RuntimeError(f"chain DELTA manifest HEAD mismatch: {spec['name']}")
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        package_results.append(package_result)

    package_paths = [path for result in package_results for path in (result["path"], result["qa_path"])]
    subprocess.run(["git", "add", "-f", "--", *package_paths], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"package: archive BVM4x4 T1 chain A020-A022 delta {args.tag}"],
                   cwd=REPO, check=True)
    push_status = "SKIPPED"
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        push_status = "PASS"
    mirror = root.copy_mirror([spec["target"] for spec in specs], mirror_dir)
    print(json.dumps({"status": "T1_CHAIN_DELTA_SUBMIT_COMPLETE", "source_commit": source_commit,
                      "final_commit": git("rev-parse", "HEAD"), "push": push_status,
                      "packages": package_results, "base_commit": T1_CHAIN_BASE_COMMIT,
                      "base_package": T1_CHAIN_BASE_SOURCE_NAME,
                      "referenced_existing_raw_count": len(context["referenced_existing_cases"]),
                      "new_physical_solve_count": 3, "package_count": len(package_results),
                      "html_included": False, "mirror": mirror},
                     ensure_ascii=False, indent=2))
    return 0


def submit_cb_direct_d1_delta(args: argparse.Namespace, root: Any) -> int:
    specs, context = cb_direct_d1_delta_specs(args.tag, root)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if not mirror_dir.is_dir():
        raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
    local_collisions = [str(spec["target"]) for spec in specs
                        if spec["target"].exists() or spec["qa_path"].exists()]
    mirror_collisions = [str(mirror_dir / spec["name"]) for spec in specs
                         if (mirror_dir / spec["name"]).exists()]
    if local_collisions or mirror_collisions:
        raise FileExistsError("refusing to overwrite package/mirror targets: " +
                              ", ".join(local_collisions + mirror_collisions))
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "package_mode": "CB_DIRECT_D1_DELTA", **context["plan"],
                          "push": git("rev-parse", "--abbrev-ref", "@{upstream}"),
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    source_paths = context["source_paths"]
    if not source_paths:
        raise RuntimeError("CB_DIRECT D1 DELTA source inventory is empty")
    subprocess.run(["git", "add", "-A", "-f", "--", *source_paths], cwd=REPO, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO,
                      check=False).returncode != 0:
        subprocess.run(["git", "commit", "-m", args.message or
                        "experiment: record CB_DIRECT D1 A023-A024 evidence"], cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")

    package_results = []
    for spec in specs:
        manifest = spec["delta_manifest"]
        if spec.get("group_kind") == "raw":
            evidence_name = manifest.get("paired_evidence_package_name")
            evidence_result = next((item for item in package_results
                                    if Path(item["path"]).name == evidence_name), None)
            if evidence_result is None:
                raise RuntimeError(f"paired run-metadata package must be created before raw: {evidence_name}")
            manifest["paired_evidence_package_sha256"] = evidence_result["sha256"]
        manifest["head_commit"] = source_commit
        manifest["generated_from_head"] = source_commit
        spec["extra_members"]["DELTA_MANIFEST.json"] = (
            json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
        result = root.archive_bundle(spec, source_commit)
        package_path, qa_path = REPO / result["path"], REPO / result["qa_path"]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"package_mode": "CB_DIRECT_D1_DELTA_SPLIT_BY_RUN",
                   "base_commit": manifest["base_commit"], "head_commit": source_commit,
                   "base_package_name": manifest["base_package_name"],
                   "base_package_sha256": manifest["base_package_sha256"],
                   "base_delta_packages": manifest["base_delta_packages"],
                   "delta_included_files": manifest["included_files"],
                   "delta_included_file_sha256": manifest["included_file_sha256"],
                   "new_files": manifest["new_files"], "modified_files": manifest["modified_files"],
                   "referenced_existing_cases": manifest["referenced_existing_cases"],
                   "referenced_existing_raw_sha256": manifest["referenced_existing_raw_sha256"],
                   "new_physical_solve_count": manifest["new_physical_solve_count"],
                   "reused_point_count": 0, "html_included": False,
                   "package_group": manifest["package_group"],
                   "raw_sha256_by_run": manifest["raw_sha256_by_run"],
                   "associated_raw_sha256_by_run": manifest["associated_raw_sha256_by_run"],
                   "run_artifact_status_by_run": manifest["run_artifact_status_by_run"],
                   "paired_evidence_package_name": manifest.get("paired_evidence_package_name"),
                   "paired_evidence_package_sha256": manifest.get("paired_evidence_package_sha256")})
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != root.sha256(package_path) or
                qa.get("package_bytes") != package_path.stat().st_size):
            raise RuntimeError(f"CB_DIRECT D1 PACKAGE_QA identity failed: {spec['name']}")
        with zipfile.ZipFile(package_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"CB_DIRECT D1 ZIP CRC failure: {spec['name']}/{bad}")
            archived_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
            names = set(archive.namelist())
            if archived_manifest.get("head_commit") != source_commit:
                raise RuntimeError(f"CB_DIRECT D1 archived HEAD mismatch: {spec['name']}")
            for member, expected_sha in archived_manifest.get("included_file_sha256", {}).items():
                if member not in names:
                    raise RuntimeError(f"CB_DIRECT D1 package member missing: {member}")
                if hashlib.sha256(archive.read(member)).hexdigest() != expected_sha:
                    raise RuntimeError(f"CB_DIRECT D1 package member SHA mismatch: {member}")
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        result.update({"sha256": qa["package_sha256"], "bytes": qa["package_bytes"],
                       "status": qa["status"]})
        package_results.append(result)

    package_paths = [path for result in package_results for path in (result["path"], result["qa_path"])]
    subprocess.run(["git", "add", "-f", "--", *package_paths], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"package: archive CB_DIRECT D1 A023-A024 delta {args.tag}"],
                   cwd=REPO, check=True)
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        push_status = "PASS"
    else:
        push_status = "SKIPPED"
    mirror = root.copy_mirror([spec["target"] for spec in specs], mirror_dir)
    print(json.dumps({"status": "CB_DIRECT_D1_DELTA_SUBMIT_COMPLETE",
                      "source_commit": source_commit, "final_commit": git("rev-parse", "HEAD"),
                      "push": push_status, "packages": package_results,
                      "base_commit": CB_DIRECT_D1_BASE_COMMIT,
                      "base_package": CB_DIRECT_D1_BASE_SOURCE_NAME,
                      "referenced_existing_raw_count": len(context["referenced_existing_raw"]),
                      "new_physical_solve_count": 2, "package_count": len(package_results),
                      "html_included": False, "mirror": mirror}, ensure_ascii=False, indent=2))
    return 0


def _verify_cb_carry_buffer_base(root: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    packages, raw_refs, member_hashes = [], [], {}
    package_manifests = {}
    expected_run_ids = {f"A{i:03d}_{case}" for i, case in enumerate(
        ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4", "PAPER_1101_1101"), start=1)}
    expected_run_ids.update(BUS400_RUN_IDS + A009_RUN_IDS + A010_A012_RUN_IDS +
                            T1_A013_A016_RUN_IDS + T1_CHAIN_BASE_RUN_IDS +
                            T1_CHAIN_DELTA_RUN_IDS + CB_DIRECT_D1_RUN_IDS)
    for group, name, expected_sha in CB_CARRY_BUFFER_D1_BASE_PACKAGES:
        path = HANDOFF / name
        qa_path = HANDOFF / f"{Path(name).stem}_PACKAGE_QA.json"
        if not path.is_file() or root.sha256(path) != expected_sha:
            raise RuntimeError(f"CB_CARRY_BUFFER base package identity mismatch: {name}")
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_sha or
                qa.get("package_bytes") != path.stat().st_size):
            raise RuntimeError(f"CB_CARRY_BUFFER base PACKAGE_QA mismatch: {name}")
        with zipfile.ZipFile(path, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"CB_CARRY_BUFFER base ZIP CRC failure: {name}")
            delta = json.loads(archive.read("DELTA_MANIFEST.json"))
            for member, digest in delta.get("included_file_sha256", {}).items():
                if member not in archive.namelist() or hashlib.sha256(archive.read(member)).hexdigest() != digest:
                    raise RuntimeError(f"CB_CARRY_BUFFER base package member hash failure: {name}/{member}")
                if member in member_hashes and member_hashes[member] != digest:
                    raise RuntimeError(f"CB_CARRY_BUFFER base package has conflicting member identity: {member}")
                member_hashes[member] = digest
        if delta.get("head_commit") != CB_CARRY_BUFFER_D1_BASE_SOURCE_HEAD:
            raise RuntimeError(f"CB_CARRY_BUFFER base package source HEAD mismatch: {name}")
        package_manifests[name] = delta
        packages.append({"package_name": name, "package_sha256": expected_sha,
                         "package_group": group, "source_commit": delta["head_commit"]})

    source_manifest = package_manifests[CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME]
    old_refs = source_manifest.get("referenced_existing_raw_sha256", [])
    if len(old_refs) != 22 or {item.get("run_id") for item in old_refs} != expected_run_ids - set(CB_DIRECT_D1_RUN_IDS):
        raise RuntimeError("CB_CARRY_BUFFER source checkpoint must close exactly A001-A022 raw")
    raw_refs.extend(old_refs)
    for group, name, expected_zip_sha in CB_CARRY_BUFFER_D1_BASE_PACKAGES[2:]:
        delta = package_manifests[name]
        run_ids = delta.get("raw_sha256_by_run", {})
        if len(run_ids) != 1:
            raise RuntimeError(f"CB_DIRECT base raw package does not bind exactly one run: {name}")
        run_id, raw_sha = next(iter(run_ids.items()))
        if run_id not in CB_DIRECT_D1_RUN_IDS or delta.get("package_group") != group:
            raise RuntimeError(f"CB_DIRECT base raw package has unexpected group/run: {name}")
        raw_members = [member for member, digest in delta.get("included_file_sha256", {}).items()
                       if member.endswith(f"/runs/{run_id}/raw.csv") and digest == raw_sha]
        if len(raw_members) != 1:
            raise RuntimeError(f"CB_DIRECT base raw package member/SHA mismatch: {name}")
        raw_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                         "raw_sha256": raw_sha, "source_package_name": name,
                         "source_package_sha256": expected_zip_sha})
    if len(raw_refs) != 24 or {item["run_id"] for item in raw_refs} != expected_run_ids:
        raise RuntimeError("CB_CARRY_BUFFER base raw reference closure is not exactly A001-A024")
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    manifest_rows = {item.get("run_id"): item for item in manifest.get("runs", [])}
    for item in raw_refs:
        row = manifest_rows.get(item["run_id"])
        if not row or row.get("raw_sha256") != item["raw_sha256"]:
            raise RuntimeError(f"base raw ref differs from experiment manifest: {item['run_id']}")
    return packages, raw_refs, member_hashes


def _cb_carry_buffer_sources(root: Any) -> tuple[list[tuple[Path, str]], dict[str, Any]]:
    head = git("rev-parse", "HEAD")
    changes = dict(root.committed_changes(CB_CARRY_BUFFER_D1_BASE_COMMIT, head))
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    sources: dict[str, Path] = {}
    excluded_html: set[str] = set()
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if not root.in_scope(rel_path, [SERIES]):
            raise RuntimeError(f"CB_CARRY_BUFFER DELTA found out-of-scope change: {rel_path}")
        if status == "D":
            raise RuntimeError(f"CB_CARRY_BUFFER DELTA refuses deletions: {rel_path}")
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            if len(path.parts) < 5 or path.parts[4] not in CB_CARRY_BUFFER_D1_RUN_IDS:
                raise RuntimeError(f"CB_CARRY_BUFFER DELTA detected historical run edit: {rel_path}")
            continue
        if _excluded_delta_path(path):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        source = REPO / path
        if source.is_file() and not source.is_symlink():
            sources[rel_path] = source

    run_files: dict[str, list[tuple[Path, str]]] = {}
    raw_sha_by_run: dict[str, str] = {}
    status_by_run: dict[str, Any] = {}
    required = {"deck.cir", "raw.csv", "run.log", "stdout.txt", "stderr.txt",
                "USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
                "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env", "D0_JTL_PARAMS.snapshot.env",
                "stimulus.inc", "case_manifest.json", "metadata.json", "provenance.json",
                "source_manifest.json", "topology_manifest.json", "probe_manifest.json", "static_qa.json",
                "stimulus_manifest.json", "metrics.json", "raw_qa.json", "chain_qa.json", "qa.json",
                "plot_manifest.json", "plot_qa.json", "result.json", "RESULT_BRIEF.md"}
    for run_id in CB_CARRY_BUFFER_D1_RUN_IDS:
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"new authorized run directory is missing: {run_id}")
        files = [(path, path.relative_to(REPO).as_posix()) for path in root.included_files(run_dir)]
        names = {Path(member).name for _source, member in files}
        if required - names:
            raise RuntimeError(f"{run_id} delta evidence missing: {sorted(required - names)}")
        raw_path = run_dir / "raw.csv"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        raw_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
        plot_qa = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
        digest = root.sha256(raw_path)
        if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
                result.get("raw_sha256") != digest or qa.get("status") != "PASS" or
                qa.get("raw_sha256_before_analysis") != digest or qa.get("raw_sha256_after_analysis") != digest or
                raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != digest or
                plot_qa.get("status") != "PASS" or plot_qa.get("raw_sha256_after") != digest or
                raw_path.stat().st_size >= root.MAX_GIT_FILE_BYTES):
            raise RuntimeError(f"new run artifact/raw/QA identity failed: {run_id}")
        for page in plot_qa.get("pages", []):
            page_path = SERIES / page["path"]
            if not page_path.is_file() or root.sha256(page_path) != page.get("sha256"):
                raise RuntimeError(f"standalone HTML hash mismatch: {run_id}/{page.get('path')}")
        run_files[run_id] = files
        raw_sha_by_run[run_id] = digest
        status_by_run[run_id] = {"artifact_status": result.get("artifact_status"),
                                 "qa_status": qa.get("status"), "physical_solve_count": 1}
        for source, member in files:
            sources[member] = source

    task_analysis = CB_CARRY_BUFFER_D1_TASK
    if not task_analysis.is_dir():
        raise RuntimeError("carry-buffer analysis directory is missing")
    for path in sorted(task_analysis.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(REPO).as_posix()
        if _excluded_delta_path(Path(rel_path)):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        sources[rel_path] = path
    for path in SERIES.rglob("*.html"):
        if path.is_file():
            excluded_html.add(path.relative_to(REPO).as_posix())

    for rel_path, status in changes.items():
        path = Path(rel_path)
        if status == "D" or _excluded_delta_path(path):
            continue
        if path.parts[:4] == ("test", "exploration", SERIES.name, "runs"):
            continue
        if root.in_scope(rel_path, [SERIES]) and (REPO / path).is_file() and rel_path not in sources:
            raise RuntimeError(f"changed source/evidence omitted from DELTA: {rel_path}")

    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    if int(manifest.get("physical_solve_count", -1)) != 26:
        raise RuntimeError(f"experiment_manifest should contain 26 solves, found {manifest.get('physical_solve_count')}")
    authorization = [item for item in manifest.get("authorization_batches", [])
                     if item.get("batch_id") == "BVM4X4_CB_CARRY_BUFFER_D1_20261009"]
    if (len(authorization) != 1 or authorization[0].get("authorized_physical_solve_count") != 2 or
            authorization[0].get("physical_solve_count_completed") != 2 or
            authorization[0].get("run_ids") != list(CB_CARRY_BUFFER_D1_RUN_IDS)):
        raise RuntimeError("experiment manifest authorization is not closed for exactly A025/A026")
    batch_path = CB_CARRY_BUFFER_D1_TASK / "BATCH_MANIFEST.json"
    analysis_path = CB_CARRY_BUFFER_D1_TASK / "BATCH_ANALYSIS.json"
    if (not batch_path.is_file() or not analysis_path.is_file() or
            json.loads(batch_path.read_text(encoding="utf-8")).get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
            json.loads(analysis_path.read_text(encoding="utf-8")).get("status") != "PASS"):
        raise RuntimeError("carry-buffer batch/analysis is not closed with mechanical QA PASS")

    all_source_files = [(sources[key], key) for key in sorted(sources)]
    if len({member for _path, member in all_source_files}) != len(all_source_files):
        raise RuntimeError("duplicate source member in carry-buffer DELTA inventory")
    return all_source_files, {"changes": changes, "excluded_html": sorted(excluded_html),
                              "run_files": run_files, "raw_sha256_by_run": raw_sha_by_run,
                              "run_status_by_run": status_by_run, "all_sources": all_source_files}


def cb_carry_buffer_d1_delta_specs(tag: str, root: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not root.TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid CB_CARRY_BUFFER D1 DELTA tag: {tag!r}")
    if git("branch", "--show-current") != "master":
        raise RuntimeError("CB_CARRY_BUFFER DELTA expects the existing master branch")
    if subprocess.run(["git", "merge-base", "--is-ancestor", CB_CARRY_BUFFER_D1_BASE_COMMIT,
                       git("rev-parse", "HEAD")], cwd=REPO, check=False).returncode != 0:
        raise RuntimeError("current HEAD is not descended from the A023/A024 package checkpoint")
    base_packages, existing_refs, base_hashes = _verify_cb_carry_buffer_base(root)
    sources, context = _cb_carry_buffer_sources(root)
    all_source_paths = context["all_sources"]
    by_run = context["run_files"]
    source_group = [(path, member) for path, member in all_source_paths
                    if len(Path(member).parts) < 5 or
                    Path(member).parts[:4] != ("test", "exploration", SERIES.name, "runs")]
    metadata_group = [(path, member) for run_id in CB_CARRY_BUFFER_D1_RUN_IDS
                      for path, member in by_run[run_id] if Path(member).name != "raw.csv"]
    raw_groups = {run_id: [(path, member) for path, member in by_run[run_id]
                           if Path(member).name == "raw.csv"] for run_id in CB_CARRY_BUFFER_D1_RUN_IDS}
    if not source_group or not metadata_group or any(len(items) != 1 for items in raw_groups.values()):
        raise RuntimeError("carry-buffer DELTA requires source, per-run metadata, and exactly one raw per run")
    groups: list[tuple[str, str, list[tuple[Path, str]], str | None, int]] = [
        ("source", "source", source_group, None, 0),
        ("runs_metadata", "evidence", metadata_group, None, 2),
        *((f"{run_id}_raw", "raw", raw_groups[run_id], run_id, 0)
          for run_id in CB_CARRY_BUFFER_D1_RUN_IDS),
    ]
    specs, plans = [], []
    for group_name, group_kind, group_sources, run_id, solve_count in groups:
        records = root.file_records(group_sources)
        source_bytes = sum(item["bytes"] for item in records)
        included = {item["archive_path"]: item["sha256"] for item in records}
        new_files = sorted(member for member, digest in included.items() if member not in base_hashes)
        modified_files = sorted(member for member, digest in included.items()
                                if member in base_hashes and base_hashes[member] != digest)
        package_name = f"{SERIES.name}_delta_CB_CARRY_BUFFER_D1_{tag}_{group_name}.zip"
        target = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_path.exists():
            raise FileExistsError(f"refusing to overwrite immutable DELTA package: {package_name}")
        raw_map = ({run_id: context["raw_sha256_by_run"][run_id]}
                   if group_kind == "raw" and run_id else {})
        associated = ({run: context["raw_sha256_by_run"][run]
                       for run in CB_CARRY_BUFFER_D1_RUN_IDS} if group_kind == "evidence" else {})
        manifest = {
            "schema": "bvm-4x4-cb-carry-buffer-d1-evidence-delta-v1",
            "package_type": "directory_snapshot_delta", "package_group": group_name,
            "base_commit": CB_CARRY_BUFFER_D1_BASE_COMMIT,
            "head_commit": "PENDING_EVIDENCE_COMMIT",
            "base_package_name": CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME,
            "base_package_sha256": CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256,
            "base_package_source_commit": CB_CARRY_BUFFER_D1_BASE_SOURCE_HEAD,
            "base_delta_packages": base_packages,
            "referenced_existing_cases": existing_refs,
            "referenced_existing_raw_sha256": existing_refs,
            "included_files": records, "included_file_sha256": included,
            "new_files": new_files, "modified_files": modified_files, "deleted_files": [],
            "new_physical_solve_count": solve_count, "reused_point_count": 0,
            "raw_sha256_by_run": raw_map,
            "associated_raw_sha256_by_run": associated,
            "paired_evidence_package_name": (f"{SERIES.name}_delta_CB_CARRY_BUFFER_D1_{tag}_runs_metadata.zip"
                                             if group_kind == "raw" else None),
            "run_artifact_status_by_run": ({run_id: context["run_status_by_run"][run_id]}
                                            if run_id else context["run_status_by_run"]),
            "excluded_html": context["excluded_html"],
            "generated_from_head": git("rev-parse", "HEAD"),
            "scientific_interpretation_performed": False,
        }
        extra = {"DELTA_MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")}
        if source_bytes + sum(len(value) for value in extra.values()) >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"{group_name} uncompressed DELTA exceeds 100MB safety guard: {source_bytes}")
        spec = {"name": package_name, "kind": "bvm_4x4_cb_carry_buffer_d1_delta_v1",
                "scope": SERIES, "target": target, "qa_path": qa_path,
                "sources": group_sources, "extra_members": extra,
                "delta_manifest": manifest, "base_name": CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME,
                "base_sha": CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256,
                "raw_by_run": raw_map, "group_kind": group_kind, "run_id": run_id,
                "readme": (f"Incremental D1 carry-side CB_0928 evidence for {SERIES.name}; tag={tag}; group={group_name}.\n"
                           f"Base checkpoint: {CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME} ({CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256}).\n"
                           "A001-A024 raw is referenced by exact package/raw SHA and is not recopied.\n"
                           "Only A025/A026 are new physical solves. Generated HTML is excluded.\n"
                           "Mechanical evidence only; no SFQ event classification or scientific interpretation.\n").encode()}
        specs.append(spec)
        plans.append({"package": package_name, "package_group": group_name,
                      "file_count": len(records), "uncompressed_source_bytes": source_bytes,
                      "raw_bytes": sum(item["bytes"] for item in records if Path(item["archive_path"]).name == "raw.csv"),
                      "raw_sha256_by_run": raw_map, "new_physical_solve_count": solve_count,
                      "new_files": new_files, "modified_files": modified_files,
                      "qa_path": qa_path.relative_to(REPO).as_posix()})
    plan = {"base_commit": CB_CARRY_BUFFER_D1_BASE_COMMIT,
            "generated_from_head": git("rev-parse", "HEAD"),
            "base_package_name": CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME,
            "base_package_sha256": CB_CARRY_BUFFER_D1_BASE_SOURCE_SHA256,
            "base_delta_packages": base_packages,
            "referenced_existing_raw_count": len(existing_refs),
            "referenced_existing_raw_sha256": existing_refs,
            "new_physical_solve_count": 2, "reused_point_count": 0,
            "html_included": False, "excluded_html_count": len(context["excluded_html"]),
            "package_count": len(specs), "packages": plans}
    return specs, {"plan": plan, "source_paths": [member for _path, member in sources],
                   "base_packages": base_packages, "referenced_existing_raw": existing_refs}


def submit_cb_carry_buffer_d1_delta(args: argparse.Namespace, root: Any) -> int:
    specs, context = cb_carry_buffer_d1_delta_specs(args.tag, root)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if not mirror_dir.is_dir():
        raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
    local_collisions = [str(spec["target"]) for spec in specs
                        if spec["target"].exists() or spec["qa_path"].exists()]
    mirror_collisions = [str(mirror_dir / spec["name"]) for spec in specs
                         if (mirror_dir / spec["name"]).exists()]
    if local_collisions or mirror_collisions:
        raise FileExistsError("refusing immutable package/mirror target overwrite: " +
                              ", ".join(local_collisions + mirror_collisions))
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "package_mode": "CB_CARRY_BUFFER_D1_DELTA", **context["plan"],
                          "push_target": git("rev-parse", "--abbrev-ref", "@{upstream}"),
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    if not context["source_paths"]:
        raise RuntimeError("carry-buffer DELTA source inventory is empty")
    subprocess.run(["git", "add", "-A", "-f", "--", *context["source_paths"]], cwd=REPO, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO,
                      check=False).returncode != 0:
        subprocess.run(["git", "commit", "-m", args.message or
                        "experiment: record D1 carry-side CB buffer A025-A026"], cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")
    package_results = []
    for spec in specs:
        manifest = spec["delta_manifest"]
        if spec["group_kind"] == "raw":
            paired_name = manifest.get("paired_evidence_package_name")
            paired = next((item for item in package_results if Path(item["path"]).name == paired_name), None)
            if paired is None:
                raise RuntimeError(f"runs_metadata package must precede raw archive: {paired_name}")
            manifest["paired_evidence_package_sha256"] = paired["sha256"]
        manifest["head_commit"] = source_commit
        manifest["generated_from_head"] = source_commit
        spec["extra_members"]["DELTA_MANIFEST.json"] = (
            json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
        result = root.archive_bundle(spec, source_commit)
        package_path, qa_path = REPO / result["path"], REPO / result["qa_path"]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"package_mode": "CB_CARRY_BUFFER_D1_DELTA_SPLIT_BY_RUN",
                   "base_commit": manifest["base_commit"], "head_commit": source_commit,
                   "base_package_name": manifest["base_package_name"],
                   "base_package_sha256": manifest["base_package_sha256"],
                   "base_package_source_commit": manifest["base_package_source_commit"],
                   "base_delta_packages": manifest["base_delta_packages"],
                   "delta_included_files": manifest["included_files"],
                   "delta_included_file_sha256": manifest["included_file_sha256"],
                   "new_files": manifest["new_files"], "modified_files": manifest["modified_files"],
                   "referenced_existing_cases": manifest["referenced_existing_cases"],
                   "referenced_existing_raw_sha256": manifest["referenced_existing_raw_sha256"],
                   "new_physical_solve_count": manifest["new_physical_solve_count"],
                   "reused_point_count": 0, "html_included": False,
                   "package_group": manifest["package_group"],
                   "raw_sha256_by_run": manifest["raw_sha256_by_run"],
                   "associated_raw_sha256_by_run": manifest["associated_raw_sha256_by_run"],
                   "paired_evidence_package_name": manifest.get("paired_evidence_package_name"),
                   "paired_evidence_package_sha256": manifest.get("paired_evidence_package_sha256")})
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != root.sha256(package_path) or
                qa.get("package_bytes") != package_path.stat().st_size or
                qa.get("reopened_zip_crc_and_member_hashes_pass") is not True):
            raise RuntimeError(f"CB_CARRY_BUFFER PACKAGE_QA identity/member check failed: {spec['name']}")
        with zipfile.ZipFile(package_path, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"CB_CARRY_BUFFER ZIP CRC failure: {spec['name']}")
            packed_delta = json.loads(archive.read("DELTA_MANIFEST.json"))
            if packed_delta.get("head_commit") != source_commit:
                raise RuntimeError(f"CB_CARRY_BUFFER archived DELTA head mismatch: {spec['name']}")
            for member, digest in packed_delta.get("included_file_sha256", {}).items():
                if hashlib.sha256(archive.read(member)).hexdigest() != digest:
                    raise RuntimeError(f"CB_CARRY_BUFFER archive member SHA mismatch: {spec['name']}/{member}")
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        result.update({"sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "status": qa["status"]})
        package_results.append(result)

    package_paths = [path for result in package_results for path in (result["path"], result["qa_path"])]
    subprocess.run(["git", "add", "-f", "--", *package_paths], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"package: archive CB carry buffer D1 A025-A026 delta {args.tag}"],
                   cwd=REPO, check=True)
    push_status = "SKIPPED"
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        push_status = "PASS"
    mirror = root.copy_mirror([spec["target"] for spec in specs], mirror_dir)
    print(json.dumps({"status": "CB_CARRY_BUFFER_D1_DELTA_SUBMIT_COMPLETE",
                      "source_commit": source_commit, "final_commit": git("rev-parse", "HEAD"),
                      "push": push_status, "packages": package_results,
                      "base_commit": CB_CARRY_BUFFER_D1_BASE_COMMIT,
                      "base_package": CB_CARRY_BUFFER_D1_BASE_SOURCE_NAME,
                      "referenced_existing_raw_count": len(context["referenced_existing_raw"]),
                      "new_physical_solve_count": 2, "package_count": len(package_results),
                      "html_included": False, "mirror": mirror}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit/package only this 4x4 experiment scope")
    parser.add_argument("tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--delta", action="store_true",
                        help="append the completed batch to its verified checkpoint using the local DELTA workflow")
    parser.add_argument("--metadata-v2", action="store_true",
                        help="create a corrected metadata-only v2; never runs JoSIM")
    parser.add_argument("--message")
    parser.add_argument("--mirror-dir", default=str(MIRROR_DEFAULT))
    args = parser.parse_args()
    try:
        root = load_root_submit()
        if args.delta:
            if args.metadata_v2:
                raise RuntimeError("--delta and --metadata-v2 are mutually exclusive")
            carry_buffer_batch = (CB_CARRY_BUFFER_D1_TASK / "BATCH_MANIFEST.json")
            if carry_buffer_batch.is_file():
                return submit_cb_carry_buffer_d1_delta(args, root)
            cb_direct_batch = (SERIES / "analysis/cb-direct-d1-20261009/attempts/002/BATCH_MANIFEST.json")
            if cb_direct_batch.is_file():
                return submit_cb_direct_d1_delta(args, root)
            chain_manifest = SERIES / "analysis" / "t1-chain-20261009" / "BATCH_MANIFEST.json"
            if chain_manifest.is_file():
                return submit_t1_chain_delta(args, root)
            return submit_delta(args, root)
        validate_scope()
        if args.metadata_v2:
            return submit_metadata_v2(args, root)
        specs, _plan = package_specs(args.tag, root, dry_run=args.dry_run)
        mirror_dir = Path(args.mirror_dir).expanduser().resolve()
        if not mirror_dir.is_dir():
            raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
        mirror_collisions = [spec["name"] for spec in specs if (mirror_dir / spec["name"]).exists()]
        if mirror_collisions:
            raise FileExistsError("same-name mirror target already exists: " + ", ".join(mirror_collisions))
        if args.dry_run:
            return 0
        source_paths = included_files(SERIES)
        relative_paths = [path.relative_to(REPO).as_posix() for path in source_paths]
        if relative_paths:
            subprocess.run(["git", "add", "-A", "-f", "--", *relative_paths], cwd=REPO, check=True)
        staged_empty = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                       cwd=REPO, check=False).returncode == 0
        if staged_empty:
            raise RuntimeError("no scoped experiment/source changes to commit")
        subprocess.run(["git", "commit", "-m", args.message or "experiment: add BVM 4x4 diagonal batch"],
                       cwd=REPO, check=True)
        source_commit = git("rev-parse", "HEAD")
        package_results = []
        for spec in specs[:-1]:
            package_results.append(root.archive_bundle(spec, source_commit))
        update_summary_with_packages(package_results)
        subprocess.run(["git", "add", "--", (SERIES / "BATCH_SUMMARY.md").relative_to(REPO).as_posix()],
                       cwd=REPO, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"],
                          cwd=REPO, check=False).returncode != 0:
            subprocess.run(["git", "commit", "-m", "docs: record 4x4 run package hashes"], cwd=REPO, check=True)
        summary_commit = git("rev-parse", "HEAD")
        package_results.append(root.archive_bundle(specs[-1], summary_commit))
        package_paths = []
        for result in package_results:
            package_paths.extend((REPO / result["path"], REPO / result["qa_path"]))
        subprocess.run(["git", "add", "--", (SERIES / "BATCH_SUMMARY.md").relative_to(REPO).as_posix()],
                       cwd=REPO, check=True)
        subprocess.run(["git", "add", "-f", "--", *[p.relative_to(REPO).as_posix() for p in package_paths]],
                       cwd=REPO, check=True)
        subprocess.run(["git", "commit", "-m", f"package: archive 4x4 diagonal batch {args.tag}"],
                       cwd=REPO, check=True)
        push_status = "SKIPPED"
        if not args.no_push:
            subprocess.run(["git", "push"], cwd=REPO, check=True)
            push_status = "PASS"
        mirror_results = root.copy_mirror([REPO / x["path"] for x in package_results], mirror_dir)
        print(json.dumps({"status": "SUBMIT_COMPLETE", "source_commit": source_commit,
                          "summary_commit": summary_commit, "final_commit": git("rev-parse", "HEAD"),
                          "push": push_status, "packages": package_results,
                          "mirror": mirror_results}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
