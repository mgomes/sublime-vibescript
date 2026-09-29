"""Cross-check every operator spelling against its scopes and continuations."""

import importlib.util
from itertools import product
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("operators", ROOT / "scripts/operators.py")
OPERATORS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPERATORS)
SPEC = importlib.util.spec_from_file_location("corpus_fixtures", ROOT / "scripts/corpus_fixtures.py")
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)
SYNTAX = (ROOT / "Vibescript.sublime-syntax").read_text()
VARIABLES = dict(re.findall(r"^  (\w+): '(.*)'$", SYNTAX.split("\ncontexts:", 1)[0], re.MULTILINE))


def expand(pattern):
    while "{{" in pattern:
        pattern = re.sub(r"{{(\w+)}}", lambda match: "(?:" + VARIABLES[match[1]] + ")", pattern)
    return pattern.replace("''", "'")


def rules(context):
    block = SYNTAX.split("\n  " + context + ":\n", 1)[1]
    block = re.split(r"\n  \S", block, maxsplit=1)[0]
    result = []
    for rule in block.split("    - match: ")[1:]:
        pattern, *lines = rule.splitlines()
        attributes = dict(re.findall(r"^      (scope|push|set): (.*)$", "\n".join(lines), re.MULTILINE))
        result.append((re.compile(expand(pattern.strip("'"))), attributes))
    return result


class OperatorTests(unittest.TestCase):
    def test_native_syntax_fixture_covers_the_operator_inventory(self):
        rendered = '# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"\n'
        for case in OPERATORS.scope_cases() + OPERATORS.continuation_cases():
            rendered += RENDERER.syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1]
        self.assertEqual((ROOT / "tests/syntax_test_operators.vibe").read_text(), rendered)

    def test_binary_operator_scopes_consume_the_entire_operator(self):
        for operator, (category, _, _) in OPERATORS.BINARY_OPERATORS.items():
            for pattern, attributes in rules("operator-tokens"):
                match = pattern.match(operator + " operand")
                if match:
                    with self.subTest(operator=operator):
                        self.assertEqual(match.group(), operator)
                        self.assertEqual(attributes["scope"], f"keyword.operator.{category}.vibescript")
                    break
            else:
                self.fail("No scope for " + operator)

    def test_symbol_and_method_matchers_agree_with_the_operator_inventory(self):
        for operator in OPERATORS.SYMBOL_OPERATORS | set(OPERATORS.BINARY_OPERATORS):
            with self.subTest(operator=operator):
                symbol = any(pattern.fullmatch(":" + operator) for pattern, _ in rules("symbol-token"))
                method = any(pattern.fullmatch(operator) for pattern, _ in rules("function-declaration"))
                self.assertEqual(symbol, operator in OPERATORS.SYMBOL_OPERATORS)
                self.assertEqual(method, operator in OPERATORS.METHOD_OPERATORS)

    def test_both_continuation_matchers_cover_every_binary_and_assignment_operator(self):
        for context, action in [("operators", "push"), ("expression-continuation", "set")]:
            patterns = [pattern for pattern, attributes in rules(context)
                        if attributes.get(action) == "[expression-continuation-start, continuation-operator]"]
            self.assertEqual(len(patterns), 1)
            for operator in set(OPERATORS.BINARY_OPERATORS) | OPERATORS.ASSIGNMENT_OPERATORS:
                for suffix in ["", " ", " # comment"]:
                    with self.subTest(context=context, operator=operator, suffix=suffix):
                        match = patterns[0].match(operator + suffix)
                        self.assertIsNotNone(match)
                        self.assertEqual(match.group(), "")
            for source in ["+ operand", "=>", "->", "::", "&.", "!", "?", "# +"]:
                with self.subTest(context=context, source=source):
                    self.assertIsNone(patterns[0].match(source))

    def test_inventory_covers_every_spelling_in_the_shared_regexes(self):
        candidates = {"".join(chars) for length in range(1, 4)
                      for chars in product("+-*/%<>=!&|.[]~", repeat=length)}
        for variable, expected in [
            ("binary_operator", set(OPERATORS.BINARY_OPERATORS)),
            ("symbol_operator", OPERATORS.SYMBOL_OPERATORS),
            ("continuation_operator", set(OPERATORS.BINARY_OPERATORS) | OPERATORS.ASSIGNMENT_OPERATORS),
        ]:
            with self.subTest(variable=variable):
                pattern = re.compile(expand("{{" + variable + "}}"))
                self.assertEqual({token for token in candidates if pattern.fullmatch(token)}, expected)

    def test_normalizer_recognizes_all_binary_line_endings(self):
        for operator in OPERATORS.BINARY_OPERATORS:
            for suffix in ["", " # comment"]:
                with self.subTest(operator=operator, suffix=suffix):
                    self.assertIsNotNone(OPERATORS.BINARY_LINE_END.search("operand " + operator + suffix))
