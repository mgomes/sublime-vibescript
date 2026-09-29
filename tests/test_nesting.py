"""Validate the nested native scope and reindent fixtures against Rust scripts."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nested_cases


class NestingTests(unittest.TestCase):
    def test_native_fixture_matches_generator(self):
        self.assertEqual((ROOT / "tests/syntax_test_nested.vibe").read_text(), nested_cases.render())

    def test_nested_cases_are_valid_scripts(self):
        cases = nested_cases.cases()
        self.assertEqual(len(cases), len({case["name"] for case in cases}))
        for case in cases:
            with self.subTest(case=case["name"]):
                for row, column, _ in case["assertions"]:
                    self.assertTrue(0 <= column <= len(case["source"].splitlines()[row]))
                if executable := os.environ.get("VIBES"):
                    checked = subprocess.run([executable, "check", "--eval", case["source"]], capture_output=True, text=True)
                    self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main()
