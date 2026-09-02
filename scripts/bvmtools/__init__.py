"""Reusable JoSIM/BVM analysis primitives.

The package is deliberately small and dependency-light.  It is the shared
implementation for future experiments; historical scripts remain available
for reproduction and are not silently migrated.
"""

from .compare import (
    TimeGridMismatch,
    compare_series,
    compare_windowed_series,
    exact_time_grid_identity,
)
from .kcl import kcl_window_metrics, linear_kcl_residual
from .onset import (
    first_persistent_exceedance,
    p99,
    pre_noise_referenced_threshold,
    tie_groups,
)
from .phase import (
    MonotonicSegment,
    continuous_unwrap,
    monotonic_segments,
    phase_delta_rad,
    phase_delta_turns,
    phase_window_metrics,
)
from .provenance import (
    file_snapshot,
    git_snapshot,
    sha256_file,
    solver_provenance,
)
from .raw import DuplicateColumnError, RawTrace, RawTraceError, read_csv
from .sfq import PHI0, StrictLocalEventSpec, strict_event_summary, strict_segment_metrics
from .waveform import waveform_metrics, waveform_window_metrics
from .waveform import percentile, zero_crossing_count

__all__ = [
    "DuplicateColumnError",
    "MonotonicSegment",
    "PHI0",
    "StrictLocalEventSpec",
    "RawTrace",
    "RawTraceError",
    "TimeGridMismatch",
    "compare_series",
    "compare_windowed_series",
    "continuous_unwrap",
    "exact_time_grid_identity",
    "file_snapshot",
    "first_persistent_exceedance",
    "git_snapshot",
    "kcl_window_metrics",
    "linear_kcl_residual",
    "monotonic_segments",
    "phase_delta_rad",
    "phase_delta_turns",
    "phase_window_metrics",
    "percentile",
    "p99",
    "pre_noise_referenced_threshold",
    "read_csv",
    "sha256_file",
    "solver_provenance",
    "strict_event_summary",
    "strict_segment_metrics",
    "waveform_metrics",
    "waveform_window_metrics",
    "zero_crossing_count",
    "tie_groups",
]
