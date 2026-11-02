from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.areas import AREAS, AREAS_BY_ID
from app.model import wetness_pct
from app.service import Conditions, ConditionsService
from app.weather import OpenMeteoProvider, WeatherError

log = logging.getLogger("dryspell")


# ---------- response schemas ----------

class DryWindow(BaseModel):
    start: datetime
    end: datetime
    open_ended: bool  # dry through the end of the forecast horizon


class AreaSummary(BaseModel):
    id: str
    name: str
    region: str
    lat: float
    lon: float
    rock: str
    notes: str
    status: str
    moisture_mm: float
    wetness_pct: float
    dry_threshold_pct: float
    hours_until_dry: Optional[int]
    next_dry_window: Optional[DryWindow]
    computed_at: datetime


class HourOut(BaseModel):
    time: datetime
    precip_mm: float
    et0_mm: float
    temp_c: Optional[float]
    moisture_mm: float
    wetness_pct: float
    status: str
    is_forecast: bool


class AreaForecast(AreaSummary):
    hourly: list[HourOut]


class AreaError(BaseModel):
    id: str
    name: str
    error: str


class AreasResponse(BaseModel):
    areas: list[AreaSummary]
    errors: list[AreaError]


def _summary(c: Conditions) -> dict:
    a = c.area
    return dict(
        id=a.id,
        name=a.name,
        region=a.region,
        lat=a.lat,
        lon=a.lon,
        rock=a.rock,
        notes=a.notes,
        status=c.status,
        moisture_mm=c.moisture_mm,
        wetness_pct=c.wetness_pct,
        dry_threshold_pct=wetness_pct(a.params.dry_threshold_mm, a.params),
        hours_until_dry=c.hours_until_dry,
        next_dry_window=(
            DryWindow(start=c.next_dry_window[0], end=c.next_dry_window[1], open_ended=c.next_dry_window[2]) if c.next_dry_window else None
        ),
        computed_at=c.computed_at,
    )


# ---------- app ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tests can pre-populate app.state.service with a fake provider.
    client: Optional[httpx.AsyncClient] = None
    if not hasattr(app.state, "service"):
        client = httpx.AsyncClient(headers={"User-Agent": "dryspell/0.1"})
        app.state.service = ConditionsService(OpenMeteoProvider(client))
    yield
    if client is not None:
        await client.aclose()


app = FastAPI(
    title="Dryspell API",
    version="0.1.0",
    description="Predicts when PNW granite bouldering areas are dry enough to climb after rain.",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/areas", response_model=AreasResponse)
async def list_areas(request: Request) -> AreasResponse:
    service: ConditionsService = request.app.state.service
    results = await service.get_many(list(AREAS))
    areas, errors = [], []
    for area, res in zip(AREAS, results):
        if isinstance(res, BaseException):
            log.warning("conditions failed for %s: %s", area.id, res)
            errors.append(AreaError(id=area.id, name=area.name, error="weather data unavailable"))
        else:
            areas.append(AreaSummary(**_summary(res)))
    if not areas and errors:
        raise HTTPException(status_code=502, detail="weather data unavailable for all areas")
    return AreasResponse(areas=areas, errors=errors)


@app.get("/areas/{area_id}/forecast", response_model=AreaForecast)
async def area_forecast(area_id: str, request: Request) -> AreaForecast:
    area = AREAS_BY_ID.get(area_id)
    if area is None:
        raise HTTPException(status_code=404, detail=f"unknown area '{area_id}'")
    service: ConditionsService = request.app.state.service
    try:
        c = await service.get(area)
    except WeatherError as exc:
        log.warning("conditions failed for %s: %s", area.id, exc)
        raise HTTPException(status_code=502, detail="weather data unavailable") from exc
    return AreaForecast(**_summary(c), hourly=[HourOut(**vars(h)) for h in c.hourly])
