#!/usr/bin/env python3
"""Generation-level ARRAY_SIZE smoke and invariant validation."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
import control_only  # noqa: E402
import fan_in  # noqa: E402
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402

REFERENCE_CONFIG = SERIES / "config" / "canonical_reference.env"
REFERENCE_CASE = SERIES / "runs" / "U136_QB_BJ1_screen_qb_bj1_area_0p75" / "config_snapshot.env"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def base_values() -> dict[str, str]:
    values = platform.load_env(REFERENCE_CASE)
    values.update({"NAME": "fan_in_smoke", "MODE": "closed", "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""})
    return values


def validate_size(size: int) -> dict[str, object]:
    values = base_values()
    values.update({"ARRAY_SIZE": str(size), "MASKS": "full"})
    reference = platform.load_env(REFERENCE_CONFIG)
    params = platform.validate(values, reference)
    canonical = fan_in.population_masks(size)
    arbitrary = {1: ["0", "1"], 2: ["10"], 3: ["100", "010", "101"], 4: ["1000", "0101"]}[size]
    arbitrary_valid = all(fan_in.resolve_masks(mask, size) == [mask] for mask in arbitrary)
    with tempfile.TemporaryDirectory(prefix=f"fan_in_{size}_") as temp:
        root = Path(temp) / "case"
        root.mkdir()
        sources = platform.render_case_sources(root, params)
        mask = canonical[-1]
        stimulus_path = root / "stimulus.inc"
        stimulus_path.write_text(platform.stimulus_text(params, mask), encoding="utf-8")
        decks = {}
        for mode in ("passive", "closed"):
            decks[mode] = legacy.render_deck(mode, params, sources, stimulus_path, root)
        config_path = root / "control_only.env"
        config_path.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
        control = control_only.render_validation(config_path)
        closed = decks["closed"]
        passive = decks["passive"]
    instance_lines = [line.strip() for line in closed.splitlines() if re.match(r"^XBVM\d+\s", line.strip())]
    passive_instances = [line.strip() for line in passive.splitlines() if re.match(r"^XBVM\d+\s", line.strip())]
    stimulus_groups = 3 * size
    requested = legacy.requested_signals("closed", params)
    invalid_probe = [signal for signal, _subsystem, _quantity in requested if (match := re.search(r"XBVM(\d+)", signal)) and int(match.group(1)) > size]
    control["requested_array_size"] = size
    control["requested_size_static_check"] = control["array_size"] == size
    status = all((len(instance_lines) == size, len(passive_instances) == size, not invalid_probe, arbitrary_valid, set(canonical) == set(fan_in.population_masks(size)), control["status"] == "PASS", control["array_size"] == size))
    return {
        "array_size": size,
        "canonical_masks": canonical,
        "arbitrary_masks_tested": arbitrary,
        "arbitrary_masks_valid": arbitrary_valid,
        "closed_bvm_instance_count": len(instance_lines),
        "passive_bvm_instance_count": len(passive_instances),
        "expected_bvm_instance_count": size,
        "expected_stimulus_source_group_count": stimulus_groups,
        "invalid_probe_references": invalid_probe,
        "control_only_render": control,
        "status": "PASS" if status else "FAIL",
    }


def main() -> int:
    results = [validate_size(size) for size in (1, 2, 3, 4)]
    output = {"schema": "bvm-rloop-array-size-platform-smoke-v1", "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL", "results": results, "scientific_interpretation_performed": False, "physical_solve_count": 0}
    write_json(SERIES / "analysis" / "fan_in_platform_smoke.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
