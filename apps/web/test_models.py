import unittest
from datetime import date, timedelta

from models import (
    CYCLE_MU0,
    M2_W0,
    SYMPTOM_SD_THRESHOLD,
    build_cycle_model,
    cold_start_predictive_sd,
    detect_period_starts,
    encode_readiness_features,
    evaluate_escalation,
    fit_nig,
    phase_for_day,
    predict_readiness,
    update_readiness_weights,
)


class M1CycleModelTests(unittest.TestCase):
    def test_cold_start_predictive_sd_is_under_symptom_threshold(self):
        sd = cold_start_predictive_sd()
        self.assertAlmostEqual(sd, 4.286, places=2)
        self.assertLess(sd, SYMPTOM_SD_THRESHOLD)

    def test_empty_nig_equals_prior(self):
        posterior = fit_nig(
            [],
            mu0=CYCLE_MU0,
            kappa0=2.0,
            alpha0=2.0,
            beta0=12.25,
        )
        self.assertEqual(posterior.mu, CYCLE_MU0)
        self.assertEqual(posterior.kappa, 2.0)
        self.assertEqual(posterior.alpha, 2.0)
        self.assertEqual(posterior.beta, 12.25)

    def test_single_observation_moves_mean_toward_data(self):
        posterior = fit_nig(
            [30.0],
            mu0=28.0,
            kappa0=2.0,
            alpha0=2.0,
            beta0=12.25,
            gamma=0.92,
        )
        # mu_n = (2*28 + 1*30) / 3 = 86/3
        self.assertAlmostEqual(posterior.mu, 86.0 / 3.0, places=6)
        self.assertAlmostEqual(posterior.kappa, 3.0, places=6)

    def test_period_start_requires_three_dry_days(self):
        checkins = [
            {"checkin_date": date(2026, 1, 1), "flow": "Light"},
            {"checkin_date": date(2026, 1, 2), "flow": "Light"},
            {"checkin_date": date(2026, 1, 3), "flow": "None"},
            {"checkin_date": date(2026, 1, 4), "flow": "None"},
            {"checkin_date": date(2026, 1, 5), "flow": "Light"},  # only 2 dry
            {"checkin_date": date(2026, 1, 6), "flow": "None"},
            {"checkin_date": date(2026, 1, 7), "flow": "None"},
            {"checkin_date": date(2026, 1, 8), "flow": "None"},
            {"checkin_date": date(2026, 1, 9), "flow": "Moderate"},
        ]
        starts, bleeds = detect_period_starts(checkins)
        self.assertEqual(starts, [date(2026, 1, 1), date(2026, 1, 9)])
        # Jan 5 Light continues the first bleed (only two dry days).
        self.assertEqual(bleeds, [3, 1])

    def test_invalid_cycle_lengths_are_excluded(self):
        starts = [date(2026, 1, 1), date(2026, 1, 10), date(2026, 2, 7)]
        # 9 days invalid, 28 days valid
        checkins = [
            {"checkin_date": starts[0], "flow": "Light"},
            {"checkin_date": starts[0] + timedelta(days=1), "flow": "None"},
            {"checkin_date": starts[0] + timedelta(days=2), "flow": "None"},
            {"checkin_date": starts[0] + timedelta(days=3), "flow": "None"},
            {"checkin_date": starts[1], "flow": "Light"},
            {"checkin_date": starts[1] + timedelta(days=1), "flow": "None"},
            {"checkin_date": starts[1] + timedelta(days=2), "flow": "None"},
            {"checkin_date": starts[1] + timedelta(days=3), "flow": "None"},
            {"checkin_date": starts[2], "flow": "Light"},
        ]
        state = build_cycle_model(
            checkins,
            today=starts[2],
            tracking_mode="period_date",
        )
        self.assertEqual(state.valid_cycle_lengths, (28,))
        self.assertEqual(state.excluded_cycle_count, 1)

    def test_unsure_mode_hides_phase_words(self):
        state = build_cycle_model(
            [],
            today=date(2026, 10, 24),
            tracking_mode="unsure",
            last_period_start=None,
        )
        day = phase_for_day(state, today=date(2026, 10, 24))
        self.assertTrue(state.symptom_mode)
        self.assertIsNone(day.phase)
        self.assertIsNone(day.cycle_day)

    def test_phase_boundaries_use_bleed_and_ovulation(self):
        state = build_cycle_model(
            [],
            today=date(2026, 10, 10),
            tracking_mode="period_date",
            last_period_start=date(2026, 10, 1),
        )
        # cold start E=28, B=5, O=14
        self.assertEqual(phase_for_day(state, today=date(2026, 10, 3)).phase, "Menstrual")
        self.assertEqual(phase_for_day(state, today=date(2026, 10, 8)).phase, "Follicular")
        self.assertEqual(phase_for_day(state, today=date(2026, 10, 14)).phase, "Ovulatory")
        self.assertEqual(phase_for_day(state, today=date(2026, 10, 20)).phase, "Luteal")
        late = phase_for_day(state, today=date(2026, 11, 5))
        self.assertEqual(late.phase, "Luteal")
        self.assertTrue(late.late_estimate)


class M2ReadinessTests(unittest.TestCase):
    def test_prior_at_mid_features_is_half(self):
        # sleep_n=energy_n=painfree=mood_n=0.55, no phase one-hot
        features = (0.55, 0.55, 0.55, 0.55, 0.0, 0.0, 0.0, 0.0, 1.0)
        result = predict_readiness(M2_W0, features)
        self.assertAlmostEqual(result.p_too_much, 0.5, places=5)
        self.assertAlmostEqual(result.r_hat, 0.5, places=5)
        self.assertEqual(result.tier, "reduce")

    def test_encode_matches_expected_order(self):
        features = encode_readiness_features(
            sleep_hours=6.0,
            energy=3,
            pain=2,
            mood="Good",
            phase="Follicular",
        )
        self.assertEqual(len(features), 9)
        self.assertAlmostEqual(features[0], 0.5)  # (6-4)/4
        self.assertAlmostEqual(features[1], 0.5)  # (3-1)/4
        self.assertAlmostEqual(features[2], 0.8)  # 1 - 0.2
        self.assertAlmostEqual(features[3], 0.75)
        self.assertEqual(features[4:8], (0.0, 1.0, 0.0, 0.0))
        self.assertEqual(features[8], 1.0)

    def test_update_moves_toward_label_and_stays_clipped(self):
        features = encode_readiness_features(
            sleep_hours=8.0,
            energy=5,
            pain=0,
            mood="Bright",
            phase="Follicular",
        )
        weights = list(M2_W0)
        for _ in range(20):
            weights = update_readiness_weights(
                weights,
                features,
                label_too_much=False,
            )
        result = predict_readiness(weights, features)
        self.assertLess(result.p_too_much, 0.5)
        for weight, prior in zip(weights, M2_W0):
            self.assertGreaterEqual(weight, prior - 2.0)
            self.assertLessEqual(weight, prior + 2.0)


class EscalationTests(unittest.TestCase):
    def test_pain_twice_in_three_days(self):
        today = date(2026, 10, 24)
        checkins = [
            {"checkin_date": today - timedelta(days=2), "flow": "None", "pain": 8},
            {"checkin_date": today, "flow": "None", "pain": 9},
        ]
        alerts = evaluate_escalation(today=today, checkins=checkins)
        self.assertTrue(any("Pain of 8" in alert for alert in alerts))

    def test_heavy_flow_three_days(self):
        today = date(2026, 10, 24)
        checkins = [
            {"checkin_date": today - timedelta(days=2), "flow": "Heavy", "pain": 0},
            {"checkin_date": today - timedelta(days=1), "flow": "Heavy", "pain": 0},
            {"checkin_date": today, "flow": "Very heavy", "pain": 0},
        ]
        alerts = evaluate_escalation(today=today, checkins=checkins)
        self.assertTrue(any("Heavy flow" in alert for alert in alerts))

    def test_short_long_cycle_rule(self):
        alerts = evaluate_escalation(
            today=date(2026, 10, 24),
            checkins=[],
            cycle_lengths=(20, 20, 40, 28),
        )
        self.assertTrue(any("Three of the last four" in alert for alert in alerts))


if __name__ == "__main__":
    unittest.main()
