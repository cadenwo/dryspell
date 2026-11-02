"""Starter climbing areas.

Coordinates are approximate area centroids. Model parameters are hand-set
priors based on exposure (sun/wind vs. forest canopy) and will be calibrated
against observed conditions later (see README roadmap).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.model import RockParams


@dataclass(frozen=True)
class Area:
    id: str
    name: str
    region: str
    lat: float
    lon: float
    rock: str
    notes: str
    params: RockParams


AREAS: tuple[Area, ...] = (
    Area(
        id="gold-bar",
        name="Gold Bar",
        region="Skykomish Valley, WA",
        lat=47.857,
        lon=-121.681,
        rock="granite",
        notes="Mossy forest boulders; heavy canopy slows drying.",
        params=RockParams(capacity_mm=2.5, drying_factor=0.7),
    ),
    Area(
        id="index",
        name="Index",
        region="Skykomish Valley, WA",
        lat=47.821,
        lon=-121.556,
        rock="granite",
        notes="Valley-bottom boulders near the Town Walls; partial canopy.",
        params=RockParams(capacity_mm=2.2, drying_factor=0.85),
    ),
    Area(
        id="leavenworth",
        name="Leavenworth",
        region="Icicle Canyon, WA",
        lat=47.570,
        lon=-120.735,
        rock="granite",
        notes="East of the crest: sunnier, drier air, fastest drying of the set.",
        params=RockParams(capacity_mm=1.8, drying_factor=1.4),
    ),
    Area(
        id="squamish",
        name="Squamish",
        region="Sea-to-Sky, BC",
        lat=49.680,
        lon=-123.156,
        rock="granite",
        notes="Forest boulders under the Chief; humid coastal air.",
        params=RockParams(capacity_mm=2.5, drying_factor=0.7),
    ),
)

AREAS_BY_ID: dict[str, Area] = {a.id: a for a in AREAS}
