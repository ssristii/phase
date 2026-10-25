import unittest

import redaction


class RedactionTests(unittest.TestCase):
    def test_feeling_statements_are_unchanged(self):
        for text in (
            "I am feeling good today",
            "I'm tired",
            "I am low on energy",
        ):
            with self.subTest(text=text):
                self.assertEqual(redaction.strip_spoken_names(text), text)

    def test_explicit_introduction_redacts_only_name(self):
        self.assertEqual(
            redaction.strip_spoken_names(
                "my name is Priya and I slept five hours"
            ),
            "my name is [name] and I slept five hours",
        )

    def test_this_is_speaking(self):
        self.assertEqual(
            redaction.strip_spoken_names("this is Priya speaking"),
            "this is [name] speaking",
        )

    def test_call_me(self):
        self.assertEqual(
            redaction.strip_spoken_names("call me Priya"),
            "call me [name]",
        )

    def test_state_word_stoplist(self):
        self.assertEqual(
            redaction.strip_spoken_names("my name is Good"),
            "my name is Good",
        )

    def test_common_case_variations(self):
        self.assertEqual(
            redaction.strip_spoken_names("My name is Priya"),
            "My name is [name]",
        )


if __name__ == "__main__":
    unittest.main()
