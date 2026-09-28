"""Check indentation preferences against nested literal boundaries."""

from pathlib import Path
import plistlib
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "preferences/Indentation Rules.tmPreferences").open("rb") as stream:
    SETTINGS = plistlib.load(stream)["settings"]


class IndentationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
