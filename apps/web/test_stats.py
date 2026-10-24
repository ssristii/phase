import unittest
from datetime import date, timedelta

from stats import build_report_pdf_bytes, compute_cycle_stats, format_stat


class StatsTests(unittest.TestCase):
    def test_hand_computed_mean_median_mode(self):
        # Lengths 28, 30, 28 -> mean 28.666..., median 28, mode 28, range 2, pstdev
        start = date(2026, 1, 1)
        checkins = []
        for offset, flow in (
            (0, "Light"),
            (1, "None"),
            (2, "None"),
            (3, "None"),
            (28, "Light"),
            (29, "None"),
            (30, "None"),
            (31, "None"),
            (58, "Light"),
            (59, "None"),
            (60, "None"),
            (61, "None"),
            (86, "Light"),
        ):
            checkins.append(
                {
                    "checkin_date": start + timedelta(days=offset),
                    "flow": flow,
                    "pain": 0,
                }
            )
        stats = compute_cycle_stats(checkins, today=start + timedelta(days=86))
        self.assertEqual(stats.lengths, (28, 30, 28))
        self.assertAlmostEqual(stats.mean, 28.666666, places=4)
        self.assertEqual(stats.median, 28)
        self.assertEqual(stats.mode, 28)
        self.assertEqual(stats.range_span, 2)
        self.assertEqual(format_stat(stats.mean), "28.7")

    def test_empty_stats(self):
        stats = compute_cycle_stats([], today=date(2026, 10, 24))
        self.assertEqual(stats.cycles_logged, 0)
        self.assertIsNone(stats.mean)

    def test_pdf_contains_self_reported_label(self):
        stats = compute_cycle_stats([], today=date(2026, 10, 24))
        pdf = build_report_pdf_bytes(stats, synthetic=True)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"Self-reported data", pdf)


if __name__ == "__main__":
    unittest.main()
