"""Daniels VDOT pace maths.

All pace and race-time arithmetic lives here so the coach never does it in its head.

Usage:
    python3 scripts/paces.py vdot 5k 25:00            # VDOT from a race or time trial
    python3 scripts/paces.py paces 40                 # training paces for a VDOT
    python3 scripts/paces.py race 40                  # equivalent race times and paces
    python3 scripts/paces.py goal 2:00:00 half        # VDOT and paces needed for a goal (default: marathon)

Distances: 5k, 10k, half, marathon, a number of km (21.1km) or metres (5000).
"""
from __future__ import annotations

import argparse
import math
import sys

MARATHON_M = 42195.0
HALF_M = 21097.5

# Fractions of VDOT used for each training intensity (Daniels).
EASY_FAST = 0.74
EASY_SLOW = 0.62
THRESHOLD = 0.88
INTERVAL = 0.975


def vo2_cost(speed_m_per_min: float) -> float:
    """Oxygen cost (ml/kg/min) of running at a speed."""
    v = speed_m_per_min
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def fraction_sustainable(minutes: float) -> float:
    """Fraction of VO2max sustainable for a race of this duration."""
    t = minutes
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t) + 0.2989558 * math.exp(-0.1932605 * t)


def vdot(distance_m: float, minutes: float) -> float:
    return vo2_cost(distance_m / minutes) / fraction_sustainable(minutes)


def _bisect(f, lo: float, hi: float, iterations: int = 200) -> float:
    f_lo = f(lo)
    for _ in range(iterations):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def race_minutes(vdot_value: float, distance_m: float) -> float:
    """Predicted race time in minutes for a distance at a VDOT."""
    return _bisect(lambda t: vdot(distance_m, t) - vdot_value, 1.0, 600.0)


def pace_at_fraction(vdot_value: float, fraction: float) -> float:
    """Pace in minutes per km at a fraction of VDOT."""
    target = vdot_value * fraction
    speed = _bisect(lambda v: vo2_cost(v) - target, 50.0, 600.0)
    return 1000.0 / speed


def training_paces(vdot_value: float) -> dict:
    """Training paces in minutes per km."""
    return {
        "easy_fast": pace_at_fraction(vdot_value, EASY_FAST),
        "easy_slow": pace_at_fraction(vdot_value, EASY_SLOW),
        "marathon": race_minutes(vdot_value, MARATHON_M) / (MARATHON_M / 1000),
        "threshold": pace_at_fraction(vdot_value, THRESHOLD),
        "interval": pace_at_fraction(vdot_value, INTERVAL),
    }


DISTANCES = {"5k": 5000.0, "10k": 10000.0, "half": HALF_M, "hm": HALF_M, "marathon": MARATHON_M}
VDOT_RANGE = (20.0, 90.0)


def parse_distance(text: str) -> float:
    """'5k', '10k', 'half', 'marathon', '21.1km' or metres ('5000') to metres."""
    t = text.strip().lower()
    if t in DISTANCES:
        return DISTANCES[t]
    if t.endswith("km") or t.endswith("k"):
        return float(t.rstrip("km")) * 1000
    metres = float(t)
    if metres < 100:
        raise ValueError(f"{text} looks like km, not metres: write {text}km")
    return metres


def checked_vdot(distance_m: float, minutes: float) -> float:
    """VDOT, refusing results no runner could have (usually a typo in the time or distance)."""
    value = vdot(distance_m, minutes)
    if not VDOT_RANGE[0] <= value <= VDOT_RANGE[1]:
        raise ValueError(f"{fmt_time(minutes)} for {distance_m / 1000:g} km gives VDOT {value:.1f}, which isn't realistic. "
                         "Check the time and the distance")
    return value


def parse_time(text: str) -> float:
    """'25:00' or '3:30:00' to minutes."""
    parts = [float(p) for p in text.split(":")]
    if len(parts) == 2:
        return parts[0] + parts[1] / 60
    if len(parts) == 3:
        return parts[0] * 60 + parts[1] + parts[2] / 60
    raise ValueError(f"Can't parse time: {text}")


def fmt_pace(minutes_per_km: float) -> str:
    seconds = round(minutes_per_km * 60)
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_time(minutes: float) -> str:
    seconds = round(minutes * 60)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _print_paces(vdot_value: float) -> None:
    p = training_paces(vdot_value)
    print(f"VDOT {vdot_value:.1f}")
    print(f"  Easy       {fmt_pace(p['easy_fast'])}-{fmt_pace(p['easy_slow'])}/km")
    print(f"  Marathon   {fmt_pace(p['marathon'])}/km")
    print(f"  Threshold  {fmt_pace(p['threshold'])}/km")
    print(f"  Interval   {fmt_pace(p['interval'])}/km")


def _print_races(vdot_value: float) -> None:
    print(f"VDOT {vdot_value:.1f}")
    for label, distance in [("5 km", 5000), ("10 km", 10000), ("Half", HALF_M), ("Marathon", MARATHON_M)]:
        minutes = race_minutes(vdot_value, distance)
        print(f"  {label:9} {fmt_time(minutes):>8}  ({fmt_pace(minutes / (distance / 1000))}/km)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_vdot = sub.add_parser("vdot", help="VDOT from a race distance and time")
    p_vdot.add_argument("distance")
    p_vdot.add_argument("time")
    p_paces = sub.add_parser("paces", help="Training paces for a VDOT")
    p_paces.add_argument("vdot", type=float)
    p_race = sub.add_parser("race", help="Equivalent race times for a VDOT")
    p_race.add_argument("vdot", type=float)
    p_goal = sub.add_parser("goal", help="VDOT needed for a goal time over a distance")
    p_goal.add_argument("time")
    p_goal.add_argument("distance", nargs="?", default="marathon")
    args = parser.parse_args()

    try:
        if args.command == "vdot":
            value = checked_vdot(parse_distance(args.distance), parse_time(args.time))
            _print_races(value)
            _print_paces(value)
        elif args.command == "paces":
            _print_paces(args.vdot)
        elif args.command == "race":
            _print_races(args.vdot)
        elif args.command == "goal":
            distance = parse_distance(args.distance)
            minutes = parse_time(args.time)
            value = checked_vdot(distance, minutes)
            print(f"Goal pace: {fmt_pace(minutes / (distance / 1000))}/km over {distance / 1000:g} km")
            _print_races(value)
            _print_paces(value)
    except ValueError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
