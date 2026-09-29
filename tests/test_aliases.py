"""Keep the alias fixtures reproducible and accepted by the script compiler."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import alias_cases


class AliasTests(unittest.TestCase):
    def test_native_alias_fixtures(self):
        self.assertEqual((ROOT / "tests/syntax_test_aliases.vibe").read_text(), alias_cases.render())

    def test_alias_cases_are_valid_scripts(self):
        cases = alias_cases.cases()
        self.assertEqual(len(cases), len({case["name"] for case in cases}))
        for case in cases:
            with self.subTest(case=case["name"]):
                for row, column, _ in case["assertions"]:
                    self.assertTrue(0 <= column < len(case["source"].splitlines()[row]))
                if executable := os.environ.get("VIBES"):
                    checked = subprocess.run([executable, "check", "--eval", case["source"]], capture_output=True, text=True)
                    self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_generic_declarations_remain_prelude_notation(self):
        if executable := os.environ.get("VIBES"):
            for source in ("type box<T> = array<T>\n", "def p<T>(value: T)\nend\n"):
                with self.subTest(source=source):
                    checked = subprocess.run([executable, "check", "--eval", source], capture_output=True, text=True)
                    self.assertNotEqual(checked.returncode, 0)


if __name__ == "__main__":
    unittest.main()
