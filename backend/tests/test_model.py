import math
import random

import pytest

from app.model import (
    RockParams,
    Status,
    classify,
    dry_windows,
    hours_until_dry,
    simulate,
    step,
)

P = RockParams(capacity_mm=4.0, drying_factor=1.0, dry_threshold_mm=0.3, damp_threshold_mm=1.5, min_drying_mm_h=0.01)


def test_no_rain_stays_dry():
    out = simulate([0.0] * 48, [0.1] * 48, P)
    assert all(w == 0.0 for w in out)


def test_rain_is_clamped_to_capacity():
    # 30 mm in one hour: everything past capacity runs off
    w = step(0.0, 30.0, 0.0, P)
    assert w == pytest.approx(P.capacity_mm - P.min_drying_mm_h)


def test_moisture_never_negative():
    assert step(0.05, 0.0, 5.0, P) == 0.0


def test_dries_monotonically_after_rain():
    precip = [5.0] + [0.0] * 30
    et0 = [0.0] + [0.15] * 30
    out = simulate(precip, et0, P)
    assert all(b <= a for a, b in zip(out, out[1:]))
    assert out[-1] <= P.dry_threshold_mm


def test_shaded_area_dries_slower_than_exposed():
    precip = [5.0] + [0.0] * 120
    et0 = [0.0] + [0.1] * 120
    shaded = RockParams(drying_factor=0.5)
    exposed = RockParams(drying_factor=1.5)
    s = simulate(precip, et0, shaded)
    e = simulate(precip, et0, exposed)
    assert hours_until_dry(e, 0, exposed) < hours_until_dry(s, 0, shaded)


def test_floor_rate_drains_bucket_when_et0_is_zero():
    params = RockParams(capacity_mm=1.0, dry_threshold_mm=0.0, damp_threshold_mm=0.5, min_drying_mm_h=0.1)
    out = simulate([1.0] + [0.0] * 20, [0.0] * 21, params)
    assert out[-1] == 0.0


def test_null_and_nan_inputs_treated_as_zero():
    out = simulate([None, float("nan"), 0.0], [None, float("nan"), 0.0], P)
    assert out == [0.0, 0.0, 0.0]


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        simulate([0.0, 0.0], [0.0], P)


def test_invalid_initial_moisture_raises():
    with pytest.raises(ValueError):
        simulate([0.0], [0.0], P, initial_moisture_mm=10.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"capacity_mm": 0},
        {"drying_factor": 0},
        {"dry_threshold_mm": 2.0, "damp_threshold_mm": 1.0},
        {"min_drying_mm_h": -1},
    ],
)
def test_invalid_params_raise(kwargs):
    with pytest.raises(ValueError):
        RockParams(**kwargs)


@pytest.mark.parametrize(
    "moisture,expected",
    [(0.0, Status.DRY), (0.3, Status.DRY), (0.31, Status.DAMP), (1.5, Status.DAMP), (1.51, Status.WET)],
)
def test_classify_boundaries(moisture, expected):
    assert classify(moisture, P) is expected


def test_hours_until_dry():
    series = [3.0, 2.0, 1.0, 0.2, 0.1]
    assert hours_until_dry(series, 0, P) == 3
    assert hours_until_dry(series, 3, P) == 0
    assert hours_until_dry([3.0, 2.0], 0, P) is None


def test_hours_until_dry_bad_index():
    with pytest.raises(IndexError):
        hours_until_dry([0.0], 5, P)


def test_dry_windows_respect_min_hours():
    #          0    1    2    3    4    5    6    7    8
    series = [0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0]
    assert dry_windows(series, 0, P, min_hours=3) == [(3, 7)]
    assert dry_windows(series, 0, P, min_hours=1) == [(0, 2), (3, 7), (8, 9)]


def test_dry_window_open_at_end_of_series():
    assert dry_windows([2.0, 0.0, 0.0, 0.0], 0, P, min_hours=3) == [(1, 4)]


@pytest.mark.parametrize("seed", range(25))
def test_random_weather_stays_within_bounds(seed):
    rng = random.Random(seed)
    n = 24 * 7
    precip = [rng.choice([0.0, 0.0, 0.0, rng.uniform(0, 8)]) for _ in range(n)]
    et0 = [rng.uniform(0, 0.4) for _ in range(n)]
    params = RockParams(drying_factor=rng.uniform(0.3, 2.0))
    out = simulate(precip, et0, params)
    assert len(out) == n
    assert all(0.0 <= w <= params.capacity_mm and math.isfinite(w) for w in out)
