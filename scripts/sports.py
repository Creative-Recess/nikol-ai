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
    unit: str                 # what weekly load and the longest session are measured in: "km" or "h"
    weekly_key: str | None    # plan.json week field for the weekly target, if the sport is coached
    long_key: str | None      # plan.json week field for the longest session
    baseline_key: str | None  # plan.json field for the longest session in the 30 days before the plan
    field: str | None         # week-file workout field holding the session's planned amount, in `unit`
    targets: frozenset[str]   # target types its workout text may use: "hr", "pace", "power" (none for swims)
    long_max_increase: float = 0.10  # longest session vs the longest in the previous 30 days

    def amount(self, activity: dict) -> float:
        """A completed intervals.icu activity's amount in this sport's unit."""
        if self.unit == "h":
            return (activity.get("moving_time") or 0) / 3600
        return (activity.get("distance") or 0) / 1000


SPORTS = {
    # Running load is distance. The 10% long-run limit is from Frandsen et al. 2025 (see RULES.md).
    "Run": Sport("Run", frozenset({"Run", "VirtualRun", "TrailRun"}), "run", "km",
                 "run_km", "long_run_km", "baseline_long_run_km", "distance_km", frozenset({"hr", "pace"})),
    # Cycling load is time, since distance depends on terrain, wind and the bike. Cycling has no impact
    # loading, so the longest ride may grow by 20% (conventional coaching practice, not a study).
    "Ride": Sport("Ride", frozenset({"Ride", "VirtualRide", "MountainBikeRide", "GravelRide", "TrackRide", "Cyclocross"}),
                  "ride", "h", "ride_hours", "long_ride_hours", "baseline_long_ride_hours", "duration_h",
                  frozenset({"hr", "power"}), long_max_increase=0.20),
    # Swimming load is distance. Like cycling it has no impact loading, so the longest swim may grow by 20%
    # (conventional practice). Swim workouts take no targets: pace targets don't reach a Garmin watch, so the
    # pace goes in each step's text instead (see RULES.md).
    "Swim": Sport("Swim", frozenset({"Swim", "OpenWaterSwim"}), "swim", "km", "swim_km", "long_swim_km",
                  "baseline_long_swim_km", "distance_km", frozenset(), long_max_increase=0.20),
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
