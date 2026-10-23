"""intervals.icu API client for the coach.

The API key comes from the INTERVALS_ICU_API_KEY environment variable or, on macOS, the Keychain
(service "intervals-icu"). It's read on every call and never printed or written to disk.

Usage:
    python3 scripts/icu.py athlete
    python3 scripts/icu.py runs --days 42            # recent runs, one per line
    python3 scripts/icu.py weeks --days 84           # weekly run km, run count, longest run, ride km
    python3 scripts/icu.py wellness --days 14        # HRV, resting HR, sleep, injury score
    python3 scripts/icu.py score 2 [--date DATE]     # log the morning injury score (default today)
    python3 scripts/icu.py events 2026-09-28 2026-10-04
    python3 scripts/icu.py push WEEK_FILE [--dry-run]
    python3 scripts/icu.py delete WEEK_FILE
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://intervals.icu/api/v1"
ATHLETE = "0"  # 0 means the athlete that owns the API key
API_KEY_ENV = "INTERVALS_ICU_API_KEY"
KEYCHAIN_SERVICE = "intervals-icu"
RUN_TYPES = {"Run", "VirtualRun", "TrailRun"}
EXTERNAL_ID_PREFIX = "nikolai"
# Cloudflare in front of intervals.icu rejects Python's default User-Agent.
USER_AGENT = "nikol.ai/2 (personal training coach)"


class IcuError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if key:
        return key
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                check=True, capture_output=True, text=True,
            )
            return out.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    raise IcuError(
        f"No intervals.icu API key. Set {API_KEY_ENV}, or on macOS store it in the Keychain with: "
        f'security add-generic-password -s {KEYCHAIN_SERVICE} -a "$USER" -w'
    )


def request(method: str, path: str, params: dict | None = None, body=None, retries: int = 3):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    token = base64.b64encode(f"API_KEY:{_api_key()}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(int(exc.headers.get("Retry-After", "5")))
                continue
            detail = exc.read().decode(errors="replace")[:500]
            raise IcuError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
            # Network blips (TLS handshake timeouts, resets). Every write here is an upsert or a
            # PUT, so retrying is safe.
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise IcuError(f"{method} {path} failed: {exc}") from exc
    raise IcuError(f"{method} {path} failed after {retries} retries")


# ---- Reads ----

def activities(oldest: str, newest: str) -> list[dict]:
    return request("GET", f"/athlete/{ATHLETE}/activities", {"oldest": oldest, "newest": newest}) or []


def wellness(oldest: str, newest: str) -> list[dict]:
    return request("GET", f"/athlete/{ATHLETE}/wellness", {"oldest": oldest, "newest": newest}) or []


def with_score(comments: str | None, name: str, score: float) -> str:
    """Wellness comments with 'name: N' set to score, keeping any other text."""
    from guardrails import score_re

    entry = f"{name}: {score:g}"
    comments = (comments or "").strip()
    pattern = score_re(name)
    if pattern.search(comments):
        return pattern.sub(entry, comments, count=1)
    return f"{entry}\n{comments}" if comments else entry


def log_score(day: str, name: str, score: float) -> str:
    """Write the injury score into that day's wellness comments and return the saved comments."""
    rows = wellness(day, day)
    comments = with_score(rows[0].get("comments") if rows else None, name, score)
    saved = request("PUT", f"/athlete/{ATHLETE}/wellness/{day}", body={"id": day, "comments": comments})
    return (saved or {}).get("comments", comments)


def events(oldest: str, newest: str) -> list[dict]:
    return request("GET", f"/athlete/{ATHLETE}/events", {"oldest": oldest, "newest": newest}) or []


def run_history(oldest: str, newest: str) -> list[tuple[dt.date, float]]:
    """Completed runs as (date, km), oldest first."""
    runs = [
        (dt.date.fromisoformat(a["start_date_local"][:10]), (a.get("distance") or 0) / 1000)
        for a in activities(oldest, newest)
        if a.get("type") in RUN_TYPES
    ]
    return sorted(runs)


# ---- Week files and pushing ----

def load_week(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def external_id(session: dict) -> str:
    return f"{EXTERNAL_ID_PREFIX}-{session['date']}-{session['id']}"


def to_event(session: dict) -> dict:
    """Turn a week-file session into an intervals.icu calendar event."""
    event = {
        "start_date_local": f"{session['date']}T00:00:00",
        "name": session["name"],
        "external_id": external_id(session),
    }
    if session["category"] == "WORKOUT":
        event.update({
            "category": "WORKOUT",
            "type": session["type"],
            "description": session["description"],
        })
        if session.get("target"):
            event["target"] = session["target"]
    else:
        event.update({
            "category": "NOTE",
            "end_date_local": f"{session['date']}T00:00:00",
            "description": session.get("description", ""),
        })
    return event


def week_range(week: dict) -> tuple[str, str]:
    """From the week's start date to the following Sunday."""
    start = dt.date.fromisoformat(week["start"])
    return str(start), str(start + dt.timedelta(days=6 - start.weekday()))


def stale_external_ids(existing: list[dict], week: dict) -> list[str]:
    """Events this coach created in the week's range that are no longer in the week file."""
    wanted = {external_id(s) for s in week["sessions"]}
    return sorted(
        e["external_id"] for e in existing
        if (e.get("external_id") or "").startswith(f"{EXTERNAL_ID_PREFIX}-") and e["external_id"] not in wanted
    )


def push(week: dict) -> list[str]:
    """Upsert the week's events and remove ones dropped from the file. Returns removed external ids."""
    body = [to_event(s) for s in week["sessions"]]
    request("POST", f"/athlete/{ATHLETE}/events/bulk", {"upsert": "true"}, body)
    stale = stale_external_ids(events(*week_range(week)), week)
    if stale:
        request("PUT", f"/athlete/{ATHLETE}/events/bulk-delete", None, [{"external_id": x} for x in stale])
    return stale


def overview_events(plan: dict, detailed_starts: set[str]) -> list[dict]:
    """A Monday note per plan week that has no detailed week file yet, plus the race if the plan has one."""
    out = []
    for w in plan["weeks"]:
        if w["start"] in detailed_starts:
            continue
        long_run = f", long run {w['long_run_km']:g} km" if w.get("long_run_km") else ""
        out.append({
            "category": "NOTE",
            "start_date_local": f"{w['start']}T00:00:00",
            "end_date_local": f"{w['start']}T00:00:00",
            "name": f"Week {w['week']} ({w['phase']}): {w['run_km']:g} km{long_run}",
            "description": "\n".join(
                [w["key"]] + ([f"Rides: {w['rides']}"] if w.get("rides") else [])
                + ["Overview only. Detailed workouts are added about 2 weeks ahead."]),
            "external_id": f"{EXTERNAL_ID_PREFIX}-{w['start']}-overview",
        })
    if not plan.get("race_date"):
        return out  # a training block with no race yet
    goal = f"Goal {plan['goal']}." if plan.get("goal") else None
    fallback = f"Anything {plan['fallback']} is a good result." if plan.get("fallback") else None
    out.append({
        "category": "RACE_A",
        "type": "Run",
        "start_date_local": f"{plan['race_date']}T00:00:00",
        "name": plan.get("event", "Race"),
        "description": " ".join(filter(None, [goal, fallback, plan.get("race_note")])),
        "distance": plan.get("race_distance_m", 42195),
        "external_id": f"{EXTERNAL_ID_PREFIX}-{plan['race_date']}-race",
    })
    return out


def push_overview(plan: dict, weeks_dir: Path) -> int:
    detailed = {load_week(f)["start"] for f in weeks_dir.glob("*.json")}
    body = overview_events(plan, detailed)
    request("POST", f"/athlete/{ATHLETE}/events/bulk", {"upsert": "true"}, body)
    # Overview notes for weeks that now have a detailed file are stale.
    stale = [{"external_id": f"{EXTERNAL_ID_PREFIX}-{start}-overview"} for start in sorted(detailed)]
    request("PUT", f"/athlete/{ATHLETE}/events/bulk-delete", None, stale)
    return len(body)


def delete(week: dict) -> None:
    ids = [{"external_id": external_id(s)} for s in week["sessions"]]
    request("PUT", f"/athlete/{ATHLETE}/events/bulk-delete", None, ids)


def step_targets(step: dict) -> set[str]:
    return {k for k in ("hr", "pace", "power") if step.get(k)}


def verify(week: dict) -> list[str]:
    """Re-read pushed events and report problems (missing events, steps without targets)."""
    problems = []
    dates = [s["date"] for s in week["sessions"]]
    found = {e.get("external_id"): e for e in events(min(dates), max(dates))}
    for s in week["sessions"]:
        event = found.get(external_id(s))
        if event is None:
            problems.append(f"{s['date']} {s['name']}: not found on the calendar")
            continue
        if s["category"] != "WORKOUT":
            continue
        steps = _flatten((event.get("workout_doc") or {}).get("steps") or [])
        if not steps:
            problems.append(f"{s['date']} {s['name']}: intervals.icu parsed no workout steps")
        for i, step in enumerate(steps, 1):
            if not step_targets(step):
                problems.append(f"{s['date']} {s['name']}: step {i} has no target (would show as No Target)")
        if event.get("push_errors"):
            problems.append(f"{s['date']} {s['name']}: push to the watch failed: {event['push_errors']}")
    return problems


def _flatten(steps: list[dict]) -> list[dict]:
    out = []
    for step in steps:
        if step.get("steps"):
            out.extend(_flatten(step["steps"]))
        else:
            out.append(step)
    return out


# ---- Summaries ----

def _fmt_pace(seconds_per_km: float) -> str:
    s = round(seconds_per_km)
    return f"{s // 60}:{s % 60:02d}"


def print_runs(days: int) -> None:
    oldest, newest = _window(days)
    for a in sorted(activities(oldest, newest), key=lambda a: a["start_date_local"]):
        if a.get("type") not in RUN_TYPES:
            continue
        km = (a.get("distance") or 0) / 1000
        pace = _fmt_pace(a["moving_time"] / km) if km else "-"
        print(f"{a['start_date_local'][:10]}  {km:5.1f} km  {pace}/km  HR {a.get('average_heartrate') or '-'}  "
              f"{a.get('name') or ''}")


def print_weeks(days: int) -> None:
    oldest, newest = _window(days)
    weeks: dict[dt.date, list[float]] = {}
    for a in activities(oldest, newest):
        day = dt.date.fromisoformat(a["start_date_local"][:10])
        monday = day - dt.timedelta(days=day.weekday())
        w = weeks.setdefault(monday, [0.0, 0, 0.0, 0.0])
        km = (a.get("distance") or 0) / 1000
        if a.get("type") in RUN_TYPES:
            w[0] += km
            w[1] += 1
            w[2] = max(w[2], km)
        elif "Ride" in (a.get("type") or ""):
            w[3] += km
    print("week        run km  runs  longest  ride km")
    for monday in sorted(weeks):
        w = weeks[monday]
        print(f"{monday}  {w[0]:6.1f}  {w[1]:4d}  {w[2]:7.1f}  {w[3]:7.0f}")


def print_wellness(days: int) -> None:
    from guardrails import injury_score_name, parse_scores

    oldest, newest = _window(days)
    rows = wellness(oldest, newest)
    name = injury_score_name()
    scores = dict(parse_scores(rows, name)) if name else {}
    print(f"date        HRV  RHR  sleep  {(name or 'score')[:8]:>8}  comments")
    for r in rows:
        sleep = f"{r['sleepSecs'] / 3600:.1f}h" if r.get("sleepSecs") else "-"
        day = dt.date.fromisoformat(r["id"])
        score = scores.get(day, "-")
        print(f"{r['id']}  {r.get('hrv') or '-':>3}  {r.get('restingHR') or '-':>3}  {sleep:>5}  {score!s:>8}  "
              f"{(r.get('comments') or '').strip()[:40]}")


def _window(days: int) -> tuple[str, str]:
    today = dt.date.today()
    return str(today - dt.timedelta(days=days)), str(today)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("athlete")
    for name in ("runs", "weeks", "wellness"):
        p = sub.add_parser(name)
        p.add_argument("--days", type=int, default={"runs": 42, "weeks": 84, "wellness": 14}[name])
    p_score = sub.add_parser("score", help="Log the morning injury score in wellness comments")
    p_score.add_argument("score", type=float)
    p_score.add_argument("--date", default=str(dt.date.today()))
    p_events = sub.add_parser("events")
    p_events.add_argument("oldest")
    p_events.add_argument("newest")
    p_push = sub.add_parser("push", help="Check guardrails, push a week file, then verify it")
    p_push.add_argument("week_file")
    p_push.add_argument("--dry-run", action="store_true", help="Run the guardrails and show events without pushing")
    sub.add_parser("overview", help="Push a Monday overview note for every week without a detailed file, plus the race")
    p_delete = sub.add_parser("delete", help="Remove a week file's events from the calendar")
    p_delete.add_argument("week_file")
    args = parser.parse_args()

    try:
        if args.command == "athlete":
            a = request("GET", f"/athlete/{ATHLETE}")
            print(json.dumps({k: a.get(k) for k in ("id", "name", "timezone")}, indent=2))
        elif args.command == "runs":
            print_runs(args.days)
        elif args.command == "weeks":
            print_weeks(args.days)
        elif args.command == "wellness":
            print_wellness(args.days)
        elif args.command == "score":
            from guardrails import injury_score_name

            name = injury_score_name()
            if not name:
                raise IcuError("No injury score is tracked (set injury_score.name in athlete/settings.json).")
            if not 0 <= args.score <= 10:
                raise IcuError("The score must be 0-10")
            print(f"{args.date}: {log_score(args.date, name, args.score)}")
        elif args.command == "events":
            for e in events(args.oldest, args.newest):
                print(f"{e['start_date_local'][:10]}  {e.get('category'):8}  {e.get('type') or '':8}  "
                      f"{e.get('name')}  [{e.get('external_id') or 'manual'}]")
        elif args.command == "push":
            from guardrails import check_week

            week = load_week(args.week_file)
            report = check_week(week)
            print(report.render())
            if not report.ok:
                sys.exit("Guardrails failed. Nothing was pushed.")
            if args.dry_run:
                print(json.dumps([to_event(s) for s in week["sessions"]], indent=2))
                return
            removed = push(week)
            for x in removed:
                print(f"Removed stale event {x}")
            problems = verify(week)
            if problems:
                print("Pushed, but verification found problems:")
                for p in problems:
                    print(f"  - {p}")
                sys.exit(1)
            print(f"Pushed and verified {len(week['sessions'])} events for week {week['week']}.")
        elif args.command == "overview":
            from guardrails import event_dir

            count = push_overview(json.loads((event_dir() / "plan.json").read_text()), event_dir() / "weeks")
            print(f"Pushed {count} overview events (weekly notes plus the race).")
        elif args.command == "delete":
            delete(load_week(args.week_file))
            print("Deleted.")
    except IcuError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
