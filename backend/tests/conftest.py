from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.service import ConditionsService
from app.weather import PAST_DAYS, FORECAST_DAYS, HourlyWeather, WeatherError


def make_weather(rain_hours_ago: int = 6, rain_mm: float = 6.0, et0: float = 0.15) -> HourlyWeather:
    """A synthetic week: dry, one heavy rain burst `rain_hours_ago`, then steady drying."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=PAST_DAYS)
    n = 24 * (PAST_DAYS + FORECAST_DAYS)
    times = [start + timedelta(hours=i) for i in range(n)]
    rain_idx = PAST_DAYS * 24 - rain_hours_ago
    precip = [rain_mm if i == rain_idx else 0.0 for i in range(n)]
    return HourlyWeather(
        times=times,
        precip_mm=precip,
        et0_mm=[et0] * n,
        temp_c=[8.0] * n,
        rh_pct=[80.0] * n,
    )


class FakeProvider:
    def __init__(self, weather=None, fail_for=frozenset()):
        self.weather = weather or make_weather()
        self.fail_for = fail_for
        self.calls = 0

    async def hourly(self, lat, lon):
        self.calls += 1
        if (lat, lon) in self.fail_for:
            raise WeatherError("boom")
        return self.weather


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(provider):
    app.state.service = ConditionsService(provider)
    with TestClient(app) as c:
        yield c
    del app.state.service
