"""Shared ARRAY_SIZE and BVM fan-in semantics for the experiment platform."""

from __future__ import annotations

import re
from typing import Any

MIN_ARRAY_SIZE = 1
MAX_ARRAY_SIZE = 4


def parse_array_size(value: Any) -> int:
    try:
        text = str(value).strip()
        if not re.fullmatch(r"[1-9]", text):
            raise ValueError
        size = int(text)
    except (TypeError, ValueError):
        raise RuntimeError(f"ARRAY_SIZE must be an integer in [{MIN_ARRAY_SIZE},{MAX_ARRAY_SIZE}], got {value!r}") from None
    if not MIN_ARRAY_SIZE <= size <= MAX_ARRAY_SIZE:
        raise RuntimeError(f"ARRAY_SIZE must be in [{MIN_ARRAY_SIZE},{MAX_ARRAY_SIZE}], got {size}")
    return size


def canonical_masks(array_size: int) -> list[str]:
    return population_masks(array_size)


def population_masks(array_size: int) -> list[str]:
    size = parse_array_size(array_size)
    return ["0" * size] + ["0" * (size - width) + "1" * width for width in range(1, size + 1)]


def quick_masks(array_size: int) -> list[str]:
    size = parse_array_size(array_size)
    masks = population_masks(size)
    return [masks[-1]] if size == 1 else masks[1:-1]


def resolve_masks(value: str, array_size: int) -> list[str]:
    size = parse_array_size(array_size)
    key = value.strip().lower()
    if key == "quick":
        return quick_masks(size)
    if key == "full":
        return population_masks(size)
    result = [item.strip() for item in value.split(",") if item.strip()]
    if not result:
        raise RuntimeError("MASKS must not be empty")
    if any(not re.fullmatch(rf"[01]{{{size}}}", item) for item in result):
        raise RuntimeError(f"MASKS must contain unique {size}-bit binary masks")
    if len(set(result)) != len(result):
        raise RuntimeError("MASKS contains a duplicate")
    return result


def bit_order(array_size: int) -> str:
    size = parse_array_size(array_size)
    if size == 1:
        return "b0=BVM1; rightmost bit maps to highest-numbered BVM"
    return f"b{size - 1}..b0=BVM1/BVM2/.../BVM{size}; rightmost bit maps to highest-numbered BVM"


def bvm_instances(array_size: int) -> str:
    size = parse_array_size(array_size)
    return "\n".join(f"XBVM{index} WL{index} BL{index} SE{index} COMMON_SL BVM" for index in range(1, size + 1))


def active_indices(mask: str, array_size: int | None = None) -> list[int]:
    size = parse_array_size(array_size if array_size is not None else len(mask))
    masks = resolve_masks(mask, size)
    # resolve_masks validates the mask; it returns the original arbitrary mask
    # as the sole element for a one-mask input.
    actual = masks[0] if len(masks) == 1 else mask
    return [index for index, bit in enumerate(actual, start=1) if bit == "1"]
