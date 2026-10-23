import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import paces  # noqa: E402


class PacesTest(unittest.TestCase):
    def test_vdot_from_a_5k(self):
        self.assertAlmostEqual(paces.vdot(5000, paces.parse_time("25:00")), 38.3, places=1)

    def test_vdot_needed_for_330(self):
        self.assertAlmostEqual(paces.vdot(paces.MARATHON_M, paces.parse_time("3:30:00")), 44.6, places=1)

    def test_race_prediction_round_trips(self):
        value = paces.vdot(paces.HALF_M, 95.0)
        self.assertAlmostEqual(paces.race_minutes(value, paces.HALF_M), 95.0, places=2)

    def test_training_paces_at_vdot_40(self):
        p = paces.training_paces(40)
        self.assertEqual(paces.fmt_pace(p["threshold"]), "5:06")
        self.assertEqual(paces.fmt_pace(p["interval"]), "4:41")
        self.assertEqual(paces.fmt_pace(p["easy_fast"]), "5:51")

    def test_goal_marathon_pace(self):
        value = paces.vdot(paces.MARATHON_M, paces.parse_time("3:30:00"))
        self.assertEqual(paces.fmt_pace(paces.training_paces(value)["marathon"]), "4:59")

    def test_distances_in_any_common_form(self):
        self.assertEqual(paces.parse_distance("5k"), 5000)
        self.assertEqual(paces.parse_distance("half"), paces.HALF_M)
        self.assertEqual(paces.parse_distance("21.1km"), 21100)
        self.assertEqual(paces.parse_distance("10000"), 10000)
        with self.assertRaises(ValueError):
            paces.parse_distance("21")

    def test_half_marathon_goal_gives_a_sensible_vdot(self):
        self.assertAlmostEqual(paces.checked_vdot(paces.HALF_M, paces.parse_time("2:00:00")), 36.5, places=1)

    def test_impossible_results_are_rejected(self):
        with self.assertRaises(ValueError):
            paces.checked_vdot(5000, paces.parse_time("30:00:00"))

    def test_format_time(self):
        self.assertEqual(paces.fmt_time(210.0), "3:30:00")
        self.assertEqual(paces.fmt_time(24 + 30 / 60), "24:30")


if __name__ == "__main__":
    unittest.main()
