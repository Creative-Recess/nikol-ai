"""Swim pace maths: CSS (critical swim speed) and training paces per 100 m.

All swim pace arithmetic lives here so the coach never does it in its head, like scripts/paces.py for running.

Usage:
    python3 scripts/swim.py css 7:00 3:20       # CSS from a 400 m and a 200 m time trial
    python3 scripts/swim.py paces 1:50          # training paces per 100 m for a CSS pace

Paces print two ways: "1:55" for people, and "1.55" for a swim step's text, since intervals.icu cuts step
text short at a colon (tested Oct 2026).
"""
from __future__ import annotations

import argparse

# Seconds per 100 m added to CSS for each training pace (conventional CSS-based zones, not a study).
PACES = [
    ("Recovery", 15, 20),
    ("Endurance", 8, 12),
    ("Tempo", 4, 6),
    ("Threshold (CSS)", -2, 2),
    ("VO2max", -6, -3),
]


def seconds(text: str) -> float:
    """'1:50' or '7:00' (m:ss), or plain seconds, to seconds."""
    if ":" in text:
        minutes, secs = text.split(":")
        return int(minutes) * 60 + float(secs)
    return float(text)


def clock(secs: float) -> str:
    s = round(secs)
    return f"{s // 60}:{s % 60:02d}"


def step_text(secs: float) -> str:
    """The dot form for a swim step's text: 115 s -> '1.55'."""
    return clock(secs).replace(":", ".")


def css(t400: float, t200: float) -> float:
    """CSS pace in seconds per 100 m: the pace between the 200 m and the 400 m."""
    if t400 <= t200:
        raise ValueError("The 400 m time must be slower than the 200 m time")
    return (t400 - t200) / 2


def paces(css_secs: float) -> list[tuple[str, float, float]]:
    """(name, fast end, slow end) in seconds per 100 m. A lower number is faster."""
    return [(name, css_secs + lo, css_secs + hi) for name, lo, hi in PACES]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_css = sub.add_parser("css")
    p_css.add_argument("t400", help="400 m time trial, m:ss")
    p_css.add_argument("t200", help="200 m time trial, m:ss")
    p_paces = sub.add_parser("paces")
    p_paces.add_argument("css", help="CSS pace per 100 m, m:ss")
    args = parser.parse_args()

    if args.command == "css":
        pace = css(seconds(args.t400), seconds(args.t200))
        print(f"CSS {clock(pace)}/100m (step text {step_text(pace)} per 100). "
              f"Set it as the Swim threshold pace in intervals.icu.")
    else:
        for name, fast, slow in paces(seconds(args.css)):
            print(f"{name:<16} {clock(fast)}-{clock(slow)}/100m   step text: {step_text(fast)}-{step_text(slow)} per 100")


if __name__ == "__main__":
    main()
