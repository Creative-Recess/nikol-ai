"""Cycling power maths: FTP estimates and power zones.

All power arithmetic lives here so the coach never does it in its head, like scripts/paces.py for running.

Usage:
    python3 scripts/power.py zones 233              # power zones in watts for an FTP
    python3 scripts/power.py ftp 20min 250          # FTP from a 20-minute test (95% of average power)
    python3 scripts/power.py ftp ramp 320           # FTP from a ramp test (75% of the best 1-minute power)
    python3 scripts/power.py watts 233 88-94        # watts for a % FTP range
"""
from __future__ import annotations

import argparse
import sys

# Upper bound of each zone as % FTP (Coggan). They match intervals.icu's default power zones.
ZONES = [
    ("Z1", "Active recovery", 55),
    ("Z2", "Endurance", 75),
    ("Z3", "Tempo", 90),
    ("Z4", "Threshold", 105),
    ("Z5", "VO2max", 120),
    ("Z6", "Anaerobic", 150),
    ("Z7", "Neuromuscular", None),
]
SWEET_SPOT = (88, 94)

# Share of the test's average power that estimates FTP.
FTP_TESTS = {"20min": 0.95, "ramp": 0.75}


def ftp_from_test(test: str, watts: float) -> float:
    if test not in FTP_TESTS:
        raise ValueError(f"Unknown test {test!r}. Use one of: {', '.join(FTP_TESTS)}")
    return watts * FTP_TESTS[test]


def zones(ftp: float) -> list[tuple[str, str, int, int | None]]:
    """(zone, name, low watts, high watts or None) for an FTP."""
    out = []
    low_pct = 0
    for zone, name, high_pct in ZONES:
        low = round(ftp * low_pct / 100) + (1 if low_pct else 0)
        out.append((zone, name, low, round(ftp * high_pct / 100) if high_pct else None))
        low_pct = high_pct or low_pct
    return out


def watts(ftp: float, low_pct: float, high_pct: float | None = None) -> tuple[int, int | None]:
    return round(ftp * low_pct / 100), round(ftp * high_pct / 100) if high_pct is not None else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_zones = sub.add_parser("zones")
    p_zones.add_argument("ftp", type=float)
    p_ftp = sub.add_parser("ftp")
    p_ftp.add_argument("test", choices=sorted(FTP_TESTS))
    p_ftp.add_argument("watts", type=float)
    p_watts = sub.add_parser("watts")
    p_watts.add_argument("ftp", type=float)
    p_watts.add_argument("percent", help="a % FTP or a range, e.g. 75 or 88-94")
    args = parser.parse_args()

    if args.command == "zones":
        for zone, name, low, high in zones(args.ftp):
            print(f"{zone}  {name:<16} {low:>4}-{high} W" if high else f"{zone}  {name:<16} {low:>4}+ W")
        low, high = watts(args.ftp, *SWEET_SPOT)
        print(f"Sweet spot ({SWEET_SPOT[0]}-{SWEET_SPOT[1]}%): {low}-{high} W")
    elif args.command == "ftp":
        ftp = ftp_from_test(args.test, args.watts)
        print(f"FTP {ftp:.0f} W")
    elif args.command == "watts":
        parts = [float(x) for x in args.percent.split("-")]
        if len(parts) not in (1, 2):
            sys.exit("Give a % FTP like 75 or a range like 88-94")
        low, high = watts(args.ftp, parts[0], parts[1] if len(parts) == 2 else None)
        print(f"{low}-{high} W" if high is not None else f"{low} W")


if __name__ == "__main__":
    main()
