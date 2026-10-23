import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import icu  # noqa: E402

WEEK = {"week": 1, "start": "2026-09-28", "sessions": [
    {"id": "run", "date": "2026-09-30", "category": "WORKOUT", "type": "Run", "name": "Easy 5 km",
     "description": "- 5km 69-86% LTHR", "target": "HR"},
    {"id": "ride", "date": "2026-10-01", "category": "NOTE", "name": "Group ride", "description": "NP 180 W"},
]}


class ScoreCommentTest(unittest.TestCase):
    def test_empty_comments(self):
        self.assertEqual(icu.with_score(None, "achilles", 0), "achilles: 0")

    def test_keeps_other_text(self):
        self.assertEqual(icu.with_score("slept badly", "calf", 2), "calf: 2\nslept badly")

    def test_replaces_an_existing_score(self):
        self.assertEqual(icu.with_score("Achilles: 3, stiff first steps", "achilles", 1.5), "achilles: 1.5, stiff first steps")


class WeekRangeTest(unittest.TestCase):
    def test_full_week_runs_monday_to_sunday(self):
        self.assertEqual(icu.week_range(WEEK), ("2026-09-28", "2026-10-04"))

    def test_partial_week_ends_on_sunday(self):
        self.assertEqual(icu.week_range({"start": "2026-09-25"}), ("2026-09-25", "2026-09-27"))


class StaleEventsTest(unittest.TestCase):
    def test_only_our_dropped_events_are_stale(self):
        existing = [
            {"external_id": "nikolai-2026-09-30-run"},   # still in the file
            {"external_id": "nikolai-2026-10-01-run"},   # dropped from the file
            {"external_id": None},                       # created by hand in intervals.icu
            {"external_id": "other-app-123"},            # created by another app
        ]
        self.assertEqual(icu.stale_external_ids(existing, WEEK), ["nikolai-2026-10-01-run"])


class ToEventTest(unittest.TestCase):
    def test_workout_event(self):
        e = icu.to_event(WEEK["sessions"][0])
        self.assertEqual(e["category"], "WORKOUT")
        self.assertEqual(e["type"], "Run")
        self.assertEqual(e["external_id"], "nikolai-2026-09-30-run")
        self.assertEqual(e["target"], "HR")

    def test_note_event(self):
        e = icu.to_event(WEEK["sessions"][1])
        self.assertEqual(e["category"], "NOTE")
        self.assertNotIn("type", e)


class OverviewTest(unittest.TestCase):
    PLAN = {"event": "City Marathon", "race_date": "2027-05-30", "goal": "3:30:00", "fallback": "sub 3:45",
            "race_note": "6:30am start.", "weeks": [
        {"week": 1, "start": "2026-09-28", "run_km": 22, "long_run_km": 10, "phase": "Rebuild", "key": "Easy"},
        {"week": 3, "start": "2026-10-12", "run_km": 27, "long_run_km": 12, "phase": "Rebuild", "key": "Wed strides",
         "rides": "Tue Hills, Thu Base"},
        {"week": 17, "start": "2027-01-18", "run_km": 32, "long_run_km": None, "phase": "Marathon-specific", "key": "Cycling tour"},
    ]}

    def test_skips_detailed_weeks_and_adds_race(self):
        events = icu.overview_events(self.PLAN, {"2026-09-28"})
        self.assertEqual([e["external_id"] for e in events],
                         ["nikolai-2026-10-12-overview", "nikolai-2027-01-18-overview", "nikolai-2027-05-30-race"])
        self.assertEqual(events[0]["name"], "Week 3 (Rebuild): 27 km, long run 12 km")
        self.assertEqual(events[1]["name"], "Week 17 (Marathon-specific): 32 km")
        self.assertEqual(events[-1]["category"], "RACE_A")
        self.assertIn("Rides: Tue Hills, Thu Base", events[0]["description"])
        self.assertNotIn("Rides", events[1]["description"])
        self.assertEqual(events[-1]["description"], "Goal 3:30:00. Anything sub 3:45 is a good result. 6:30am start.")


class TrainingBlockTest(unittest.TestCase):
    def test_plan_without_a_race_has_no_race_event(self):
        plan = {"weeks": [{"week": 1, "start": "2027-01-04", "run_km": 20, "long_run_km": 10, "phase": "Base", "key": "Easy"}]}
        self.assertEqual([e["category"] for e in icu.overview_events(plan, set())], ["NOTE"])


class VerifyStepsTest(unittest.TestCase):
    def test_flatten_nested_repeats(self):
        steps = [{"pace": {"value": 273}}, {"reps": 4, "steps": [{"pace": {"value": 273}}, {"duration": 90}]}]
        flat = icu._flatten(steps)
        self.assertEqual(len(flat), 3)
        self.assertEqual([bool(icu.step_targets(s)) for s in flat], [True, True, False])


class NetworkRetryTest(unittest.TestCase):
    def setUp(self):
        self._urlopen, self._sleep, self._key = icu.urllib.request.urlopen, icu.time.sleep, icu._api_key
        icu.time.sleep = lambda s: None
        icu._api_key = lambda: "test"

    def tearDown(self):
        icu.urllib.request.urlopen, icu.time.sleep, icu._api_key = self._urlopen, self._sleep, self._key

    def test_retries_a_handshake_timeout_then_succeeds(self):
        import io
        calls = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake(req, timeout):
            calls.append(1)
            if len(calls) == 1:
                raise icu.urllib.error.URLError("_ssl.c:1112: The handshake operation timed out")
            return Resp(b'[{"id": 1}]')

        icu.urllib.request.urlopen = fake
        self.assertEqual(icu.request("GET", "/x"), [{"id": 1}])
        self.assertEqual(len(calls), 2)

    def test_gives_up_with_a_clear_error(self):
        def fake(req, timeout):
            raise icu.urllib.error.URLError("down")

        icu.urllib.request.urlopen = fake
        with self.assertRaises(icu.IcuError):
            icu.request("GET", "/x", retries=2)


class ApiKeyTest(unittest.TestCase):
    def setUp(self):
        self._env = icu.os.environ.pop(icu.API_KEY_ENV, None)
        self._platform = icu.sys.platform

    def tearDown(self):
        icu.os.environ.pop(icu.API_KEY_ENV, None)
        if self._env is not None:
            icu.os.environ[icu.API_KEY_ENV] = self._env
        icu.sys.platform = self._platform

    def test_environment_variable_wins(self):
        icu.os.environ[icu.API_KEY_ENV] = " abc123 "
        self.assertEqual(icu._api_key(), "abc123")

    def test_no_key_outside_macos_explains_both_options(self):
        icu.sys.platform = "linux"
        with self.assertRaises(icu.IcuError) as ctx:
            icu._api_key()
        self.assertIn(icu.API_KEY_ENV, str(ctx.exception))
        self.assertIn("Keychain", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
