"""Check indentation preferences against literal boundaries and comments."""

from pathlib import Path
import importlib.util
import plistlib
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "preferences/Indentation Rules.tmPreferences").open("rb") as stream:
    SETTINGS = plistlib.load(stream)["settings"]
with (ROOT / "preferences/Indentation Rules - Block Comments.tmPreferences").open("rb") as stream:
    BLOCK_SETTINGS = plistlib.load(stream)["settings"]
SPEC = importlib.util.spec_from_file_location("indentation", ROOT / "scripts/indentation.py")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
SPEC = importlib.util.spec_from_file_location("semicolon_cases", ROOT / "scripts/semicolon_cases.py")
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


class IndentationTests(unittest.TestCase):
    def test_generated_preference_matches_source(self):
        self.assertEqual(SETTINGS["increaseIndentPattern"], GENERATOR.increase_pattern())

    def test_semicolon_nesting_and_inline_closures(self):
        increase = re.compile(SETTINGS["increaseIndentPattern"])
        for case in FIXTURES.semicolon_cases():
            for row, line in enumerate(case["source"].splitlines()):
                with self.subTest(case=case["name"], row=row, line=line):
                    self.assertEqual(bool(increase.search(line)), row in case["increase"])
                    self.assertIsNone(increase.search("# " + line))

    def test_only_code_separators_select_the_bounded_rule(self):
        separator = re.compile(GENERATOR.BEFORE_SEPARATOR)
        for line in [
            'text = "if; end"', "text = 'if; end'", r'text = "escaped\"; end"',
            r"pattern = /[#;]/", r"pattern = /[#/;]/", r"pattern = /a\/;b/",
            "puts 1 # if; end", "# if true; end",
        ]:
            with self.subTest(line=line):
                self.assertIsNone(separator.match(line))
                self.assertIsNotNone(separator.match("count = 1; " + line))
        increase = re.compile(SETTINGS["increaseIndentPattern"])
        self.assertIsNone(increase.match("xs.select { |x| next false if x > 2"))

    def test_inline_blocks_and_multiline_signatures(self):
        pattern = re.compile(SETTINGS["increaseIndentPattern"])
        for line in [
            "a=[1];begin", "result = (begin", "result = if ready",
            ") -> { updated: array<int> }", "def sum(",
            "def f(a: int = (while true; break 1; end)) -> int",
            "items.each { |item: int | string| # union parameter",
        ]:
            with self.subTest(line=line):
                self.assertIsNotNone(pattern.search(line))
        for line in [
            "def literal -> int 42 end", "def literal -> int 42 end # done",
            'concat(begin; "a"; end, "b")', "x = (if true; 1; else; 2; end)",
            "end: 1,", "if: true,", "# ) -> int", "# result = begin",
        ]:
            with self.subTest(line=line):
                self.assertIsNone(pattern.search(line))

    def test_parenthesized_closers(self):
        pattern = re.compile(SETTINGS["decreaseIndentPattern"])
        for line in [")", "  ),", "  ) -> int", "  ) % 7", "  ) # done"]:
            with self.subTest(line=line):
                self.assertIsNotNone(pattern.search(line))

    def test_regex_literals_before_openers(self):
        pattern = re.compile(SETTINGS["increaseIndentPattern"])
        for line in [
            "records[/#/] = [", r"consume(/\d+/) {", r"consume(/a\/#b/) {",
            r"records[/[#/\\]/] = [", "consume(/hash#tag/i) { # body",
            'consume(/"quoted"/) {', "consume(/'quoted'/) {",
        ]:
            with self.subTest(line=line):
                self.assertIsNotNone(pattern.search(line))
        for line in [
            r"consume(/\d+/) # example {", "records[/#/] = [] # [",
            r"# consume(/\d+/) {", r"consume(/\d+{2}/)",
        ]:
            with self.subTest(line=line):
                self.assertIsNone(pattern.search(line))

    def test_nested_literal_closers_deindent(self):
        pattern = re.compile(SETTINGS["decreaseIndentPattern"])
        for line in ["}", "]", "  },", "  ],", "  })", "  ]),", "  ];", "  } # record", "  ].size"]:
            with self.subTest(line=line):
                self.assertIsNotNone(pattern.match(line))

    def test_expressions_and_comments_do_not_deindent(self):
        pattern = re.compile(SETTINGS["decreaseIndentPattern"])
        for line in ['  name: "alex",', "  value = items[0]", "  # }", '  "}"', "  end_value = 1"]:
            with self.subTest(line=line):
                self.assertIsNone(pattern.match(line))

    def test_literal_openers_and_block_boundaries(self):
        increase = re.compile(SETTINGS["increaseIndentPattern"])
        decrease = re.compile(SETTINGS["decreaseIndentPattern"])
        for line in ["items = [", "  {", "consume({", "items = [ # values"]:
            with self.subTest(line=line):
                self.assertIsNotNone(increase.match(line))
        for line in ["end", "  else", "  rescue RuntimeError"]:
            with self.subTest(line=line):
                self.assertIsNotNone(decrease.match(line))

    def test_comment_only_lines_never_change_indentation(self):
        contents = [
            "examples [", "record {", "{ |item|", "}", "],", "})",
            "def example", "export def example", "private def example",
            "class User", "module Models", "enum Status", "if ready", "elsif ready",
            "else", "while ready", "for item in items", "case value", "when 1",
            "begin", "rescue Error", "ensure", "end", "=begin", "=end",
        ]
        for name, expression in SETTINGS.items():
            if not name.endswith("Pattern"):
                continue
            pattern = re.compile(expression)
            for prefix in ["# ", "  # ", "\t# "]:
                for content in contents:
                    line = prefix + content
                    with self.subTest(rule=name, line=line):
                        self.assertIsNone(pattern.search(line))
            for line in ["=begin examples [", "=begin record {", "=end # record {", "=end ["]:
                with self.subTest(rule=name, line=line):
                    self.assertIsNone(pattern.search(line))

    def test_trailing_comments_do_not_open_literals(self):
        pattern = re.compile(SETTINGS["increaseIndentPattern"])
        for line in [
            "value = 1 # examples [", "value = 1 # record {", "value = 1 # { |item|",
            "items = [] # [", "record = {} # {", "value = 1 # if ready",
        ]:
            with self.subTest(line=line):
                self.assertIsNone(pattern.search(line))

    def test_block_comment_text_never_changes_indentation(self):
        for name, expression in BLOCK_SETTINGS.items():
            pattern = re.compile(expression)
            for line in ["=begin examples [", "record {", "if ready", "end", "  },", "=end"]:
                with self.subTest(rule=name, line=line):
                    self.assertIsNone(pattern.search(line))

    def test_code_before_comments_keeps_its_indentation(self):
        increase = re.compile(SETTINGS["increaseIndentPattern"])
        decrease = re.compile(SETTINGS["decreaseIndentPattern"])
        for line in [
            "items = [ # values", "record = { # fields", "items.each { |item| # body",
            'records["#"] = {', "records['#'] = [", 'send("#", {',
            'records["escaped\\\"#"] = {', "records['escaped\\'#'] = [",
            "if ready # condition", "else # fallback", "def example # body",
        ]:
            with self.subTest(line=line):
                self.assertIsNotNone(increase.match(line))
        for line in ["} # record", "], # items", "}) # argument", "end # body", "else # fallback"]:
            with self.subTest(line=line):
                self.assertIsNotNone(decrease.match(line))


if __name__ == "__main__":
    unittest.main()
