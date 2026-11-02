from fastapi.testclient import TestClient

from app.areas import AREAS
from app.main import app
from app.service import ConditionsService
from tests.conftest import FakeProvider


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_areas_returns_every_area(client):
    body = client.get("/areas").json()
    assert {a["id"] for a in body["areas"]} == {a.id for a in AREAS}
    assert body["errors"] == []
    for a in body["areas"]:
        assert a["status"] in {"dry", "damp", "wet"}
        assert 0 <= a["wetness_pct"] <= 100


def test_recent_rain_means_not_dry_yet_but_drying_in_forecast(client):
    # 6 mm fell 6 h ago; shaded Gold Bar should still be wet and dry later.
    a = client.get("/areas/gold-bar/forecast").json()
    assert a["status"] != "dry"
    assert a["hours_until_dry"] is not None and a["hours_until_dry"] > 0
    assert a["next_dry_window"] is not None
    # synthetic weather never rains again, so the window runs to the horizon
    assert a["next_dry_window"]["open_ended"] is True


def test_exposed_area_dries_before_shaded_area(client):
    lv = client.get("/areas/leavenworth/forecast").json()
    gb = client.get("/areas/gold-bar/forecast").json()
    assert lv["hours_until_dry"] < gb["hours_until_dry"]


def test_forecast_hourly_window(client):
    a = client.get("/areas/index/forecast").json()
    hourly = a["hourly"]
    assert 60 <= len(hourly) <= 73  # 24h history + now + 48h forecast
    assert any(h["is_forecast"] for h in hourly)
    assert any(not h["is_forecast"] for h in hourly)
    times = [h["time"] for h in hourly]
    assert times == sorted(times)


def test_unknown_area_404(client):
    r = client.get("/areas/yosemite/forecast")
    assert r.status_code == 404


def test_results_are_cached(client, provider):
    client.get("/areas")
    client.get("/areas")
    client.get("/areas/index/forecast")
    assert provider.calls == len(AREAS)


def test_partial_upstream_failure_reports_errors():
    bad = AREAS[0]
    app.state.service = ConditionsService(FakeProvider(fail_for={(bad.lat, bad.lon)}))
    try:
        with TestClient(app) as c:
            body = c.get("/areas").json()
            assert len(body["areas"]) == len(AREAS) - 1
            assert body["errors"][0]["id"] == bad.id
            assert c.get(f"/areas/{bad.id}/forecast").status_code == 502
    finally:
        del app.state.service


def test_total_upstream_failure_is_502():
    app.state.service = ConditionsService(FakeProvider(fail_for={(a.lat, a.lon) for a in AREAS}))
    try:
        with TestClient(app) as c:
            assert c.get("/areas").status_code == 502
    finally:
        del app.state.service
