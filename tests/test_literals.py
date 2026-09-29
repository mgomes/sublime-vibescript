"""Check literal indentation guards and the independent preservation audit."""

import importlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import literal_audit
import literal_cases


class LiteralTests(unittest.TestCase):
    def test_fixture_is_current(self):
        self.assertEqual((ROOT / "tests/syntax_test_literals.vibe").read_text(), literal_cases.render())

    def test_all_literal_contexts_disable_indentation(self):
        preferences = plistlib.loads((ROOT / "preferences/Indentation Rules - Literals.tmPreferences").read_bytes())
        self.assertEqual({key: preferences["settings"][key] for key in literal_cases.DISABLED}, literal_cases.DISABLED)
        for scope in ("string", "meta.interpolation", "constant.other.symbol.double-quoted", "constant.other.symbol.single-quoted"):
            self.assertIn("source.vibescript " + scope, preferences["scope"])
            for name in ("Indentation Rules.tmPreferences", "Indentation Rules - Method Closers.tmPreferences",
                         "Indentation Rules - Continuations.tmPreferences"):
                rule = plistlib.loads((ROOT / "preferences" / name).read_bytes())
                self.assertIn(" - " + scope, rule["scope"])

    def test_regressions_and_rejected_literal_forms_match_rust(self):
        if not (compiler := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check literal syntax")
        for case in literal_cases.cases():
            with self.subTest(case=case["name"]):
                checked = subprocess.run([compiler, "check", "--eval", case["source"]], capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        for source in ("text = <<EOF\nvalue\nEOF\n", "pattern = /first\nsecond/\n"):
            checked = subprocess.run([compiler, "check", "--eval", source], capture_output=True)
            self.assertNotEqual(checked.returncode, 0)

    def parser(self):
        if not (library := os.environ.get("VIBES_TREE_SITTER")):
            self.skipTest("Set VIBES_TREE_SITTER to check the literal audit")
        return literal_audit.parser_for(library)

    def test_literal_comparison_includes_interpolation_and_every_string(self):
        parser = self.parser()
        source = 'text = "prefix #{\'nested\\nvalue\'}\n  tail"\nother = \'one line\'\n'
        literals = literal_audit.literal_bytes(source, parser)
        self.assertEqual(len(literals), 3)
        for before, after in [("  tail", "    tail"), ("nested", "altered"), ("one line", "changed")]:
            self.assertNotEqual(literals, literal_audit.literal_bytes(source.replace(before, after), parser))
        self.assertEqual(literals, literal_audit.literal_bytes("  " + source, parser))

    def test_audit_detects_content_changes_even_when_reindent_expectation_passes(self):
        parser = self.parser()
        if not (compiler := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check preservation failures")
        case = {"name": "canary", "source": '"examples [\nvalue\n"\n', "literal_runtime": True}
        result = {"indent_passed": True, "literal_source": '"examples [\n  value\n"\n'}
        checked = literal_audit.verify_case(case, result, parser, compiler, str(ROOT))
        self.assertFalse(checked["bytes_preserved"])
        self.assertFalse(checked["value_preserved"])
        self.assertTrue(checked["failures"])
        self.assertTrue(literal_audit.verify_case(case, {}, parser, compiler, str(ROOT))["failures"])

    def test_every_multiline_literal_program_is_marked(self):
        parser = self.parser()
        cases = [{"source": source} for source in ('"one line"\n', '"two\nlines"\n', ':"two\nlines"\n')]
        self.assertEqual(literal_audit.mark_cases(cases, parser), 2)
        self.assertFalse(cases[0].get("preserve_literals"))
        self.assertTrue(all(case["preserve_literals"] for case in cases[1:]))

    def test_sampled_program_parse_errors_cannot_silently_skip_the_audit(self):
        parser = self.parser()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.vibe"
            path.write_text('"unterminated\nstring\n')
            with self.assertRaises(ValueError):
                literal_audit.mark_cases([{"path": str(path)}], parser)

    def test_audit_rediscovers_multiline_cases_without_manifest_markers(self):
        if not (compiler := os.environ.get("VIBES")) or not (library := os.environ.get("VIBES_TREE_SITTER")):
            self.skipTest("Set VIBES and VIBES_TREE_SITTER to check audit coverage")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, results, output = (root / name for name in ("manifest.json", "results.json", "audit.json"))
            manifest.write_text(json.dumps({
                "literal_audit": {"vibes": compiler, "library": library, "cwd": str(ROOT)},
                "cases": [{"name": "unmarked", "source": '"first\nsecond"\n'}],
            }) + "\n")
            results.write_text(json.dumps({"cases": [{"name": "unmarked", "indent_passed": True,
                                                       "literal_source": '"first\n  second"\n'}]}) + "\n")
            checked = subprocess.run([sys.executable, str(ROOT / "scripts/literal_audit.py"),
                                      "--manifest", str(manifest), "--results", str(results),
                                      "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(len(report["checks"]), 1)
            self.assertFalse(report["checks"][0]["bytes_preserved"])

    def test_corpus_normalizer_preserves_all_literal_bytes(self):
        parser = self.parser()
        generator = importlib.import_module("generate-corpus-tests")
        for case in literal_cases.cases():
            with self.subTest(case=case["name"]):
                before = case["source"]
                after = generator.normalize_indentation(before, parser)
                self.assertEqual(literal_audit.literal_bytes(before, parser), literal_audit.literal_bytes(after, parser))

    def test_corpus_formatter_cannot_escape_away_multiline_coverage(self):
        parser = self.parser()
        if not (compiler := os.environ.get("VIBES")):
            self.skipTest("Set VIBES to check corpus formatting")
        generator = importlib.import_module("generate-corpus-tests")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "literal.vibe"
            for case in literal_cases.cases():
                with self.subTest(case=case["name"]):
                    before = case["source"]
                    after = generator.format_preserving_literals(before, parser, compiler, path)
                    self.assertEqual(literal_audit.literal_bytes(before, parser), literal_audit.literal_bytes(after, parser))
