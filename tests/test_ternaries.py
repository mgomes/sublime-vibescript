"""Keep the colon sweep reproducible and accepted by the Rust checker."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ternary_cases


class TernaryTests(unittest.TestCase):
    def test_generated_fixture_is_current(self):
        self.assertEqual((ROOT / "tests/syntax_test_ternaries.vibe").read_text(), ternary_cases.render())

    def test_corpus_is_accepted_by_rust(self):
        if not (compiler := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check the Rust parser")
        for case in ternary_cases.cases():
            with self.subTest(case=case["name"]):
                checked = subprocess.run([compiler, "check", "--eval", case["source"]], capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
