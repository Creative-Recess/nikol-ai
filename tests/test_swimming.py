import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails as g  # noqa: E402
import icu  # noqa: E402
import sports  # noqa: E402
import swim  # noqa: E402

D = dt.date
MON = D(2027, 1, 4)
SWIM = sports.SPORTS["Swim"]

# The format pushed to a Garmin Forerunner 255S and checked on the watch (31 Oct 2026).
TESTED = ("Pool length: 50m\n\nWarmup\n- Easy 2.20 per 100 200mtr\n\nMain Set 4x\n- Hold 1.55-2.05 per 100 100mtr\n"
          "- Rest 20s\n\nCooldown\n- Easy 2.30 per 100 100mtr")


def swim_session(day, km, text=TESTED, kind="easy", sid="swim"):
    return {"id": sid, "date": str(day), "category": "WORKOUT", "type": "Swim", "kind": kind,
            "name": f"{kind} swim", "distance_km": km, "description": text}


def errors_for(text, pool=None):
    report = g.Report()
    g.check_workout_text(swim_session(MON, 0.7, text), report, pool)
    return report.errors


class SwimTextTest(unittest.TestCase):
    def test_tested_format_passes(self):
        self.assertEqual(errors_for(TESTED), [])

    def test_pace_targets_fail_with_a_pointer_to_step_text(self):
        for text in ("Pool length: 25m\n\n- 100mtr 1:55/100m Pace", "Pool length: 25m\n\n- 300mtr 80-85% Pace"):
            self.assertTrue(any("Write the pace into the step text" in e for e in errors_for(text)), text)

    def test_hr_targets_fail(self):
        self.assertTrue(errors_for("Pool length: 25m\n\n- 400mtr 70% LTHR"))

    def test_colon_in_step_text_fails(self):
        self.assertTrue(any("colon" in e for e in errors_for("Pool length: 25m\n\n- Hold 1:55 per 100 100mtr")))

    def test_step_needs_a_distance_or_to_be_a_rest(self):
        self.assertTrue(any("needs a distance" in e for e in errors_for("Pool length: 25m\n\n- Easy 5m")))
        self.assertEqual(errors_for("Pool length: 25m\n\n- Easy 2.20 per 100 1.5km\n- Rest 30s"), [])

    def test_metres_written_as_minutes_fails(self):
        self.assertTrue(any("means minutes" in e for e in errors_for("Pool length: 25m\n\n- 400m")))

    def test_missing_pool_length_fails(self):
        self.assertTrue(any("Pool length" in e for e in errors_for("- Easy 2.20 per 100 400mtr")))

    def test_pool_length_must_match_the_athletes_pool(self):
        self.assertTrue(any("athlete's pool is 25 m" in e for e in errors_for(TESTED, pool=25)))
        self.assertEqual(errors_for(TESTED, pool=50), [])


class SwimLoadTest(unittest.TestCase):
    def test_longest_swim_may_grow_20_percent(self):
        report = g.Report()
        g.check_long_runs([(D(2027, 1, 2), 2.5)], [(D(2027, 1, 9), 3.0)], report, SWIM)
        self.assertTrue(report.ok, report.errors)
        report = g.Report()
        g.check_long_runs([(D(2027, 1, 2), 2.5)], [(D(2027, 1, 9), 3.1)], report, SWIM)
        self.assertFalse(report.ok)

    def test_weekly_swim_km(self):
        plan = {"sports": ["Swim"], "weeks": [{"week": 1, "swim_km": 6}, {"week": 2, "swim_km": 7}]}
        week = {"week": 2, "start": str(MON), "sessions": [swim_session(MON + dt.timedelta(days=i), 2.5, sid=f"s{i}")
                                                         for i in (1, 3, 5)]}
        report = g.Report()
        g.check_weekly(week, plan, report)
        self.assertFalse(report.ok)
        self.assertIn("7.5 km of swims is more than 15%", report.errors[0])

    def test_whole_swim_week_passes_offline(self):
        plan = {"sports": ["Swim"], "baseline_long_swim_km": 2.5,
                "weeks": [{"week": 1, "start": str(MON), "swim_km": 6.5, "long_swim_km": 2.5}]}
        week = {"week": 1, "start": str(MON), "sessions": [
            swim_session(MON + dt.timedelta(days=1), 2, sid="tue"), swim_session(MON + dt.timedelta(days=3), 2, sid="thu"),
            swim_session(MON + dt.timedelta(days=6), 2.5, kind="long", sid="sun")]}
        with mock.patch.object(g, "settings", return_value={"swim": {"pool_length_m": 50}}):
            report = g.check_week(week, history=[], scores=[], plan=plan, offline=True)
        self.assertTrue(report.ok, report.render())
        self.assertIn("Workout text: 3 swims, one target type each", report.passes)

    def test_swim_on_an_office_morning_is_timed(self):
        plan = {"schedule": {"office_days": ["Wed"], "office_start": "06:15", "office_done_by": "08:00"}}
        report = g.Report()
        g.check_schedule([swim_session(D(2027, 1, 6), 4)], plan, report)
        self.assertFalse(report.ok)


class VerifySwimTest(unittest.TestCase):
    def test_swim_steps_need_no_targets_but_need_the_pool_length(self):
        week = {"week": 1, "start": str(MON), "sessions": [swim_session(MON, 0.7)]}
        steps = [{"text": "Easy 2.20 per 100", "distance": 200}, {"text": "Rest", "duration": 20}]
        event = {"external_id": icu.external_id(week["sessions"][0]),
                 "workout_doc": {"steps": steps, "options": {"pool_length": "50m"}}}
        with mock.patch.object(icu, "events", return_value=[event]):
            self.assertEqual(icu.verify(week), [])
        event["workout_doc"]["options"] = {}
        with mock.patch.object(icu, "events", return_value=[event]):
            self.assertIn("no pool length", icu.verify(week)[0])


class SwimMathsTest(unittest.TestCase):
    def test_css_from_400_and_200(self):
        self.assertEqual(swim.css(swim.seconds("7:00"), swim.seconds("3:20")), 110)

    def test_slower_200_is_an_error(self):
        with self.assertRaises(ValueError):
            swim.css(200, 210)

    def test_step_text_has_no_colon(self):
        self.assertEqual(swim.step_text(115), "1.55")
        self.assertEqual(swim.clock(125), "2:05")

    def test_threshold_pace_brackets_css(self):
        threshold = dict((name, (fast, slow)) for name, fast, slow in swim.paces(110))["Threshold (CSS)"]
        self.assertEqual(threshold, (108, 112))


if __name__ == "__main__":
    unittest.main()
