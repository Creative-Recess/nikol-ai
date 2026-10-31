import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails as g  # noqa: E402
import icu  # noqa: E402
import sports  # noqa: E402

D = dt.date
MON = D(2027, 1, 4)
TRI = sports.coached({"sports": ["Swim", "Ride", "Run"]})


def day(i):
    return MON + dt.timedelta(days=i)


def run(i, km, kind="easy", sid="run", **extra):
    return dict({"id": sid, "date": str(day(i)), "category": "WORKOUT", "type": "Run", "kind": kind,
                 "name": f"{kind} run {km} km", "distance_km": km, "description": f"- {km}km 69-86% LTHR"}, **extra)


def ride(i, hours, kind="easy", sid="ride"):
    return {"id": sid, "date": str(day(i)), "category": "WORKOUT", "type": "Ride", "kind": kind,
            "name": f"{kind} ride {hours} h", "duration_h": hours, "target": "POWER",
            "description": f"- {round(hours * 60)}m 56-75%"}


def swim(i, km, sid="swim"):
    return {"id": sid, "date": str(day(i)), "category": "WORKOUT", "type": "Swim", "kind": "endurance",
            "name": f"Swim {km} km", "distance_km": km,
            "description": f"Pool length: 50m\n\n- Steady 2.05 per 100 {round(km * 1000)}mtr"}


PLAN = {"sports": ["Swim", "Ride", "Run"], "event": "Sample Olympic triathlon", "race_date": "2027-03-07",
        "race_distance_m": 51500, "baseline_long_swim_km": 2, "baseline_long_ride_hours": 2.5,
        "baseline_long_run_km": 12, "weeks": [
            {"week": 1, "start": str(MON), "phase": "Base", "key": "Bricks Sat",
             "swim_km": 6, "long_swim_km": 2.2, "ride_hours": 6, "long_ride_hours": 2.5, "run_km": 25, "long_run_km": 12}]}

WEEK = {"week": 1, "start": str(MON), "sessions": [
    swim(1, 2, sid="tue-swim"), run(1, 7, sid="tue-run", time="evening"),
    ride(2, 1.5, kind="sweet_spot", sid="wed-ride"),
    swim(3, 2.2, sid="thu-swim"), run(3, 6, sid="thu-run", time="evening"),
    swim(4, 1.8, sid="fri-swim"),
    ride(5, 2.5, sid="sat-ride"), run(5, 4, sid="sat-brick", brick=True),
    ride(6, 2, sid="sun-ride"), run(6, 8, kind="long", sid="sun-run")]}


class TriathlonWeekTest(unittest.TestCase):
    def check(self, week=WEEK, ramp=None):
        with mock.patch.object(g, "settings", return_value={"swim": {"pool_length_m": 50}}), \
             mock.patch.object(icu, "wellness", return_value=[{"id": str(MON), "rampRate": ramp}]):
            return g.check_week(week, history={"Run": [(D(2026, 12, 20), 12.0)], "Ride": [], "Swim": []},
                                scores=[], plan=PLAN)

    def test_a_balanced_week_passes(self):
        report = self.check()
        self.assertTrue(report.ok, report.render())
        for line in ("Weekly swim km: 6 km planned vs 6 km target", "Weekly ride h: 6 h planned vs 6 h target",
                     "Weekly run km: 25 km planned vs 25 km target", "Workout text: 10 workouts, one target type each"):
            self.assertIn(line, report.passes)

    def test_each_sports_longest_session_is_checked(self):
        week = dict(WEEK, sessions=[s for s in WEEK["sessions"] if s["id"] != "sat-ride"] + [ride(5, 3.5, sid="sat-ride")])
        report = self.check(week)
        self.assertTrue(any("longest ride" in e for e in report.errors), report.render())

    def test_combined_ramp_above_8_warns(self):
        report = self.check(ramp=9.5)
        self.assertTrue(report.ok)
        self.assertTrue(any("ramp rate is 9.5" in w for w in report.warnings), report.warnings)

    def test_combined_ramp_within_range_passes(self):
        self.assertIn("Combined load: fitness (CTL) ramp rate 4.0 a week across all sports", self.check(ramp=4).passes)


class BrickTest(unittest.TestCase):
    def check(self, sessions):
        report = g.Report()
        g.check_bricks(sessions, report)
        return report

    def test_brick_after_a_ride_passes(self):
        self.assertTrue(self.check([ride(5, 2), run(5, 4, brick=True)]).ok)

    def test_brick_without_a_ride_fails(self):
        self.assertIn("needs a ride the same day", self.check([run(5, 4, brick=True)]).errors[0])

    def test_only_runs_are_bricks(self):
        brick_swim = dict(swim(5, 1), brick=True)
        self.assertIn("only a run", self.check([ride(5, 2), brick_swim]).errors[0])


class RidesInATriathlonTest(unittest.TestCase):
    def test_easy_ride_before_a_key_run_is_fine(self):
        report = g.Report()
        g.check_rides([ride(1, 1.5), run(2, 8, kind="threshold")], report, None, TRI)
        self.assertTrue(report.ok, report.errors)

    def test_hard_ride_before_a_key_run_fails(self):
        report = g.Report()
        g.check_rides([ride(1, 1.5, kind="interval"), run(2, 8, kind="threshold")], report, None, TRI)
        self.assertFalse(report.ok)

    def test_running_plan_still_protects_key_runs_from_any_ride(self):
        report = g.Report()
        g.check_rides([ride(1, 1.5), run(2, 8, kind="threshold")], report, None, sports.coached({}))
        self.assertFalse(report.ok)


class TriathlonOverviewTest(unittest.TestCase):
    def test_race_is_other_and_weeks_name_each_sport(self):
        events = icu.overview_events(PLAN, set())
        self.assertEqual(events[0]["name"],
                         "Week 1 (Base): swim 6 km, long swim 2.2 km; ride 6 h, long ride 2.5 h; run 25 km, long run 12 km")
        self.assertEqual((events[-1]["type"], events[-1]["distance"]), ("Other", 51500))

    def test_plan_passes(self):
        self.assertTrue(g.check_plan(PLAN).ok, g.check_plan(PLAN).render())


if __name__ == "__main__":
    unittest.main()
