"""Guardrails every week file must pass before anything reaches the calendar or watch.

The rules are written in plain English in RULES.md. This module is the source of truth
for how they're enforced.

Usage:
    python3 scripts/guardrails.py check WEEK_FILE     # uses live history from intervals.icu
    python3 scripts/guardrails.py plan [PLAN_FILE]    # the whole plan: ramp, long runs, dates (default: current event)
    python3 scripts/guardrails.py score               # injury score status from wellness comments
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ATHLETE_DIR = REPO / "athlete"
SETTINGS_FILE = ATHLETE_DIR / "settings.json"


def event_dir() -> Path:
    """The event being coached, named by "current_event" in athlete/settings.json."""
    if not SETTINGS_FILE.exists():
        sys.exit("No athlete/settings.json. Copy template/ to athlete/ and fill it in first.")
    name = json.loads(SETTINGS_FILE.read_text()).get("current_event")
    path = ATHLETE_DIR / "events" / str(name)
    if not name or not path.is_dir():
        sys.exit(f"\"current_event\" in athlete/settings.json must name a folder in athlete/events/ (got {name!r})")
    return path


def plan_file() -> Path:
    return event_dir() / "plan.json"


def settings() -> dict:
    return json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}


def injury_score_name() -> str | None:
    """The body part the athlete scores each morning (e.g. "achilles"), or None if they don't track one."""
    score = settings().get("injury_score") or {}
    return (score.get("name") or "").strip().lower() or None

LONG_RUN_MAX_INCREASE = 0.10        # single run vs longest run in the previous 30 days
LONG_RUN_WINDOW_DAYS = 30
WEEKLY_MAX_INCREASE = 0.15          # vs the last full training week
TWO_WEEK_MAX_INCREASE = 0.30        # vs the full week before that
WEEK_TARGET_TOLERANCE = 0.10        # planned run km vs the plan's weekly target

# No scores means no flare: the body part is assumed fine unless the scores say otherwise.
SCORE_FLARE_ABOVE = 3               # any score above this in the window pauses quality work
SCORE_WINDOW_DAYS = 7
GATED_KINDS = {"strides", "threshold", "interval", "time_trial", "marathon_pace", "hills"}
KEY_KINDS = {"long", "threshold", "interval", "time_trial", "marathon_pace"}

# Only percentage and zone HR targets are parsed. Absolute bpm ("120-150bpm") is silently dropped by
# intervals.icu (tested 24 Sep 2026), so it's rejected below.
HR_TARGET_RE = re.compile(r"%\s*(?:LT)?HR|Z\d(?:-Z\d)?\s*HR", re.IGNORECASE)
BPM_RE = re.compile(r"\d\s*bpm", re.IGNORECASE)
PACE_TARGET_RE = re.compile(r"\bpace\b", re.IGNORECASE)
BARE_PACE_RE = re.compile(r"\d:\d\d/km(?!\s*pace)(?!-)", re.IGNORECASE)
# "400m" means 400 minutes to intervals.icu. Anything 100m or longer is almost certainly a distance mistake.
MINUTES_AS_METRES_RE = re.compile(r"(?<![\d.])(\d{3,})m\b")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"PASS  {p}" for p in self.passes]
        lines += [f"WARN  {w}" for w in self.warnings]
        lines += [f"FAIL  {e}" for e in self.errors]
        lines.append("Guardrails: " + ("OK" if self.ok else f"{len(self.errors)} failure(s)"))
        return "\n".join(lines)


# ---- Injury score ----

def score_re(name: str) -> re.Pattern:
    """Matches 'name: N' (or 'name = N') in wellness comments."""
    return re.compile(rf"{re.escape(name)}\s*[:=]\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_scores(wellness_rows: list[dict], name: str) -> list[tuple[dt.date, float]]:
    """Morning scores logged as 'name: N' in wellness comments."""
    pattern = score_re(name)
    out = []
    for row in wellness_rows:
        match = pattern.search(row.get("comments") or "")
        if match:
            out.append((dt.date.fromisoformat(row["id"]), float(match.group(1))))
    return sorted(out)


def score_cleared(scores: list[tuple[dt.date, float]], as_of: dt.date, name: str = "injury") -> tuple[bool, str]:
    """Quality work is allowed unless a recent score flares above 3/10 or the trend is rising."""
    label = name.capitalize()
    window = [(d, s) for d, s in scores if as_of - dt.timedelta(days=SCORE_WINDOW_DAYS) < d <= as_of]
    if not window:
        return True, f"no {name} scores in the {SCORE_WINDOW_DAYS} days to {as_of}, assumed fine (log them daily)"
    worst = max(s for _, s in window)
    if worst > SCORE_FLARE_ABOVE:
        return False, f"{label} score reached {worst:g}/10 in the {SCORE_WINDOW_DAYS} days to {as_of}"
    previous = [s for d, s in scores
                if as_of - dt.timedelta(days=2 * SCORE_WINDOW_DAYS) < d <= as_of - dt.timedelta(days=SCORE_WINDOW_DAYS)]
    recent_avg = sum(s for _, s in window) / len(window)
    if previous and recent_avg > sum(previous) / len(previous) + 0.5:
        return False, f"{label} scores are trending up week on week"
    return True, f"{label} fine: {len(window)} scores in the last {SCORE_WINDOW_DAYS} days, worst {worst:g}/10"


# ---- Individual checks ----

def check_long_runs(history: list[tuple[dt.date, float]], planned: list[tuple[dt.date, float]], report: Report) -> None:
    """No run more than 10% longer than the longest run in the previous 30 days."""
    timeline = sorted(history + planned)
    planned_set = set(planned)
    for i, (day, km) in enumerate(timeline):
        if (day, km) not in planned_set:
            continue
        prior = [k for d, k in timeline[:i] if 0 < (day - d).days <= LONG_RUN_WINDOW_DAYS]
        if not prior:
            report.errors.append(f"{day}: no runs in the previous {LONG_RUN_WINDOW_DAYS} days to compare a {km:g} km run against")
            continue
        limit = max(prior) * (1 + LONG_RUN_MAX_INCREASE)
        if km > limit + 1e-9:
            report.errors.append(f"{day}: {km:g} km is more than 10% over the 30-day longest run ({max(prior):g} km, limit {limit:.1f} km)")
    longest = max((k for _, k in planned), default=0)
    if planned:
        report.passes.append(f"Long-run rule: longest planned run {longest:g} km is within 10% of the 30-day max")


def check_weekly(week: dict, plan: dict, report: Report) -> None:
    """Plan targets rise by at most 15% over the last full week and 30% over two full weeks."""
    weeks = {w["week"]: w for w in plan["weeks"]}
    this = weeks.get(week["week"])
    if this is None:
        report.errors.append(f"Week {week['week']} is not in plan.json")
        return
    planned_km = sum(s.get("distance_km", 0) for s in week["sessions"] if s.get("type") == "Run")
    target = this["run_km"]
    if abs(planned_km - target) > target * WEEK_TARGET_TOLERANCE:
        report.warnings.append(f"Planned run km {planned_km:g} is more than 10% away from the plan target {target:g}")
    else:
        report.passes.append(f"Weekly km: {planned_km:g} km planned vs {target:g} km target")
    if this.get("down_week"):
        return
    full = [w for n, w in sorted(weeks.items()) if n < week["week"] and not w.get("down_week")]
    if full:
        prev = full[-1]["run_km"]
        if planned_km > prev * (1 + WEEKLY_MAX_INCREASE) + 1e-9:
            report.errors.append(f"{planned_km:g} km is more than 15% over the last full week ({prev:g} km)")
    if len(full) >= 2:
        prev2 = full[-2]["run_km"]
        if planned_km > prev2 * (1 + TWO_WEEK_MAX_INCREASE) + 1e-9:
            report.errors.append(f"{planned_km:g} km is more than 30% over two full weeks ago ({prev2:g} km)")


def check_workout_text(session: dict, report: Report) -> None:
    # Only step lines are parsed by intervals.icu. The free-text notes above them can say anything.
    text = "\n".join(l for l in session.get("description", "").splitlines() if l.strip().startswith("-"))
    label = f"{session['date']} {session['name']}"
    has_hr = bool(HR_TARGET_RE.search(text))
    has_pace = bool(PACE_TARGET_RE.search(text))
    if has_hr and has_pace:
        report.errors.append(f"{label}: mixes HR and pace targets (Garmin and COROS only handle one target type per workout)")
    if not has_hr and not has_pace:
        report.errors.append(f"{label}: no HR or pace target in the workout text")
    if BPM_RE.search(text):
        report.errors.append(f"{label}: absolute bpm targets are silently dropped. Use % LTHR (e.g. 69-86% LTHR)")
    if BARE_PACE_RE.search(text):
        report.errors.append(f"{label}: absolute pace without the word 'pace' is silently dropped")
    if MINUTES_AS_METRES_RE.search(text):
        report.errors.append(f"{label}: '{MINUTES_AS_METRES_RE.search(text).group(0)}' means minutes. Use 'mtr' for metres")
    for line in text.splitlines():
        if line.strip().startswith("-") and not (HR_TARGET_RE.search(line) or PACE_TARGET_RE.search(line)):
            report.errors.append(f"{label}: step '{line.strip()}' has no target")


def check_availability(sessions: list[dict], plan: dict, report: Report) -> None:
    """Nothing is scheduled on a date the athlete has marked unavailable."""
    blocked = {u["date"]: u.get("note", "") for u in plan.get("unavailable", [])}
    for s in sessions:
        if s["date"] in blocked and s.get("category") == "WORKOUT":
            report.errors.append(f"{s['date']} {s['name']}: unavailable ({blocked[s['date']]})")


EASY_MIN_PER_KM = 6.0         # conservative time estimate for any run
STRENGTH_MIN = {"A": 40, "B": 15, "C": 20}
LEG_STRENGTH = {"A", "B"}


def _minutes(hh_mm: str) -> int:
    hours, minutes = hh_mm.split(":")
    return int(hours) * 60 + int(minutes)


def check_schedule(sessions: list[dict], plan: dict, report: Report) -> None:
    """No strength after a ride unless it's in the evening, no upper body on leg days, office days done in time.

    There's no time for strength after a morning ride, on any day. Evening strength ("time": "evening" on
    the session) is fine on any day, including ride days, and doesn't count toward the morning budget.
    The budget runs from schedule.office_start to schedule.office_done_by in plan.json, and isn't checked
    when either is missing. Public holidays count as WFH days.
    """
    schedule = plan.get("schedule", {})
    start, done_by = schedule.get("office_start"), schedule.get("office_done_by")
    budget = _minutes(done_by) - _minutes(start) if start and done_by else None
    office = set(schedule.get("office_days", []))
    wfh = set(schedule.get("wfh_days", []))
    holidays = set(plan.get("holidays", {}))
    by_day: dict[str, list[dict]] = {}
    for s in sessions:
        by_day.setdefault(s["date"], []).append(s)
    for day, items in sorted(by_day.items()):
        strength = {x["strength"] for x in items if x.get("strength")}
        morning_strength = {x["strength"] for x in items if x.get("strength") and x.get("time") != "evening"}
        rides = [x for x in items if x.get("kind") == "ride"]
        weekday = dt.date.fromisoformat(day).strftime("%a")
        flexible = weekday in wfh or day in holidays
        if morning_strength and rides:
            report.errors.append(f"{day}: strength {'/'.join(sorted(morning_strength))} after a ride. Mark it \"time\": \"evening\"")
        if "C" in strength and strength & LEG_STRENGTH:
            report.errors.append(f"{day}: upper-body strength on a leg strength day")
        if budget is not None and weekday in office and not flexible and not rides:
            minutes = sum(x.get("distance_km", 0) for x in items if x.get("type") == "Run") * EASY_MIN_PER_KM
            minutes += sum(STRENGTH_MIN.get(x, 0) for x in morning_strength)
            if minutes > budget:
                report.errors.append(f"{day} ({weekday}, office day): about {minutes:.0f} min won't finish by {done_by}")


def check_rides(sessions: list[dict], report: Report, exceptions: dict | None = None) -> None:
    """No ride the day before a long run or a key session.

    A week file can allow a ride before an easy long run with
    "exceptions": {"ride_before_long_run": "reason"}. It then shows as a warning, not a failure.
    Key sessions (threshold, intervals, marathon pace, time trials) never get an exception.
    """
    exceptions = exceptions or {}
    kinds = {}
    for s in sessions:
        if s.get("kind") in KEY_KINDS:
            kinds[dt.date.fromisoformat(s["date"])] = s["kind"]
    for s in sessions:
        if s.get("kind") != "ride":
            continue
        next_day = dt.date.fromisoformat(s["date"]) + dt.timedelta(days=1)
        kind = kinds.get(next_day)
        if kind is None:
            continue
        if kind == "long" and "ride_before_long_run" in exceptions:
            report.warnings.append(f"{s['date']}: ride the day before the long run, allowed: {exceptions['ride_before_long_run']}")
        else:
            report.errors.append(f"{s['date']}: ride the day before a {kind.replace('_', ' ')} run")


def check_rest_day(week: dict, report: Report) -> None:
    """Every full Monday-Sunday week has a day with no run, no ride and no leg strength.

    Upper-body strength, mobility and recovery notes are fine on a rest day. A week file can skip it with
    "exceptions": {"no_rest_day": "reason"} (e.g. a cycling tour), which shows as a warning. Partial weeks (week 0) are
    not checked.
    """
    start = dt.date.fromisoformat(week["start"])
    if start.weekday() != 0:
        return
    busy = {s["date"] for s in week["sessions"]
            if s.get("type") == "Run" or s.get("kind") == "ride" or s.get("strength") in LEG_STRENGTH}
    rest = [start + dt.timedelta(days=i) for i in range(7) if str(start + dt.timedelta(days=i)) not in busy]
    if rest:
        report.passes.append("Rest day: " + ", ".join(f"{d:%a} {d.day} {d:%b}" for d in rest))
    elif "no_rest_day" in week.get("exceptions", {}):
        report.warnings.append(f"No rest day this week, allowed: {week['exceptions']['no_rest_day']}")
    else:
        report.errors.append("No rest day this week (a day with no run, no ride and no leg strength)")


def check_gates(sessions: list[dict], cleared: bool, reason: str, report: Report) -> None:
    # Gate on explicit fields only. Text search would trip on notes like "no strides this week".
    gated = [s for s in sessions if s.get("kind") in GATED_KINDS or s.get("strides")]
    if gated and not cleared:
        for s in gated:
            report.errors.append(f"{s['date']} {s['name']}: {s.get('kind')} is paused ({reason})")
    elif gated:
        report.passes.append(f"Quality sessions allowed: {reason}")


def provisional_runs(weeks_dir: Path, today: dt.date, before: dt.date, exclude_start: str) -> list[tuple[dt.date, float]]:
    """Planned runs from earlier week files that are still in the future, so can't be in the history yet."""
    out = []
    for f in sorted(weeks_dir.glob("*.json")):
        week = json.loads(f.read_text())
        if week["start"] == exclude_start:
            continue
        for s in week["sessions"]:
            if s.get("category") == "WORKOUT" and s.get("type") == "Run":
                day = dt.date.fromisoformat(s["date"])
                if today <= day < before:
                    out.append((day, float(s["distance_km"])))
    return out


# ---- Whole-plan check ----

def check_plan(plan: dict) -> Report:
    """The plan's weekly targets follow the load rules before any week is written.

    Weekly run km rises by at most 15% over the last full week and 30% over two full weeks (down weeks
    aren't checked), each long run is at most 10% longer than the longest in the previous 30 days (the
    plan's baseline_long_run_km covers the 30 days before it starts), weeks run Monday to Monday (a short
    week 0 may start on any day), and the race falls in the last week once the plan reaches it.
    """
    report = Report()
    weeks = sorted(plan.get("weeks", []), key=lambda w: w["week"])
    if not weeks:
        report.errors.append("plan.json has no weeks")
        return report
    full: list[dict] = []
    longs: list[tuple[dt.date, float]] = []
    if plan.get("baseline_long_run_km"):
        longs.append((dt.date.fromisoformat(weeks[0]["start"]) - dt.timedelta(days=1), float(plan["baseline_long_run_km"])))
    else:
        report.warnings.append("No baseline_long_run_km: the first long runs can't be checked against recent history")
    for i, w in enumerate(weeks):
        start = dt.date.fromisoformat(w["start"])
        label = f"Week {w['week']} ({w['start']})"
        if i > 0:
            expected = dt.date.fromisoformat(weeks[i - 1]["start"])
            expected += dt.timedelta(days=7 - expected.weekday() if i == 1 else 7)
            if start != expected:
                report.errors.append(f"{label}: expected to start on Monday {expected}")
        if not w.get("down_week"):
            km = w["run_km"]
            if full and km > full[-1]["run_km"] * (1 + WEEKLY_MAX_INCREASE) + 1e-9:
                report.errors.append(f"{label}: {km:g} km is more than 15% over week {full[-1]['week']} ({full[-1]['run_km']:g} km)")
            if len(full) >= 2 and km > full[-2]["run_km"] * (1 + TWO_WEEK_MAX_INCREASE) + 1e-9:
                report.errors.append(f"{label}: {km:g} km is more than 30% over week {full[-2]['week']} ({full[-2]['run_km']:g} km)")
            full.append(w)
        long_km = w.get("long_run_km")
        if long_km:
            prior = [k for d, k in longs if 0 < (start - d).days <= LONG_RUN_WINDOW_DAYS]
            if prior and long_km > max(prior) * (1 + LONG_RUN_MAX_INCREASE) + 1e-9:
                report.errors.append(f"{label}: long run {long_km:g} km is more than 10% over the 30-day longest ({max(prior):g} km)")
            longs.append((start, float(long_km)))
    race = plan.get("race_date")
    if race:
        last = dt.date.fromisoformat(weeks[-1]["start"])
        if dt.date.fromisoformat(race) > last + dt.timedelta(days=6):
            report.warnings.append(f"The plan stops at the week of {last}, before the race on {race}")
        elif dt.date.fromisoformat(race) < last:
            report.errors.append(f"race_date {race} is before the last plan week (starting {last})")
    if report.ok:
        report.passes.append(f"Plan: {len(weeks)} weeks, weekly ramp and long-run growth within the rules")
    return report


# ---- Whole-week check ----

RUN_FIELDS = ("id", "date", "category", "type", "kind", "name", "distance_km", "description")
SESSION_FIELDS = ("id", "date", "category", "name")


def missing_fields(week: dict) -> list[str]:
    """Fields a week file needs before any check can run, as readable errors."""
    errors = [f"week file has no \"{k}\"" for k in ("week", "start", "sessions") if k not in week]
    for i, s in enumerate(week.get("sessions", []), 1):
        needed = RUN_FIELDS if s.get("category") == "WORKOUT" else SESSION_FIELDS
        gaps = [k for k in needed if k not in s]
        if gaps:
            errors.append(f"session {i} ({s.get('name', 'unnamed')}) is missing {', '.join(gaps)}")
    return errors


def baseline_history(plan: dict) -> list[tuple[dt.date, float]]:
    """The plan's baseline_long_run_km as a run the day before the plan starts, so new runners can be checked."""
    if not plan.get("baseline_long_run_km") or not plan.get("weeks"):
        return []
    first = min(dt.date.fromisoformat(w["start"]) for w in plan["weeks"])
    return [(first - dt.timedelta(days=1), float(plan["baseline_long_run_km"]))]


def check_week(week: dict, history: list[tuple[dt.date, float]] | None = None,
               scores: list[tuple[dt.date, float]] | None = None, plan: dict | None = None,
               offline: bool = False, weeks_dir: Path | None = None) -> Report:
    """Run every guardrail. Fetches run history and injury scores from intervals.icu unless given or offline."""
    report = Report()
    report.errors.extend(missing_fields(week))
    if not report.ok:
        return report
    sessions = week["sessions"]
    start = dt.date.fromisoformat(week["start"])
    if plan is None:
        plan = json.loads(plan_file().read_text())
    score_name = injury_score_name() if scores is None else None
    if offline:
        history = [] if history is None else history
        scores = [] if scores is None else scores
        report.warnings.append("Offline: checked against the plan only, not your recent runs or injury scores. "
                               "Check again online before pushing")
    if history is None or (scores is None and score_name):
        import icu

        oldest = str(start - dt.timedelta(days=LONG_RUN_WINDOW_DAYS + 7))
        if history is None:
            history = icu.run_history(oldest, str(dt.date.today() - dt.timedelta(days=1)))
            provisional = provisional_runs(weeks_dir or event_dir() / "weeks", dt.date.today(), start, week["start"])
            if provisional:
                history = sorted(history + provisional)
                report.warnings.append(
                    f"Counted {len(provisional)} planned runs that haven't happened yet. "
                    "Re-check this week once they're done"
                )
        if scores is None:
            scores = parse_scores(icu.wellness(oldest, str(dt.date.today())), score_name)
    history = sorted(history + baseline_history(plan))

    runs = [s for s in sessions if s.get("category") == "WORKOUT" and s.get("type") == "Run"]
    planned = [(dt.date.fromisoformat(s["date"]), float(s["distance_km"])) for s in runs]
    check_long_runs(history, planned, report)
    check_weekly(week, plan, report)
    for s in runs:
        check_workout_text(s, report)
    check_rides(sessions, report, week.get("exceptions"))
    check_availability(sessions, plan, report)
    check_schedule(sessions, plan, report)
    check_rest_day(week, report)
    if scores is None:
        cleared, reason = True, "no injury score tracked"
    else:
        cleared, reason = score_cleared(scores, start - dt.timedelta(days=1), score_name or "injury")
    check_gates(sessions, cleared, reason, report)
    if not report.errors:
        report.passes.append(f"Workout text: {len(runs)} runs, one target type each")
    return report


def main() -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="Check one week file")
    p_check.add_argument("week_file")
    p_check.add_argument("--plan", help="plan.json to check against (default: the current event's)")
    p_check.add_argument("--offline", action="store_true",
                         help="Don't fetch recent runs or injury scores (e.g. before the API key is set up)")
    p_plan = sub.add_parser("plan", help="Check a whole plan.json")
    p_plan.add_argument("plan_file", nargs="?")
    sub.add_parser("score", help="Recent injury scores and whether quality work is allowed")
    args = parser.parse_args()
    if args.command == "check":
        week_file = Path(args.week_file)
        plan = json.loads(Path(args.plan).read_text()) if args.plan else None
        report = check_week(json.loads(week_file.read_text()), plan=plan, offline=args.offline,
                            weeks_dir=week_file.parent)
        print(report.render())
        sys.exit(0 if report.ok else 1)
    elif args.command == "plan":
        report = check_plan(json.loads(Path(args.plan_file or plan_file()).read_text()))
        print(report.render())
        sys.exit(0 if report.ok else 1)
    elif args.command == "score":
        name = injury_score_name()
        if not name:
            sys.exit("No injury score is tracked (set injury_score.name in athlete/settings.json to start one).")
        import icu

        today = dt.date.today()
        scores = parse_scores(icu.wellness(str(today - dt.timedelta(days=28)), str(today)), name)
        for d, sc in scores:
            print(f"{d}  {sc:g}/10")
        print(score_cleared(scores, today, name)[1])


if __name__ == "__main__":
    main()
