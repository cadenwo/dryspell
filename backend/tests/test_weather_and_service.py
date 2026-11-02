from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.areas import AREAS_BY_ID
from app.service import ConditionsService
from app.weather import OPEN_METEO_URL, OpenMeteoProvider, WeatherError, parse_open_meteo
from tests.conftest import FakeProvider

PAYLOAD = {
    "utc_offset_seconds": -28800,
    "hourly": {
        "time": ["2026-11-01T00:00", "2026-11-01T01:00", "2026-11-01T02:00"],
        "precipitation": [0.0, 1.2, None],
        "et0_fao_evapotranspiration": [0.01, 0.0, 0.02],
        "temperature_2m": [7.1, 6.8, 6.5],
        "relative_humidity_2m": [90, 95, 93],
    },
}


def test_parse_attaches_utc_offset():
    wx = parse_open_meteo(PAYLOAD)
    assert wx.times[0].utcoffset() == timedelta(hours=-8)
    assert wx.times[0] == datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    assert wx.precip_mm == [0.0, 1.2, None]


def test_parse_rejects_ragged_columns():
    bad = {"hourly": {**PAYLOAD["hourly"], "precipitation": [0.0]}}
    with pytest.raises(ValueError):
        parse_open_meteo(bad)


def test_now_index():
    wx = parse_open_meteo(PAYLOAD)
    assert wx.now_index(datetime(2026, 11, 1, 9, 30, tzinfo=timezone.utc)) == 1
    assert wx.now_index(datetime(2020, 1, 1, tzinfo=timezone.utc)) == 0
    assert wx.now_index(datetime(2030, 1, 1, tzinfo=timezone.utc)) == 2


@respx.mock
async def test_provider_success():
    respx.get(OPEN_METEO_URL).mock(return_value=httpx.Response(200, json=PAYLOAD))
    async with httpx.AsyncClient() as c:
        wx = await OpenMeteoProvider(c).hourly(47.8, -121.5)
    assert len(wx.times) == 3


@respx.mock
async def test_provider_http_error_becomes_weather_error():
    respx.get(OPEN_METEO_URL).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        with pytest.raises(WeatherError):
            await OpenMeteoProvider(c).hourly(47.8, -121.5)


async def test_cache_expires_after_ttl():
    t = [0.0]
    provider = FakeProvider()
    svc = ConditionsService(provider, ttl_seconds=60, clock=lambda: t[0])
    area = AREAS_BY_ID["index"]
    await svc.get(area)
    t[0] = 30
    await svc.get(area)
    assert provider.calls == 1
    t[0] = 61
    await svc.get(area)
    assert provider.calls == 2
