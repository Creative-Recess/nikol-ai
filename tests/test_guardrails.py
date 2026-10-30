import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails as g  # noqa: E402

D = dt.date


def run(day, km, kind="easy", text=None, sid="run"):
    return {"id": sid, "date": str(day), "category": "WORKOUT", "type": "Run", "kind": kind,
            "name": f"{kind} {km} km", "distance_km": km, "description": text or f"- {km}km 69-86% LTHR"}


PLAN = {"weeks": [
    {"week": 0, "run_km": 11, "down_week": True},
    {"week": 1, "run_km": 22, "down_week": False},
    {"week": 2, "run_km": 24, "down_week": False},
    {"week": 3, "run_km": 27, "down_week": False},
    {"week": 4, "run_km": 24, "down_week": True},
    {"week": 5, "run_km": 30, "down_week": False},
]}
CLEARED = [(D(2026, 9, 14) + dt.timedelta(days=i), 1.0) for i in range(14)]


class LongRunTest(unittest.TestCase):
    def test_within_ten_percent_passes(self):
        report = g.Report()
        g.check_long_runs([(D(2026, 9, 9), 9.1)], [(D(2026, 10, 4), 10.0)], report)
        self.assertTrue(report.ok, report.errors)

    def test_over_ten_percent_fails(self):
        report = g.Report()
        g.check_long_runs([(D(2026, 9, 9), 9.1)], [(D(2026, 10, 4), 12.0)], report)
        self.assertFalse(report.ok)

    def test_failure_has_no_pass_line(self):
        report = g.Report()
        g.check_long_runs([(D(2026, 9, 9), 9.1)], [(D(2026, 10, 4), 12.0)], report)
        self.assertEqual(report.passes, [])

    def test_pass_ignores_earlier_failures(self):
        report = g.Report()
        report.errors.append("an earlier check failed")
        g.check_long_runs([(D(2026, 9, 9), 9.1)], [(D(2026, 10, 4), 10.0)], report)
        self.assertEqual(len(report.passes), 1)

    def test_runs_older_than_30_days_dont_count(self):
        report = g.Report()
        g.check_long_runs([(D(2026, 7, 19), 19.0), (D(2026, 9, 9), 9.1)], [(D(2026, 10, 4), 15.0)], report)
        self.assertFalse(report.ok)

    def test_earlier_planned_runs_raise_the_limit(self):
        report = g.Report()
        planned = [(D(2026, 9, 27), 10.0), (D(2026, 10, 4), 11.0)]
        g.check_long_runs([(D(2026, 9, 9), 9.1)], planned, report)
        self.assertTrue(report.ok, report.errors)


class WeeklyTest(unittest.TestCase):
    def week(self, n, kms):
        return {"week": n, "start": "2026-10-26", "sessions": [run(D(2026, 10, 26) + dt.timedelta(days=i), km) for i, km in enumerate(kms)]}

    def test_normal_progression_passes(self):
        report = g.Report()
        g.check_weekly(self.week(5, [8, 8, 14]), PLAN, report)
        self.assertTrue(report.ok, report.errors)

    def test_more_than_15_percent_over_last_full_week_fails(self):
        report = g.Report()
        g.check_weekly(self.week(5, [10, 10, 14]), PLAN, report)
        self.assertFalse(report.ok)

    def test_down_weeks_are_not_ramp_checked(self):
        report = g.Report()
        g.check_weekly(self.week(4, [10, 14]), PLAN, report)
        self.assertTrue(report.ok, report.errors)

    def test_unknown_week_fails(self):
        report = g.Report()
        g.check_weekly(self.week(99, [5]), PLAN, report)
        self.assertFalse(report.ok)


class WorkoutTextTest(unittest.TestCase):
    def errors_for(self, text):
        report = g.Report()
        g.check_workout_text(run(D(2026, 10, 1), 5, text=text), report)
        return report.errors

    def test_percent_lthr_passes(self):
        self.assertEqual(self.errors_for("- 5km 69-86% LTHR"), [])

    def test_words_in_the_notes_are_not_targets(self):
        text = "Keep HR at or below 150 even if pace is slower. Walk 400m if needed.\n\n- 10km 69-86% LTHR"
        self.assertEqual(self.errors_for(text), [])

    def test_pace_workout_passes(self):
        self.assertEqual(self.errors_for("- 2km 5:15-6:00/km pace\n\n4x\n- 5m 4:45/km pace\n- 2m 5:30-6:00/km pace"), [])

    def test_bpm_is_rejected(self):
        self.assertTrue(any("bpm" in e for e in self.errors_for("- 5km 120-150bpm HR")))

    def test_mixed_targets_are_rejected(self):
        self.assertTrue(any("mixes" in e for e in self.errors_for("- 2km 69-86% LTHR\n- 3km 4:45/km pace")))

    def test_bare_pace_is_rejected(self):
        self.assertTrue(self.errors_for("- 3km 4:45/km"))

    def test_metres_written_as_minutes_is_rejected(self):
        self.assertTrue(any("minutes" in e for e in self.errors_for("- 400m 4:11/km pace")))

    def test_step_without_target_is_rejected(self):
        self.assertTrue(any("no target" in e for e in self.errors_for("- 2km 69-86% LTHR\n- 3km")))


class AchillesTest(unittest.TestCase):
    TODAY = D(2026, 9, 27)

    def test_parses_scores_from_comments(self):
        rows = [{"id": "2026-09-25", "comments": "Achilles: 2, slept ok"}, {"id": "2026-09-26", "comments": "no score"}]
        self.assertEqual(g.parse_scores(rows, "achilles"), [(D(2026, 9, 25), 2.0)])

    def test_no_scores_is_assumed_fine(self):
        self.assertTrue(g.score_cleared([], self.TODAY)[0])

    def test_low_scores_are_fine(self):
        self.assertTrue(g.score_cleared(CLEARED, self.TODAY)[0])

    def test_three_out_of_ten_is_still_fine(self):
        self.assertTrue(g.score_cleared([(self.TODAY, 3.0)], self.TODAY)[0])

    def test_flare_above_three_pauses_quality(self):
        scores = CLEARED[:-1] + [(self.TODAY, 4.0)]
        self.assertFalse(g.score_cleared(scores, self.TODAY)[0])

    def test_rising_trend_pauses_quality(self):
        scores = [(self.TODAY - dt.timedelta(days=i), 0.0) for i in range(7, 14)]
        scores += [(self.TODAY - dt.timedelta(days=i), 2.0) for i in range(0, 7)]
        self.assertFalse(g.score_cleared(scores, self.TODAY)[0])

    def test_old_flare_no_longer_counts(self):
        self.assertTrue(g.score_cleared([(self.TODAY - dt.timedelta(days=10), 5.0)], self.TODAY)[0])

    def test_mentioning_strides_in_notes_is_not_gated(self):
        report = g.Report()
        g.check_gates([run(D(2026, 10, 1), 4, text="No strides this week.\n\n- 4km 69-86% LTHR")], False, "flare", report)
        self.assertTrue(report.ok, report.errors)

    def test_strides_flag_is_gated_during_a_flare(self):
        session = dict(run(D(2026, 10, 1), 6), strides=True)
        report = g.Report()
        g.check_gates([session], False, "flare", report)
        self.assertFalse(report.ok)

    def test_quality_sessions_paused_during_a_flare(self):
        report = g.Report()
        g.check_gates([run(D(2026, 10, 1), 7, kind="threshold")], False, "flare", report)
        self.assertFalse(report.ok)


class RideTest(unittest.TestCase):
    def test_ride_before_long_run_fails(self):
        ride = {"id": "ride", "date": "2026-10-03", "category": "NOTE", "kind": "ride", "name": "Ride"}
        report = g.Report()
        g.check_rides([ride, run(D(2026, 10, 4), 10, kind="long")], report)
        self.assertFalse(report.ok)

    def test_exception_allows_ride_before_easy_long_run_as_a_warning(self):
        ride = {"id": "ride", "date": "2026-10-03", "category": "NOTE", "kind": "ride", "name": "Long ride"}
        report = g.Report()
        g.check_rides([ride, run(D(2026, 10, 4), 10, kind="long")], report, {"ride_before_long_run": "short easy long run"})
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(report.warnings)

    def test_exception_never_covers_key_sessions(self):
        ride = {"id": "ride", "date": "2026-10-06", "category": "NOTE", "kind": "ride", "name": "Hills"}
        report = g.Report()
        g.check_rides([ride, run(D(2026, 10, 7), 8, kind="threshold")], report, {"ride_before_long_run": "x"})
        self.assertFalse(report.ok)

    def test_ride_before_easy_run_passes(self):
        ride = {"id": "ride", "date": "2026-09-26", "category": "NOTE", "kind": "ride", "name": "Ride"}
        report = g.Report()
        g.check_rides([ride, run(D(2026, 9, 27), 6)], report)
        self.assertTrue(report.ok)


class AvailabilityTest(unittest.TestCase):
    PLAN = {"unavailable": [{"date": "2026-10-17", "note": "gig"}]}

    def test_run_on_unavailable_date_fails(self):
        report = g.Report()
        g.check_availability([run(D(2026, 10, 17), 4)], self.PLAN, report)
        self.assertFalse(report.ok)

    def test_other_dates_pass(self):
        report = g.Report()
        g.check_availability([run(D(2026, 10, 18), 12)], self.PLAN, report)
        self.assertTrue(report.ok)


class ScheduleTest(unittest.TestCase):
    PLAN = {"schedule": {"office_days": ["Mon", "Wed", "Thu", "Fri"], "wfh_days": ["Tue"],
                         "office_start": "06:15", "office_done_by": "08:00"},
            "holidays": {"2026-10-05": "Labour Day"}}
    RIDE = {"id": "ride", "date": "2026-10-01", "category": "NOTE", "kind": "ride", "name": "Group ride"}

    def check(self, sessions):
        report = g.Report()
        g.check_schedule(sessions, self.PLAN, report)
        return report

    def test_strength_after_a_ride_on_an_office_day_fails(self):
        self.assertFalse(self.check([dict(self.RIDE, strength="B")]).ok)

    def test_strength_after_a_ride_on_wfh_tuesday_fails(self):
        ride = dict(self.RIDE, date="2026-09-29")
        strength = {"id": "s", "date": "2026-09-29", "category": "NOTE", "kind": "strength", "name": "A", "strength": "A"}
        self.assertFalse(self.check([ride, strength]).ok)

    def test_evening_strength_on_a_ride_day_passes(self):
        strength = {"id": "s", "date": "2026-10-01", "category": "NOTE", "kind": "strength", "name": "B",
                    "strength": "B", "time": "evening"}
        self.assertTrue(self.check([self.RIDE, strength]).ok)

    def test_evening_strength_is_outside_the_morning_budget(self):
        strength = {"id": "s", "date": "2026-09-30", "category": "NOTE", "kind": "strength", "name": "A",
                    "strength": "A", "time": "evening"}
        self.assertTrue(self.check([run(D(2026, 9, 30), 12), strength]).ok)

    def test_long_run_on_a_public_holiday_passes(self):
        self.assertTrue(self.check([run(D(2026, 10, 5), 18, kind="medium_long")]).ok)

    def test_upper_body_on_leg_day_fails(self):
        a = dict(run(D(2026, 9, 29), 5), strength="A")
        c = dict(run(D(2026, 9, 29), 3, sid="run2"), strength="C")
        self.assertFalse(self.check([a, c]).ok)

    def test_easy_run_and_upper_body_fits_before_work(self):
        self.assertTrue(self.check([dict(run(D(2026, 9, 28), 10), strength="C")]).ok)

    def test_long_run_on_office_day_fails(self):
        self.assertFalse(self.check([run(D(2026, 9, 30), 18, kind="medium_long")]).ok)

    def test_no_office_hours_means_no_morning_budget(self):
        report = g.Report()
        plan = {"schedule": {"office_days": ["Wed"]}}
        g.check_schedule([run(D(2026, 9, 30), 18, kind="medium_long")], plan, report)
        self.assertTrue(report.ok)

    def test_long_run_on_wfh_tuesday_passes(self):
        self.assertTrue(self.check([run(D(2026, 9, 29), 18, kind="medium_long")]).ok)


class RestDayTest(unittest.TestCase):
    MON = D(2026, 10, 5)

    def week(self, sessions, **extra):
        return dict({"week": 2, "start": str(self.MON), "sessions": sessions}, **extra)

    def ride(self, i):
        return {"id": "ride", "date": str(self.MON + dt.timedelta(days=i)), "category": "NOTE", "kind": "ride", "name": "Ride"}

    def check(self, week):
        report = g.Report()
        g.check_rest_day(week, report)
        return report

    def test_every_day_busy_fails(self):
        sessions = [run(self.MON + dt.timedelta(days=i), 5) for i in (1, 2, 5, 6)] + [self.ride(i) for i in (0, 3, 4)]
        self.assertFalse(self.check(self.week(sessions)).ok)

    def test_one_free_day_passes(self):
        sessions = [run(self.MON + dt.timedelta(days=i), 5) for i in (1, 2, 5, 6)] + [self.ride(i) for i in (0, 3)]
        report = self.check(self.week(sessions))
        self.assertTrue(report.ok, report.errors)
        self.assertIn("Fri 9 Oct", report.passes[0])

    def test_evening_run_on_a_ride_day_keeps_monday_free(self):
        evening = [dict(run(self.MON + dt.timedelta(days=i), 5, sid="pm"), time="evening") for i in (1, 3)]
        sessions = evening + [self.ride(i) for i in (1, 3, 4, 5)] + [run(self.MON + dt.timedelta(days=6), 12, kind="long")]
        report = self.check(self.week(sessions))
        self.assertTrue(report.ok, report.errors)
        self.assertIn("Mon 5 Oct", report.passes[0])

    def test_recovery_note_and_upper_body_still_count_as_rest(self):
        note = {"id": "rest", "date": str(self.MON), "category": "NOTE", "kind": "recovery", "name": "Rest day"}
        upper = {"id": "c", "date": str(self.MON), "category": "NOTE", "kind": "strength", "name": "C", "strength": "C"}
        sessions = [note, upper] + [self.ride(i) for i in range(1, 7)]
        self.assertTrue(self.check(self.week(sessions)).ok)

    def test_leg_strength_is_not_rest(self):
        a = {"id": "a", "date": str(self.MON), "category": "NOTE", "kind": "strength", "name": "A", "strength": "A"}
        self.assertFalse(self.check(self.week([a] + [self.ride(i) for i in range(1, 7)])).ok)

    def test_exception_turns_it_into_a_warning(self):
        report = self.check(self.week([self.ride(i) for i in range(7)], exceptions={"no_rest_day": "cycling tour"}))
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(report.warnings)

    def test_partial_week_is_not_checked(self):
        ride = {"id": "ride", "date": "2026-09-26", "category": "NOTE", "kind": "ride", "name": "Long ride"}
        sessions = [run(D(2026, 9, 25), 5), ride, run(D(2026, 9, 27), 6, sid="run2")]
        report = self.check({"week": 0, "start": "2026-09-25", "sessions": sessions})
        self.assertTrue(report.ok)
        self.assertEqual(report.passes, [])


class ProvisionalRunsTest(unittest.TestCase):
    def test_only_future_runs_from_earlier_weeks_count(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            weeks = Path(tmp)
            week1 = {"start": "2026-09-28", "sessions": [run(D(2026, 9, 28), 5), run(D(2026, 10, 4), 10, kind="long", sid="lr")]}
            week2 = {"start": "2026-10-05", "sessions": [run(D(2026, 10, 6), 11, kind="long")]}
            (weeks / "w1.json").write_text(json.dumps(week1))
            (weeks / "w2.json").write_text(json.dumps(week2))
            got = g.provisional_runs(weeks, today=D(2026, 9, 30), before=D(2026, 10, 5), exclude_start="2026-10-05")
        # 28 Sep is in the past (it's in the real history or it was missed), 4 Oct is still to come.
        self.assertEqual(got, [(D(2026, 10, 4), 10.0)])


class WholeWeekTest(unittest.TestCase):
    def test_week_zero_passes_with_real_history(self):
        week = {"week": 0, "start": "2026-09-25", "sessions": [run(D(2026, 9, 25), 5), run(D(2026, 9, 27), 6, sid="run2")]}
        report = g.check_week(week, history=[(D(2026, 9, 9), 9.1), (D(2026, 9, 14), 5.7)], scores=[], plan=PLAN)
        self.assertTrue(report.ok, report.render())


class NewAthleteTest(unittest.TestCase):
    """What a new athlete hits first: no run history yet, no injury score, an incomplete week file."""
    PLAN = {"baseline_long_run_km": 8, "weeks": [{"week": 1, "start": "2027-01-04", "run_km": 15}]}
    WEEK = {"week": 1, "start": "2027-01-04", "sessions": [
        run(D(2027, 1, 5), 5), run(D(2027, 1, 7), 5, sid="run2"), run(D(2027, 1, 10), 8, kind="long", sid="run3")]}

    def test_baseline_stands_in_for_missing_history(self):
        report = g.check_week(self.WEEK, history=[], scores=[], plan=self.PLAN)
        self.assertTrue(report.ok, report.render())

    def test_without_a_baseline_the_first_long_run_fails(self):
        report = g.check_week(self.WEEK, history=[], scores=[], plan={"weeks": self.PLAN["weeks"]})
        self.assertFalse(report.ok)

    def test_offline_check_needs_no_network(self):
        report = g.check_week(self.WEEK, plan=self.PLAN, offline=True)
        self.assertTrue(report.ok, report.render())
        self.assertTrue(any("Offline" in w for w in report.warnings))

    def test_missing_fields_are_reported_plainly(self):
        week = {"week": 1, "start": "2027-01-04", "sessions": [{"date": "2027-01-05", "category": "WORKOUT"}]}
        report = g.check_week(week, history=[], scores=[], plan=self.PLAN)
        self.assertFalse(report.ok)
        self.assertIn("missing", report.errors[0])

    def test_any_body_part_can_be_scored(self):
        rows = [{"id": "2027-01-03", "comments": "calf: 5"}]
        scores = g.parse_scores(rows, "calf")
        self.assertFalse(g.score_cleared(scores, D(2027, 1, 3), "calf")[0])
        self.assertEqual(g.parse_scores(rows, "achilles"), [])


class PlanTest(unittest.TestCase):
    def plan(self, *weeks, **extra):
        rows = [dict({"week": i + 1, "start": str(D(2027, 1, 4) + dt.timedelta(days=7 * i)), "run_km": km,
                      "long_run_km": lr}, **x) for i, (km, lr, x) in enumerate(weeks)]
        return dict({"weeks": rows, "baseline_long_run_km": 10}, **extra)

    def test_steady_build_passes(self):
        self.assertTrue(g.check_plan(self.plan((20, 10, {}), (22, 11, {}), (25, 12, {}))).ok)

    def test_weekly_jump_over_15_percent_fails(self):
        self.assertFalse(g.check_plan(self.plan((20, 10, {}), (24, 11, {}))).ok)

    def test_down_week_is_not_a_jump(self):
        report = g.check_plan(self.plan((20, 10, {}), (16, 9, {"down_week": True}), (23, 11, {})))
        self.assertTrue(report.ok, report.render())

    def test_long_run_spike_fails(self):
        self.assertFalse(g.check_plan(self.plan((20, 10, {}), (22, 12, {}))).ok)

    def test_baseline_covers_the_first_long_run(self):
        self.assertFalse(g.check_plan(self.plan((20, 12, {}))).ok)
        self.assertTrue(g.check_plan(self.plan((20, 11, {}))).ok)

    def test_gap_between_weeks_fails(self):
        plan = self.plan((20, 10, {}), (22, 11, {}))
        plan["weeks"][1]["start"] = "2027-01-18"
        self.assertFalse(g.check_plan(plan).ok)

    def test_race_before_the_last_week_fails_and_after_it_warns(self):
        self.assertFalse(g.check_plan(self.plan((20, 10, {}), (22, 11, {}), race_date="2027-01-06")).ok)
        report = g.check_plan(self.plan((20, 10, {}), race_date="2027-05-30"))
        self.assertTrue(report.ok and report.warnings)


class TemplateTest(unittest.TestCase):
    """The sample event in template/ is what new athletes copy, so it has to pass the guardrails."""

    def test_sample_week_passes(self):
        import json

        event = g.REPO / "template/events/sample-event"
        plan = json.loads((event / "plan.json").read_text())
        for f in sorted((event / "weeks").glob("*.json")):
            week = json.loads(f.read_text())
            report = g.check_week(week, history=[(D(2026, 12, 13), 10), (D(2026, 12, 20), 9.5)], scores=[], plan=plan)
            self.assertTrue(report.ok, f"{f.name}\n{report.render()}")

    def test_sample_plan_passes(self):
        import json

        plan = json.loads((g.REPO / "template/events/sample-event/plan.json").read_text())
        report = g.check_plan(plan)
        self.assertTrue(report.ok, report.render())

    def test_sample_settings_name_the_sample_event(self):
        import json

        settings = json.loads((g.REPO / "template/settings.json").read_text())
        self.assertTrue((g.REPO / "template/events" / settings["current_event"]).is_dir())


if __name__ == "__main__":
    unittest.main()
