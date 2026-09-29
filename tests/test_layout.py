"""Keep layout coverage complete and scope comparison stricter than selectors."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import layout_cases
import operators

SPEC = importlib.util.spec_from_file_location("native_runner", ROOT / "scripts/native_runner.py")
RUNNER = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {"sublime": SimpleNamespace(Region=lambda start, end: (start, end)),
                              "sublime_api": SimpleNamespace()}):
    SPEC.loader.exec_module(RUNNER)


class LayoutTests(unittest.TestCase):
    def test_generated_syntax_is_current(self):
        self.assertEqual((ROOT / "tests/syntax_test_layout.vibe").read_text(), layout_cases.render())

    def test_operator_and_keyword_coverage(self):
        inventory = layout_cases.inventory()
        names = {item["name"] for item in inventory}
        for prefix, tokens in [("binary ", operators.BINARY_OPERATORS), ("assignment ", operators.ASSIGNMENT_OPERATORS),
                               ("method ", operators.METHOD_OPERATORS), ("symbol ", operators.SYMBOL_OPERATORS)]:
            self.assertEqual({name.removeprefix(prefix) for name in names if name.startswith(prefix)}, set(tokens))
        syntax = (ROOT / "Vibescript.sublime-syntax").read_text()
        variables = dict(re.findall(r"^  (\w+): '(.*)'$", syntax.split("\ncontexts:", 1)[0], re.MULTILINE))
        words = set()
        for rule in re.split(r"\n\s+- match: ", syntax)[1:]:
            pattern, _, attributes = rule.partition("\n")
            if re.search(r"(?:scope:|\d+:) keyword\.", attributes):
                while "{{" in pattern:
                    pattern = re.sub(r"{{(\w+)}}", lambda match: variables[match[1]], pattern)
                for group in re.findall(r"\(([a-z_]+(?:\|[a-z_]+)*)\)", pattern):
                    words.update(group.split("|"))
        self.assertTrue(words)
        self.assertLessEqual(words, {item["token"] for item in inventory})

    def test_layout_locations_point_to_complete_tokens(self):
        cases = layout_cases.cases()
        self.assertEqual(len(cases), len({case["name"] for case in cases}))
        for case in cases:
            lines = case["source"].splitlines()
            for group in case["equal_scopes"]:
                layouts = ({"inline", "space", "tab", "newline", "comment"} if case.get("layout_kind") == "call-spacing" else
                           {"inline", "leading", "trailing", "continued-inline", "continued-leading", "continued-trailing"})
                self.assertLessEqual(layouts,
                                     {location["layout"] for location in group["locations"]})
                for location in group["locations"]:
                    row, column = location["position"]
                    self.assertEqual(lines[row][column:column + len(group["token"])], group["token"])

    def test_comparison_ignores_only_continuation_meta_scopes(self):
        baseline = "source.vibescript keyword.operator.comparison.vibescript"
        group = {"token": "<=", "locations": [{"layout": "inline", "position": [0, 0]},
                                                {"layout": "continued", "position": [1, 0]}]}
        for changed, fails in [
            (baseline + " meta.expression.continuation.vibescript", False),
            (baseline + " meta.annotation.type.vibescript", True),
            ("source.vibescript keyword.operator.vibescript", True),
            (baseline + " keyword.operator.comparison.vibescript", True),
        ]:
            scopes = [baseline, baseline, baseline, changed]
            view = SimpleNamespace(text_point=lambda row, column: row * 2 + column,
                                   substr=lambda region: "<=", scope_name=lambda point: scopes[point])
            failures, count, _ = RUNNER.compare_scope_group(view, group)
            self.assertEqual(bool(failures), fails, changed)
            self.assertEqual(count, 2)

    def test_changed_line_breaks_are_accepted_by_rust(self):
        if not (executable := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check the Rust parser")
        for source in [
            "enum\n Color\n Red\nend\n",
            "items = [1]\nvalue = items&.\nlength\n",
            "opts = {name\n: 1}\n",
            "[1].each {\n|item\n| puts item }\n",
            "type Id =\n[int]\n",
            "type Id =\n{field: int}\n",
            "type Id = array\n<int>\n",
            "def f(&block: (int)\n -> bool) -> int\n1\nend\n",
            "class Box\nprivate # continued\ndef value -> int\n1\nend\nend\n",
            "left = 1\nright = 2\nresult = (true ? left\n: right)\n",
        ]:
            with self.subTest(source=source):
                checked = subprocess.run([executable, "check", "--eval", source], capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main()
