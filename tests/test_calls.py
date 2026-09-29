"""Audit type-accepting builtins and call boundaries against the Rust prelude."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import call_cases
import type_inventory


class CallTests(unittest.TestCase):
    def test_all_prelude_type_parameters_are_covered(self):
        self.assertEqual(type_inventory.type_call_parameters(type_inventory.PRELUDE.read_text()), call_cases.TYPE_CALLS)
        if compiler := os.environ.get("VIBES"):
            prelude = subprocess.check_output([compiler, "prelude"], text=True)
            self.assertEqual(type_inventory.type_call_parameters(prelude), call_cases.TYPE_CALLS)

    def test_type_parameter_positions_ignore_nested_types_and_defaults(self):
        prelude = '''module Sample
  def parse<T>(text: string = "type", callback: (int, string) -> bool, schema: type<T>) -> T
  def symbol_name(type: symbol) -> bool
end
class T
  def as<U>(type: type<U>) -> U
end
'''
        self.assertEqual(type_inventory.type_call_parameters(prelude), {"Sample.parse": [2], "T.as": [0]})

    def test_generated_fixture_is_current(self):
        self.assertEqual((ROOT / "tests/syntax_test_calls.vibe").read_text(), call_cases.render())

    def test_spacing_and_newlines_match_rust(self):
        if not (compiler := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check the Rust parser")
        for case in call_cases.cases():
            with self.subTest(case=case["name"]):
                checked = subprocess.run([compiler, "check", "--eval", case["source"]], capture_output=True, text=True)
                self.assertEqual(checked.returncode == 0, case["compiler_accepted"], checked.stdout + checked.stderr)
