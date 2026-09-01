"""Reusable JoSIM/BVM analysis primitives.

The package is deliberately small and dependency-light.  It is the shared
implementation for future experiments; historical scripts remain available
for reproduction and are not silently migrated.
"""

from .compare import TimeGridMismatch, compare_series, exact_time_grid_identity
from .phase import (
    MonotonicSegment,
    continuous_unwrap,
    monotonic_segments,
    phase_delta_rad,
    phase_delta_turns,
)
from .provenance import (
    file_snapshot,
    git_snapshot,
    sha256_file,
    solver_provenance,
)
from .raw import DuplicateColumnError, RawTrace, RawTraceError, read_csv
from .sfq import PHI0, StrictLocalEventSpec, strict_event_summary, strict_segment_metrics
from .waveform import waveform_metrics

__all__ = [
    "DuplicateColumnError",
    "MonotonicSegment",
    "PHI0",
    "StrictLocalEventSpec",
    "RawTrace",
    "RawTraceError",
    "TimeGridMismatch",
    "compare_series",
    "continuous_unwrap",
    "exact_time_grid_identity",
    "file_snapshot",
    "git_snapshot",
    "monotonic_segments",
    "phase_delta_rad",
    "phase_delta_turns",
    "read_csv",
    "sha256_file",
    "solver_provenance",
    "strict_event_summary",
    "strict_segment_metrics",
    "waveform_metrics",
]
