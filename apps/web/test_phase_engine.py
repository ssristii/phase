import unittest
from datetime import date, timedelta

from phase_engine import (
    build_plan,
    evaluate_safety,
    predict_cycle,
    validate_exercises,
    weekly_workout_schedule,
)


class CycleEngineTests(unittest.TestCase):
    def test_regular_cycle_estimates_phase_and_fertile_window(self):
        prediction = predict_cycle(date(2026, 10, 23), date(2026, 10, 10))
        self.assertEqual(prediction.phase, "Ovulatory")
        self.assertEqual(prediction.cycle_day, 14)
        self.assertEqual(prediction.fertile_window, (9, 15))
        self.assertIsNone(prediction.confidence)

    def test_cold_start_uses_population_default(self):
        prediction = predict_cycle(date(2026, 10, 23), date(2026, 10, 18))
        self.assertTrue(prediction.population_default)
        self.assertIsNone(prediction.confidence)
        self.assertIn("population prior", prediction.reason)

    def test_unsure_mode_makes_no_phase_or_fertile_window_claim(self):
        prediction = predict_cycle(date.today(), None, unsure=True)
        self.assertIsNone(prediction.phase)
        self.assertIsNone(prediction.confidence)
        self.assertIsNone(prediction.fertile_window)
        self.assertTrue(prediction.symptom_mode)

    def test_future_period_date_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_cycle(date.today(), date.today() + timedelta(days=1))

    def test_poor_sleep_and_high_pain_downgrade_effort(self):
        plan = build_plan("Follicular", "Strength", ["Squat"], 3, 5, 7)
        self.assertIn(plan["tier"], {"reduce", "recovery"})
        self.assertTrue(plan["adjusted"])
        self.assertIn("sleep", plan["reason"])

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
        self.assertGreaterEqual(len(safety.alerts), 3)

    def test_exercise_entry_accepts_catalog_names_and_reports_unknown_names(self):
        supported, unsupported = validate_exercises(
            "bodyweight squat\nWalking, made-up exercise, WALKING"
        )
        self.assertEqual(supported, ["Bodyweight squat", "Walking"])
        self.assertEqual(unsupported, ["made-up exercise"])

    def test_weekly_schedule_has_seven_days_and_adjusts_today(self):
        schedule = weekly_workout_schedule(
            "Follicular",
            "Strength",
            workouts_per_week=3,
            usual_split="Full body",
            energy=2,
            sleep_hours=5,
            pain=7,
            today=date(2026, 10, 19),
        )
        self.assertEqual(len(schedule), 7)
        self.assertEqual(sum(item["is_today"] for item in schedule), 1)
        self.assertTrue(schedule[0]["is_today"])
        self.assertIn("sleep", schedule[0]["reason"])
        self.assertEqual(
            sum(item["type"] == "workout" for item in schedule),
            3,
        )
        split_schedule = weekly_workout_schedule(
            "Luteal",
            "Strength",
            workouts_per_week=4,
            usual_split="Upper/Lower",
            energy=3,
            sleep_hours=7,
            pain=0,
            today=date(2026, 10, 19),
        )
        training_items = [item for item in split_schedule if item["type"] == "workout"]
        self.assertEqual(
            [item["title"].split(" - ")[0] for item in training_items],
            ["Upper body", "Lower body", "Upper body", "Lower body"],
        )

    def test_weekly_schedule_rejects_invalid_frequency(self):
        with self.assertRaises(ValueError):
            weekly_workout_schedule(
                "Follicular",
                "Strength",
                workouts_per_week=0,
                usual_split="Full body",
                energy=3,
                sleep_hours=7,
                pain=0,
                today=date(2026, 10, 19),
            )


if __name__ == "__main__":
    unittest.main()
