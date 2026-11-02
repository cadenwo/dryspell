"""Open-Meteo client.

Pulls a week of past hourly weather (to spin up the moisture bucket so the
current state reflects recent rain) plus a few days of forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 7
FORECAST_DAYS = 4


class WeatherError(RuntimeError):
    """Upstream weather data was unavailable or malformed."""


@dataclass(frozen=True)
class HourlyWeather:
    times: list[datetime]  # timezone-aware, one per hour
    precip_mm: list[Optional[float]]
    et0_mm: list[Optional[float]]
    temp_c: list[Optional[float]]
    rh_pct: list[Optional[float]]

    def now_index(self, now: Optional[datetime] = None) -> int:
        """Index of the hour containing `now` (clamped to the series)."""
        now = now or datetime.now(timezone.utc)
        for i, t in enumerate(self.times):
            if t <= now < t + timedelta(hours=1):
                return i
        return 0 if now < self.times[0] else len(self.times) - 1


class WeatherProvider(Protocol):
    async def hourly(self, lat: float, lon: float) -> HourlyWeather: ...


class OpenMeteoProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def hourly(self, lat: float, lon: float) -> HourlyWeather:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,et0_fao_evapotranspiration,temperature_2m,relative_humidity_2m",
            "past_days": PAST_DAYS,
            "forecast_days": FORECAST_DAYS,
            "timezone": "auto",
        }
        try:
            resp = await self._client.get(OPEN_METEO_URL, params=params, timeout=15.0)
            resp.raise_for_status()
            return parse_open_meteo(resp.json())
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise WeatherError(f"Open-Meteo request failed: {exc}") from exc


def parse_open_meteo(payload: dict) -> HourlyWeather:
    """Turn an Open-Meteo JSON payload into an HourlyWeather.

    Open-Meteo returns local wall-clock times without an offset when
    timezone=auto, plus `utc_offset_seconds`; we attach that offset so every
    timestamp is unambiguous.
    """
    hourly = payload["hourly"]
    tz = timezone(timedelta(seconds=int(payload.get("utc_offset_seconds", 0))))
    times = [datetime.fromisoformat(t).replace(tzinfo=tz) for t in hourly["time"]]
    n = len(times)
    if n == 0:
        raise ValueError("empty hourly series")

    def col(name: str) -> list[Optional[float]]:
        values = hourly.get(name) or [None] * n
        if len(values) != n:
            raise ValueError(f"column {name} has {len(values)} rows, expected {n}")
        return values

    return HourlyWeather(
        times=times,
        precip_mm=col("precipitation"),
        et0_mm=col("et0_fao_evapotranspiration"),
        temp_c=col("temperature_2m"),
        rh_pct=col("relative_humidity_2m"),
    )
