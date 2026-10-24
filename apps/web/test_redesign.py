import unittest
from datetime import date, timedelta

import svg
import theme


class RedesignTests(unittest.TestCase):
    def test_tide_wheel_glyph_counts(self):
        for n in (21, 28, 29, 35):
            markup = svg.tide_wheel_svg(5, n, 5, 14, "phase")
            self.assertEqual(
                markup.count('stroke="rgba(233,212,154,.6)"'), n
            )

    def test_symptom_wheel_has_seven_glyphs_and_no_phase_words(self):
        markup = svg.tide_wheel_svg(7, 7, 0, 0, "symptom", levels=[None] * 7)
        self.assertEqual(markup.count('stroke="rgba(233,212,154,.6)"'), 7)
        for word in ("Menstrual", "Follicular", "Ovulatory", "Luteal"):
            self.assertNotIn(word, markup)

    def test_wave_timeline_has_fourteen_points(self):
        markup = svg.wave_timeline_svg(
            date.today() - timedelta(days=6), days=14, checkins=[]
        )
        self.assertEqual(markup.count("<circle"), 14)

    def test_starfield_is_deterministic(self):
        first = theme.star_positions_for_session()
        second = theme.star_positions_for_session()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 40)

    def test_reduced_motion_css_present(self):
        import pathlib

        source = pathlib.Path("theme.py").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", source)


if __name__ == "__main__":
    unittest.main()
