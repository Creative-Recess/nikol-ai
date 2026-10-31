"""The sports the coach knows, and how each one's training load is measured.

A plan names the sports it coaches in plan.json ("sports": ["Run"]). Plans without the field are running
plans, so older plans keep working unchanged. Every load check (weekly ramp, longest session) loops over
the plan's sports and reads each sport's own fields, so adding a sport means adding a row here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sport:
    name: str                 # the intervals.icu workout type used when pushing ("Run")
    types: frozenset[str]     # intervals.icu activity types that count as this sport
    noun: str                 # "run", for messages
    unit: str                 # what weekly load and the longest session are measured in
    weekly_key: str | None    # plan.json week field for the weekly target, if the sport is coached
    long_key: str | None      # plan.json week field for the longest session
    baseline_key: str | None  # plan.json field for the longest session in the 30 days before the plan


SPORTS = {
    "Run": Sport("Run", frozenset({"Run", "VirtualRun", "TrailRun"}), "run", "km",
                 "run_km", "long_run_km", "baseline_long_run_km"),
    # Counted in summaries and rest days. Load fields come with coaching for each sport.
    "Ride": Sport("Ride", frozenset({"Ride", "VirtualRide", "MountainBikeRide", "GravelRide", "TrackRide", "Cyclocross"}),
                  "ride", "km", None, None, None),
    "Swim": Sport("Swim", frozenset({"Swim", "OpenWaterSwim"}), "swim", "km", None, None, None),
}

DEFAULT_SPORTS = ["Run"]


def coached(plan: dict) -> list[Sport]:
    """The sports a plan coaches, in the order it lists them. Plans without "sports" coach running."""
    names = plan.get("sports") or DEFAULT_SPORTS
    unknown = [n for n in names if n not in SPORTS]
    if unknown:
        raise ValueError(f"Unknown sport(s) in plan.json: {', '.join(unknown)}. Known: {', '.join(SPORTS)}")
    return [SPORTS[n] for n in names]


def sport_of(activity_type: str | None) -> Sport | None:
    """The sport an intervals.icu activity or workout type belongs to, or None (strength, walks, other)."""
    for sport in SPORTS.values():
        if activity_type in sport.types:
            return sport
    return None
