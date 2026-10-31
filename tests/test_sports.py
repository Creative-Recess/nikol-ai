import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails as g  # noqa: E402
import icu  # noqa: E402
import sports  # noqa: E402

D = dt.date
MON = D(2027, 1, 4)


def run(day, km, kind="easy", sid="run"):
    return {"id": sid, "date": str(day), "category": "WORKOUT", "type": "Run", "kind": kind,
            "name": f"{kind} {km} km", "distance_km": km, "description": f"- {km}km 69-86% LTHR"}


def swim(day):
    return {"id": "swim", "date": str(day), "category": "WORKOUT", "type": "Swim", "kind": "easy",
            "name": "Easy swim", "description": "- 1000mtr 80% Pace"}


class CoachedSportsTest(unittest.TestCase):
    def test_plans_without_sports_coach_running(self):
        self.assertEqual([s.name for s in sports.coached({"weeks": []})], ["Run"])

    def test_listed_sports_keep_their_order(self):
        self.assertEqual([s.name for s in sports.coached({"sports": ["Swim", "Ride", "Run"]})], ["Swim", "Ride", "Run"])

    def test_unknown_sport_is_an_error(self):
        with self.assertRaises(ValueError):
            sports.coached({"sports": ["Rowing"]})

    def test_unknown_sport_fails_the_plan_check(self):
        report = g.check_plan({"sports": ["Rowing"], "weeks": [{"week": 1, "start": "2027-01-04"}]})
        self.assertFalse(report.ok)
        self.assertIn("Rowing", report.errors[0])

    def test_activity_types_map_to_sports(self):
        self.assertEqual(sports.sport_of("TrailRun").name, "Run")
        self.assertEqual(sports.sport_of("VirtualRide").name, "Ride")
        self.assertEqual(sports.sport_of("OpenWaterSwim").name, "Swim")
        self.assertIsNone(sports.sport_of("WeightTraining"))


class OtherSportsInARunningPlanTest(unittest.TestCase):
    PLAN = {"baseline_long_run_km": 10, "weeks": [{"week": 1, "start": str(MON), "run_km": 16}]}

    def test_swims_dont_count_toward_run_km(self):
        week = {"week": 1, "start": str(MON), "sessions": [
            run(MON + dt.timedelta(days=1), 6), swim(MON + dt.timedelta(days=2)),
            run(MON + dt.timedelta(days=6), 10, kind="long", sid="long")]}
        report = g.Report()
        g.check_weekly(week, self.PLAN, report)
        self.assertIn("Weekly run km: 16 km planned vs 16 km target", report.passes)

    def test_non_run_workouts_dont_need_a_distance(self):
        week = {"week": 1, "start": str(MON), "sessions": [swim(MON + dt.timedelta(days=2))]}
        self.assertEqual(g.missing_fields(week), [])

    def test_a_swim_takes_the_rest_day(self):
        days = range(1, 7)
        sessions = [run(MON + dt.timedelta(days=i), 5, sid=f"r{i}") for i in days] + [swim(MON)]
        report = g.Report()
        g.check_rest_day({"week": 1, "start": str(MON), "sessions": sessions}, report)
        self.assertFalse(report.ok)


class PlanWithoutRunningTest(unittest.TestCase):
    """A plan that doesn't coach running skips the running checks instead of crashing on missing run_km."""
    PLAN = {"sports": ["Ride"], "baseline_long_ride_hours": 3, "weeks": [
        {"week": 1, "start": str(MON), "ride_hours": 8, "long_ride_hours": 3},
        {"week": 2, "start": str(MON + dt.timedelta(days=7)), "ride_hours": 9, "long_ride_hours": 3.5}]}

    def test_plan_check_skips_running(self):
        report = g.check_plan(self.PLAN)
        self.assertTrue(report.ok, report.render())
        self.assertFalse(any("run" in w for w in report.warnings), report.warnings)

    def test_week_check_skips_running(self):
        week = {"week": 1, "start": str(MON), "sessions": []}
        report = g.check_week(week, scores=[], plan=self.PLAN, offline=True)
        self.assertTrue(report.ok, report.render())
        self.assertFalse(any("Long-run" in p or "run km" in p for p in report.passes), report.passes)

    def test_running_plan_week_without_run_km_warns(self):
        plan = {"weeks": [{"week": 1, "start": str(MON)}]}
        report = g.Report()
        g.check_weekly({"week": 1, "start": str(MON), "sessions": []}, plan, report)
        self.assertTrue(report.ok)
        self.assertIn("run_km", report.warnings[0])


class OverviewForOtherSportsTest(unittest.TestCase):
    def test_race_type_comes_from_the_plan(self):
        plan = {"sports": ["Swim"], "race_date": "2027-03-01", "race_distance_m": 3800,
                "weeks": [{"week": 1, "start": str(MON), "phase": "Base", "key": "Easy"}]}
        race = icu.overview_events(plan, set())[-1]
        self.assertEqual((race["type"], race["distance"]), ("Swim", 3800))

    def test_marathon_default_is_only_for_runs(self):
        plan = {"sports": ["Ride"], "race_date": "2027-03-01",
                "weeks": [{"week": 1, "start": str(MON), "phase": "Base", "key": "Easy"}]}
        self.assertNotIn("distance", icu.overview_events(plan, set())[-1])

    def test_explicit_race_type_wins(self):
        plan = {"race_type": "Ride", "race_date": "2027-03-01",
                "weeks": [{"week": 1, "start": str(MON), "run_km": 20, "phase": "Base", "key": "Easy"}]}
        self.assertEqual(icu.overview_events(plan, set())[-1]["type"], "Ride")

    def test_multi_sport_summary_names_each_sport(self):
        week = {"run_km": 20, "long_run_km": 10}
        self.assertEqual(icu.week_summary(week, sports.coached({})), "20 km, long run 10 km")
        self.assertEqual(icu.week_summary(week, sports.coached({"sports": ["Run", "Swim"]})),
                         "run 20 km, long run 10 km")


if __name__ == "__main__":
    unittest.main()
