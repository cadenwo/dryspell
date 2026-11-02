"""Turns raw weather into area conditions, with a small in-memory TTL cache.

Caching keeps us well inside Open-Meteo's free-tier limits and makes repeat
page loads instant. (The full design replaces this with a scheduled worker
that precomputes scores into Postgres; see README.)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from app.areas import Area
from app.model import classify, dry_windows, hours_until_dry, simulate, wetness_pct
from app.weather import HourlyWeather, WeatherProvider

HISTORY_HOURS = 24
FORECAST_HOURS = 48
MIN_WINDOW_HOURS = 3


@dataclass
class HourPoint:
    time: datetime
    precip_mm: float
    et0_mm: float
    temp_c: Optional[float]
    moisture_mm: float
    wetness_pct: float
    status: str
    is_forecast: bool


@dataclass
class Conditions:
    area: Area
    computed_at: datetime
    status: str
    moisture_mm: float
    wetness_pct: float
    hours_until_dry: Optional[int]
    next_dry_window: Optional[tuple[datetime, datetime, bool]]  # (start, last dry hour, runs past forecast)
    hourly: list[HourPoint]


def compute_conditions(area: Area, wx: HourlyWeather, now: Optional[datetime] = None) -> Conditions:
    now = now or datetime.now(timezone.utc)
    p = area.params
    moisture = simulate(wx.precip_mm, wx.et0_mm, p)
    i_now = wx.now_index(now)

    windows = dry_windows(moisture, i_now, p, min_hours=MIN_WINDOW_HOURS)
    next_window = None
    if windows:
        s, e = windows[0]
        next_window = (wx.times[s], wx.times[e - 1], e == len(moisture))

    lo = max(0, i_now - HISTORY_HOURS)
    hi = min(len(moisture), i_now + FORECAST_HOURS + 1)
    hourly = [
        HourPoint(
            time=wx.times[i],
            precip_mm=float(wx.precip_mm[i] or 0.0),
            et0_mm=float(wx.et0_mm[i] or 0.0),
            temp_c=wx.temp_c[i],
            moisture_mm=round(moisture[i], 3),
            wetness_pct=wetness_pct(moisture[i], p),
            status=classify(moisture[i], p).value,
            is_forecast=i > i_now,
        )
        for i in range(lo, hi)
    ]

    return Conditions(
        area=area,
        computed_at=now,
        status=classify(moisture[i_now], p).value,
        moisture_mm=round(moisture[i_now], 3),
        wetness_pct=wetness_pct(moisture[i_now], p),
        hours_until_dry=hours_until_dry(moisture, i_now, p),
        next_dry_window=next_window,
        hourly=hourly,
    )


class ConditionsService:
    def __init__(
        self,
        provider: WeatherProvider,
        ttl_seconds: float = 1800,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._ttl = ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, Conditions]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(self, area: Area) -> Conditions:
        hit = self._cache.get(area.id)
        if hit and self._clock() - hit[0] < self._ttl:
            return hit[1]
        # One in-flight fetch per area, so a burst of requests can't stampede upstream.
        lock = self._locks.setdefault(area.id, asyncio.Lock())
        async with lock:
            hit = self._cache.get(area.id)
            if hit and self._clock() - hit[0] < self._ttl:
                return hit[1]
            wx = await self._provider.hourly(area.lat, area.lon)
            cond = compute_conditions(area, wx)
            self._cache[area.id] = (self._clock(), cond)
            return cond

    async def get_many(self, areas: list[Area]) -> list[Conditions | BaseException]:
        return await asyncio.gather(*(self.get(a) for a in areas), return_exceptions=True)
