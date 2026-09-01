"""Strict, provenance-friendly reader for JoSIM CSV output.

JoSIM output occasionally contains repeated labels such as ``I(B_LD1)``.
This reader preserves header order and every occurrence.  A caller must name
an occurrence explicitly (or request all occurrences) before a duplicate can
be selected; duplicate columns are never silently collapsed.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class RawTraceError(ValueError):
    """The raw CSV is malformed or fails basic numerical QA."""


class DuplicateColumnError(RawTraceError):
    """A duplicate label was requested without an occurrence selector."""


@dataclass(frozen=True)
class RawTrace:
    """Parsed JoSIM trace with duplicate-column identity retained."""

    path: Path
    headers: tuple[str, ...]
    time_column: str
    time: tuple[float, ...]
    _columns: Mapping[str, tuple[tuple[float, ...], ...]]

    @property
    def sample_count(self) -> int:
        return len(self.time)

    @property
    def dt(self) -> tuple[float, ...]:
        return tuple(self.time[i + 1] - self.time[i] for i in range(len(self.time) - 1))

    @property
    def duplicate_columns(self) -> dict[str, int]:
        return {
            name: len(values)
            for name, values in self._columns.items()
            if len(values) > 1
        }

    def occurrences(self, name: str) -> tuple[tuple[float, ...], ...]:
        """Return all exact-label occurrences in original column order."""

        try:
            return self._columns[name]
        except KeyError as exc:
            raise KeyError(f"missing exact signal label {name!r}") from exc

    def column(
        self,
        name: str,
        *,
        occurrence: int | None = None,
        all_matches: bool = False,
    ) -> tuple[float, ...] | tuple[tuple[float, ...], ...]:
        """Select an exact signal label without hiding duplicate identity.

        Unique labels may be selected without an occurrence.  Duplicate
        labels require ``occurrence=...`` or ``all_matches=True``.
        """

        matches = self.occurrences(name)
        if all_matches:
            if occurrence is not None:
                raise RawTraceError("occurrence and all_matches are mutually exclusive")
            return matches
        if occurrence is None and len(matches) > 1:
            raise DuplicateColumnError(
                f"signal {name!r} has {len(matches)} occurrences; "
                "select occurrence=... or all_matches=True"
            )
        selected = 0 if occurrence is None else occurrence
        if isinstance(selected, bool) or selected < 0 or selected >= len(matches):
            raise IndexError(
                f"signal {name!r} occurrence {selected} is out of range "
                f"(0..{len(matches) - 1})"
            )
        return matches[selected]

    def qa(self) -> dict[str, object]:
        """Return basic QA without discarding the actual time grid."""

        dt = self.dt
        uniform = bool(dt) and all(value == dt[0] for value in dt)
        return {
            "status": "VALID",
            "path": str(self.path),
            "headers": list(self.headers),
            "time_column": self.time_column,
            "sample_count": self.sample_count,
            "time_start": self.time[0],
            "time_end": self.time[-1],
            "dt_min": min(dt) if dt else None,
            "dt_max": max(dt) if dt else None,
            "uniform_time_grid": uniform,
            "nonuniform_time_grid": bool(dt) and not uniform,
            "strictly_increasing_time": True,
            "nan_inf_status": "PASS",
            "duplicate_columns": self.duplicate_columns,
        }


def _detect_time_column(headers: list[str], requested: str | None) -> tuple[str, int]:
    if requested is not None:
        matches = [index for index, value in enumerate(headers) if value == requested]
        if len(matches) != 1:
            raise RawTraceError(
                f"requested time column {requested!r} must occur exactly once; "
                f"found {len(matches)}"
            )
        return requested, matches[0]

    exact = [index for index, value in enumerate(headers) if value == "time"]
    if len(exact) == 1:
        return "time", exact[0]
    if len(exact) > 1:
        raise RawTraceError("time column occurs more than once")

    insensitive = [index for index, value in enumerate(headers) if value.casefold() == "time"]
    if len(insensitive) == 1:
        return headers[insensitive[0]], insensitive[0]
    if not insensitive:
        raise RawTraceError("could not detect a time column named 'time'")
    raise RawTraceError("time column detection is ambiguous")


def read_csv(path: str | Path, *, time_column: str | None = None) -> RawTrace:
    """Read a JoSIM CSV and perform strict, basic numerical QA.

    Quoted headers are parsed by :mod:`csv` and returned as exact labels.
    Nonuniform but strictly increasing time grids are valid and preserved.
    NaN, infinity, missing cells, malformed rows, and non-increasing time are
    rejected as artifact errors.
    """

    csv_path = Path(path)
    if not csv_path.is_file():
        raise RawTraceError(f"raw CSV does not exist: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration as exc:
            raise RawTraceError(f"empty CSV: {csv_path}") from exc
        headers = list(raw_header)
        if not headers or any(not header for header in headers):
            raise RawTraceError(f"CSV has an empty header label: {csv_path}")
        detected_time_name, time_index = _detect_time_column(headers, time_column)
        columns: dict[str, list[list[float]]] = {}
        for name in headers:
            columns.setdefault(name, []).append([])
        times: list[float] = []
        for line_number, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(headers):
                raise RawTraceError(
                    f"{csv_path}: row {line_number} has {len(row)} fields, "
                    f"expected {len(headers)}"
                )
            values: list[float] = []
            for column_index, token in enumerate(row):
                try:
                    value = float(token)
                except (TypeError, ValueError) as exc:
                    raise RawTraceError(
                        f"{csv_path}: non-numeric value at row {line_number}, "
                        f"column {headers[column_index]!r}"
                    ) from exc
                if not math.isfinite(value):
                    raise RawTraceError(
                        f"{csv_path}: NaN/Inf at row {line_number}, "
                        f"column {headers[column_index]!r}"
                    )
                values.append(value)
            current_time = values[time_index]
            if times and current_time <= times[-1]:
                raise RawTraceError(
                    f"{csv_path}: time must be strictly increasing at row {line_number}"
                )
            times.append(current_time)
            occurrence_counts: dict[str, int] = {}
            for column_index, name in enumerate(headers):
                occurrence = occurrence_counts.get(name, 0)
                columns[name][occurrence].append(values[column_index])
                occurrence_counts[name] = occurrence + 1

    if len(times) < 2:
        raise RawTraceError(f"{csv_path}: at least two data rows are required")
    frozen_columns = {
        name: tuple(tuple(values) for values in occurrences)
        for name, occurrences in columns.items()
    }
    return RawTrace(
        path=csv_path,
        headers=tuple(headers),
        time_column=detected_time_name,
        time=tuple(times),
        _columns=frozen_columns,
    )
