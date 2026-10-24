import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHIPPED_SURFACES = (
    ROOT / "apps" / "web" / "streamlit_app.py",
    ROOT / "apps" / "web" / "phase_engine.py",
    ROOT / "apps" / "web" / "persistence.py",
    ROOT / "apps" / "mobile" / "app" / "index.tsx",
    ROOT / "apps" / "api" / "src" / "schema.sql",
)
FORBIDDEN_COPY = (
    "Informational, not a diagnosis",
    "not a diagnosis",
    "How this works",
    "calorie",
    "macro",
    "weight loss",
    "grocery",
    "dietary preference",
)


class ProductCopyTests(unittest.TestCase):
    def test_shipped_surfaces_exclude_removed_features_and_copy(self):
        for path in SHIPPED_SURFACES:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8").casefold()
                for phrase in FORBIDDEN_COPY:
                    self.assertNotIn(phrase.casefold(), content)

    def test_dashboard_does_not_render_model_confidence(self):
        content = (ROOT / "apps" / "web" / "streamlit_app.py").read_text(
            encoding="utf-8"
        ).casefold()
        self.assertNotIn("confidence:", content)
        self.assertNotIn("confidence is", content)


if __name__ == "__main__":
    unittest.main()
