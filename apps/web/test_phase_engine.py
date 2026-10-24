import unittest
from datetime import date, timedelta

from phase_engine import build_plan, evaluate_safety, predict_cycle


class CycleEngineTests(unittest.TestCase):
    def test_regular_cycle_estimates_phase_and_fertile_window(self):
        prediction = predict_cycle(date(2026, 10, 23), date(2026, 10, 10), 28)
        self.assertEqual(prediction.phase, "Ovulatory")
        self.assertEqual(prediction.cycle_day, 14)
        self.assertEqual(prediction.fertile_window, (9, 15))
        self.assertEqual(prediction.confidence, 0.45)

    def test_cold_start_uses_population_default(self):
        prediction = predict_cycle(date(2026, 10, 23), date(2026, 10, 18))
        self.assertTrue(prediction.population_default)
        self.assertEqual(prediction.confidence, 0.3)
        self.assertIn("population-default", prediction.reason)

    def test_unsure_mode_makes_no_phase_or_fertile_window_claim(self):
        prediction = predict_cycle(date.today(), None, unsure=True)
        self.assertIsNone(prediction.phase)
        self.assertIsNone(prediction.confidence)
        self.assertIsNone(prediction.fertile_window)

    def test_missed_logs_keep_estimate_low_confidence(self):
        prediction = predict_cycle(date(2026, 10, 23), date(2026, 9, 1), 28)
        self.assertEqual(prediction.confidence, 0.45)
        self.assertIn("low-confidence", prediction.reason)

    def test_future_period_date_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_cycle(date.today(), date.today() + timedelta(days=1), 28)

    def test_poor_sleep_and_high_pain_downgrade_effort(self):
        plan = build_plan("Follicular", "Strength", ["Squat"], 3, 5, 7)
        self.assertEqual(plan["title"], "Moderate strength practice")
        self.assertIn("sleep", plan["reason"])
        self.assertIn("pain 7/10", plan["reason"])

    def test_safety_trigger_suppresses_plan(self):
        safety = evaluate_safety(
            today=date(2026, 10, 23),
            last_period_start=date(2026, 7, 1),
            flow="Very heavy",
            pain=8,
            severe_pain=False,
            persistently_irregular_cycles=True,
            positive_pregnancy_test=True,
        )
        self.assertTrue(safety.suppress_plan)
        self.assertEqual(len(safety.alerts), 5)


if __name__ == "__main__":
    unittest.main()
