import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails as g  # noqa: E402
import icu  # noqa: E402
import power  # noqa: E402
import sports  # noqa: E402

D = dt.date
MON = D(2027, 1, 4)
RIDE = sports.SPORTS["Ride"]


def ride(day, hours, kind="easy", text=None, sid="ride", **extra):
    return dict({"id": sid, "date": str(day), "category": "WORKOUT", "type": "Ride", "kind": kind,
                 "name": f"{kind} ride {hours} h", "duration_h": hours, "target": "POWER",
                 "description": text or f"- {round(hours * 60)}m 56-75%"}, **extra)


def run(day, km, kind="easy", sid="run"):
    return {"id": sid, "date": str(day), "category": "WORKOUT", "type": "Run", "kind": kind,
            "name": f"{kind} {km} km", "distance_km": km, "description": f"- {km}km 69-86% LTHR"}


class RideLoadTest(unittest.TestCase):
    def test_ride_amount_is_moving_time_in_hours(self):
        self.assertEqual(RIDE.amount({"moving_time": 5400, "distance": 50000}), 1.5)

    def test_longest_ride_may_grow_20_percent(self):
        report = g.Report()
        g.check_long_runs([(D(2027, 1, 2), 3.0)], [(D(2027, 1, 9), 3.6)], report, RIDE)
        self.assertTrue(report.ok, report.errors)
        self.assertIn("Long-ride rule: longest planned ride 3.6 h is within 20% of the 30-day max", report.passes)

    def test_longest_ride_over_20_percent_fails(self):
        report = g.Report()
        g.check_long_runs([(D(2027, 1, 2), 3.0)], [(D(2027, 1, 9), 3.75)], report, RIDE)
        self.assertFalse(report.ok)
        self.assertIn("more than 20%", report.errors[0])

    def test_weekly_ride_hours_ramp(self):
        plan = {"sports": ["Ride"], "weeks": [{"week": 1, "ride_hours": 8}, {"week": 2, "ride_hours": 10}]}
        week = {"week": 2, "start": str(MON), "sessions": [ride(MON + dt.timedelta(days=i), 2.5, sid=f"r{i}")
                                                         for i in range(1, 5)]}
        report = g.Report()
        g.check_weekly(week, plan, report)
        self.assertFalse(report.ok)
        self.assertIn("10 h of rides is more than 15%", report.errors[0])

    def test_plan_long_ride_spike_fails(self):
        plan = {"sports": ["Ride"], "baseline_long_ride_hours": 3, "weeks": [
            {"week": 1, "start": str(MON), "ride_hours": 8, "long_ride_hours": 3.5},
            {"week": 2, "start": str(MON + dt.timedelta(days=7)), "ride_hours": 9, "long_ride_hours": 4.5}]}
        report = g.check_plan(plan)
        self.assertFalse(report.ok)
        self.assertIn("long ride 4.5 h", report.errors[0])

    def test_ride_workouts_need_a_duration(self):
        session = ride(MON, 2)
        del session["duration_h"]
        self.assertIn("duration_h", g.missing_fields({"week": 1, "start": str(MON), "sessions": [session]})[0])

    def test_whole_ride_week_passes_offline(self):
        plan = {"sports": ["Ride"], "baseline_long_ride_hours": 3,
                "weeks": [{"week": 1, "start": str(MON), "ride_hours": 7, "long_ride_hours": 3}]}
        week = {"week": 1, "start": str(MON), "sessions": [
            ride(MON + dt.timedelta(days=1), 1.5, kind="threshold", sid="tue",
                 text="Warmup\n- 15m 50-70%\n\nMain Set 3x\n- 8m 95-100%\n- 4m 55%\n\nCooldown\n- 15m 50%"),
            ride(MON + dt.timedelta(days=3), 2.5, sid="thu"),
            ride(MON + dt.timedelta(days=6), 3, kind="long", sid="sun")]}
        report = g.check_week(week, history=[], scores=[], plan=plan, offline=True)
        self.assertTrue(report.ok, report.render())
        self.assertIn("Workout text: 3 rides, one target type each", report.passes)


class RideWorkoutTextTest(unittest.TestCase):
    def errors_for(self, text, session=None):
        report = g.Report()
        g.check_workout_text(session or ride(MON, 1, text=text), report)
        return report.errors

    def test_tested_power_formats_pass(self):
        # Pushed to a Garmin Edge 840 and Forerunner 255S and checked on both (30-31 Oct 2026).
        for text in ("- ramp 10m 50-70% 90rpm\n\n3x\n- 5m 88-94%\n- 3m 55%",
                     "- 15m Z2\n- 5m 200-220w\n- 10m Z1"):
            self.assertEqual(self.errors_for(text), [], text)

    def test_hr_targets_pass_on_rides(self):
        self.assertEqual(self.errors_for("- 20m 69-83% LTHR\n- 10m Z1 HR"), [])

    def test_hr_zone_is_not_mistaken_for_power(self):
        self.assertEqual(g.step_targets("- 10m Z2 HR"), {"hr"})
        self.assertEqual(g.step_targets("- 10m Z2 Pace"), {"pace"})
        self.assertEqual(g.step_targets("- 5m 98-102% pace"), {"pace"})
        self.assertEqual(g.step_targets("- 5km 69-86% LTHR"), {"hr"})

    def test_mixing_power_and_hr_fails(self):
        self.assertTrue(any("mixes HR and power" in e for e in self.errors_for("- 20m 60%\n- 10m 69-80% LTHR")))

    def test_pace_on_a_ride_fails(self):
        self.assertTrue(any("pace targets aren't used for rides" in e for e in self.errors_for("- 20m 5:00/km pace")))

    def test_power_on_a_run_fails(self):
        errors = self.errors_for(None, run(MON, 5) | {"description": "- 30m 60%"})
        self.assertTrue(any("power targets aren't used for runs" in e for e in errors))

    def test_long_ride_steps_in_minutes_are_fine(self):
        self.assertEqual(self.errors_for("- 120m 56-75%"), [])

    def test_swim_workouts_get_a_plain_error_until_swimming_is_coached(self):
        swim = {"id": "swim", "date": str(MON), "category": "WORKOUT", "type": "Swim", "kind": "easy",
                "name": "Swim", "description": "- 400mtr 80% Pace"}
        self.assertEqual(self.errors_for(None, swim),
                         [f"{MON} Swim: swim workouts aren't coached yet, so write it as a note (kind \"swim\")"])

    def test_step_without_target_fails(self):
        self.assertTrue(any("no target" in e for e in self.errors_for("- 20m 60%\n- 10m")))


class RideScheduleTest(unittest.TestCase):
    PLAN = {"schedule": {"office_days": ["Mon", "Wed", "Thu", "Fri"], "office_start": "06:15", "office_done_by": "08:00"}}

    def check(self, sessions):
        report = g.Report()
        g.check_schedule(sessions, self.PLAN, report)
        return report

    def test_long_ride_on_an_office_morning_fails(self):
        self.assertFalse(self.check([ride(D(2027, 1, 6), 2.5)]).ok)

    def test_short_ride_on_an_office_morning_fits(self):
        self.assertTrue(self.check([ride(D(2027, 1, 6), 1.5)]).ok)

    def test_evening_sessions_are_outside_the_morning_budget(self):
        evening = [ride(D(2027, 1, 6), 2.5, time="evening"), dict(run(D(2027, 1, 6), 15), time="evening")]
        self.assertTrue(self.check(evening).ok)

    def test_strength_after_a_ride_workout_fails(self):
        strength = {"id": "s", "date": "2027-01-06", "category": "NOTE", "kind": "strength", "name": "A", "strength": "A"}
        self.assertFalse(self.check([ride(D(2027, 1, 6), 1), strength]).ok)


class CrossTrainingTest(unittest.TestCase):
    def test_ride_workout_before_a_key_run_fails(self):
        report = g.Report()
        g.check_rides([ride(D(2027, 1, 5), 1), run(D(2027, 1, 6), 8, kind="threshold")], report)
        self.assertFalse(report.ok)

    def test_ride_before_a_key_ride_is_fine(self):
        report = g.Report()
        g.check_rides([ride(D(2027, 1, 5), 1, sid="a"), ride(D(2027, 1, 6), 4, kind="long", sid="b")], report)
        self.assertTrue(report.ok, report.errors)

    def test_injury_gate_covers_runs_by_default(self):
        report = g.Report()
        g.check_gates([ride(MON, 1, kind="threshold")], False, "calf 5/10", report)
        self.assertTrue(report.ok)

    def test_injury_gate_can_cover_rides(self):
        report = g.Report()
        g.check_gates([ride(MON, 1, kind="threshold")], False, "knee 5/10", report, ["Run", "Ride"])
        self.assertFalse(report.ok)


class PowerTest(unittest.TestCase):
    def test_zones_match_intervals_defaults(self):
        z = power.zones(200)
        self.assertEqual(z[1], ("Z2", "Endurance", 111, 150))
        self.assertEqual(z[-1], ("Z7", "Neuromuscular", 301, None))

    def test_ftp_from_a_20_minute_test(self):
        self.assertEqual(power.ftp_from_test("20min", 300), 285)

    def test_unknown_test_is_an_error(self):
        with self.assertRaises(ValueError):
            power.ftp_from_test("8min", 300)


class RideOverviewTest(unittest.TestCase):
    def test_ride_weeks_are_summarised_in_hours(self):
        week = {"ride_hours": 8.5, "long_ride_hours": 4}
        self.assertEqual(icu.week_summary(week, sports.coached({"sports": ["Ride"]})), "8.5 h, long ride 4 h")


if __name__ == "__main__":
    unittest.main()
