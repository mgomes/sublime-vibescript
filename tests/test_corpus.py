"""Keep the checked-in real-code scope and indentation fixtures reproducible."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("corpus_fixtures", ROOT / "scripts/corpus_fixtures.py")
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)
CASES = json.loads((ROOT / "tests/corpus_cases.json").read_text())["cases"]


class CorpusTests(unittest.TestCase):
    def test_generated_syntax_matches_cases(self):
        rendered = '# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"\n'
        for case in CASES:
            rendered += RENDERER.syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1]
        self.assertEqual((ROOT / "tests/syntax_test_corpus.vibe").read_text(), rendered)

    def test_assertions_point_to_source_tokens(self):
        self.assertEqual(len(CASES), len({case["name"] for case in CASES}))
        for case in CASES:
            self.assertTrue(case["source"].endswith("\n"), case["name"])
            lines = case["source"].splitlines()
            for row, column, selector in case["assertions"]:
                with self.subTest(case=case["name"], row=row, column=column):
                    self.assertTrue(selector)
                    self.assertTrue(0 <= row < len(lines))
                    self.assertTrue(0 <= column < len(lines[row]))


if __name__ == "__main__":
    unittest.main()
