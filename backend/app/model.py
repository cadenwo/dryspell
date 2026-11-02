"""Rock-surface moisture model.

A single-bucket water balance stepped hourly. Granite is effectively
impermeable, so the only water that matters is what sits on the surface and
in shallow cracks/pores. That makes a bucket model a good fit:

    W[t] = clamp(W[t-1] + P[t], 0, capacity)        # rain fills, excess runs off
    W[t] = max(0, W[t] - max(k * ET0[t], floor))    # evaporation drains

where
    P     = hourly precipitation (mm)
    ET0   = FAO-56 reference evapotranspiration (mm/h) from Open-Meteo;
            it already folds in temperature, humidity, wind, and radiation
    k     = drying factor for the area (sun/wind exposure; <1 shaded, >1 exposed)
    floor = small baseline drying (drainage, wind) so the bucket can empty
            overnight-ish rather than stalling at exactly ET0 = 0

The rock is "dry" (climbable) when W falls to or below a threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence


@dataclass(frozen=True)
class RockParams:
    """Tunable parameters for one climbing area."""

    capacity_mm: float = 2.5
    drying_factor: float = 1.0
    dry_threshold_mm: float = 0.2
    damp_threshold_mm: float = 0.8
    min_drying_mm_h: float = 0.02

    def __post_init__(self) -> None:
        if self.capacity_mm <= 0:
            raise ValueError("capacity_mm must be positive")
        if self.drying_factor <= 0:
            raise ValueError("drying_factor must be positive")
        if not 0 <= self.dry_threshold_mm <= self.damp_threshold_mm <= self.capacity_mm:
            raise ValueError("need 0 <= dry_threshold <= damp_threshold <= capacity")
        if self.min_drying_mm_h < 0:
            raise ValueError("min_drying_mm_h must be non-negative")


class Status(str, Enum):
    DRY = "dry"
    DAMP = "damp"
    WET = "wet"


def _clean(value: Optional[float]) -> float:
    """Open-Meteo occasionally returns null for an hour; treat it as zero."""
    if value is None or value != value:  # None or NaN
        return 0.0
    return max(0.0, float(value))


def step(moisture_mm: float, precip_mm: Optional[float], et0_mm: Optional[float], params: RockParams) -> float:
    """Advance the bucket by one hour and return the new moisture (mm)."""
    w = min(moisture_mm + _clean(precip_mm), params.capacity_mm)
    loss = max(_clean(et0_mm) * params.drying_factor, params.min_drying_mm_h)
    return max(0.0, w - loss)


def simulate(
    precip_mm: Sequence[Optional[float]],
    et0_mm: Sequence[Optional[float]],
    params: RockParams,
    initial_moisture_mm: float = 0.0,
) -> list[float]:
    """Run the bucket over an hourly series; returns moisture at the end of each hour."""
    if len(precip_mm) != len(et0_mm):
        raise ValueError(f"series length mismatch: precip={len(precip_mm)} et0={len(et0_mm)}")
    if not 0 <= initial_moisture_mm <= params.capacity_mm:
        raise ValueError("initial moisture must be within [0, capacity]")

    out: list[float] = []
    w = initial_moisture_mm
    for p, e in zip(precip_mm, et0_mm):
        w = step(w, p, e, params)
        out.append(w)
    return out


def classify(moisture_mm: float, params: RockParams) -> Status:
    if moisture_mm <= params.dry_threshold_mm:
        return Status.DRY
    if moisture_mm <= params.damp_threshold_mm:
        return Status.DAMP
    return Status.WET


def wetness_pct(moisture_mm: float, params: RockParams) -> float:
    return round(100.0 * moisture_mm / params.capacity_mm, 1)


def hours_until_dry(moisture: Sequence[float], now_idx: int, params: RockParams) -> Optional[int]:
    """Hours from now_idx until the first dry hour. 0 if dry now, None if not within the series."""
    if not 0 <= now_idx < len(moisture):
        raise IndexError("now_idx out of range")
    for i in range(now_idx, len(moisture)):
        if moisture[i] <= params.dry_threshold_mm:
            return i - now_idx
    return None


def dry_windows(
    moisture: Sequence[float],
    start_idx: int,
    params: RockParams,
    min_hours: int = 3,
) -> list[tuple[int, int]]:
    """Contiguous dry runs at or after start_idx lasting >= min_hours.

    Returns (start, end) index pairs with end exclusive.
    """
    if min_hours < 1:
        raise ValueError("min_hours must be >= 1")
    windows: list[tuple[int, int]] = []
    run_start: Optional[int] = None
    for i in range(start_idx, len(moisture)):
        if moisture[i] <= params.dry_threshold_mm:
            if run_start is None:
                run_start = i
        elif run_start is not None:
            if i - run_start >= min_hours:
                windows.append((run_start, i))
            run_start = None
    if run_start is not None and len(moisture) - run_start >= min_hours:
        windows.append((run_start, len(moisture)))
    return windows
