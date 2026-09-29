"""Generate literal preservation probes with significant, uneven whitespace."""

from corpus_fixtures import syntax_test


DISABLED = {"increaseIndentPattern": "(?!)", "decreaseIndentPattern": "(?!)",
            "indentNextLinePattern": "(?!)", "indentSquareBrackets": False,
            "indentParens": False, "indentCurlyBrackets": False, "preserveIndent": True}


def cases():
    payload = "header\nexamples [\nvalue\n   \n\tkept tab\n  end\n) -> bool\n  tail\n"
    literals = [
        ("double", '"' + payload + '"', "string", "string.quoted.double"),
        ("single", "'" + payload + "'", "string", "string.quoted.single"),
        ("double symbol", ':"' + payload + '"', "symbol", "constant.other.symbol.double-quoted"),
        ("single symbol", ":'" + payload + "'", "symbol", "constant.other.symbol.single-quoted"),
        ("interpolation", '"header\n#{[1,\n     2\n  ].length}\nexamples [\ntail\n"',
         "string", "string.quoted, meta.interpolation"),
        ("nested interpolation string", '"#{begin\n  text = \'examples [\n  nested\n\'\n  text\nend}\ntail"',
         "string", "string.quoted, meta.interpolation"),
    ]
    result = []
    for name, literal, kind, selector in literals:
        for context, before, after in [
            ("top level", "", "\n"),
            ("method", f"def sample -> {kind}\n  ", "\nend\nsample\n"),
            ("default parameter", f"def sample(\n  value: {kind} = ", f"\n) -> {kind}\n  value\nend\nsample()\n"),
            ("array", "values = [", "]\nvalues[0]\n"),
            ("continuation", "value =\n  ", "\nvalue\n"),
            ("followed by code", f"def sample -> {kind}\n  value = ", "\n  value\nend\nsample\n"),
        ]:
            source = before + literal + after
            first_row = before.count("\n")
            rows = range(first_row + 1, first_row + literal.count("\n") + 1)
            assertions, indentation = [], []
            for row in rows:
                line = source.splitlines()[row]
                column = len(line) - len(line.lstrip())
                assertions.append([row, column, selector])
                indentation.append([row, column, DISABLED])
            result.append({"name": f"literal:{name}:{context}", "source": source, "assertions": assertions,
                           "indentation_assertions": indentation, "literal_runtime": True})
    for literal, kind in [('"inline"', "string"), ("'inline'", "string"),
                          ('"#{1}"', "string"), (':"inline"', "symbol"), (":'inline'", "symbol")]:
        result.append({"name": "literal:inline default:" + literal,
                       "source": f"def sample value: {kind} = {literal}\n  value\nend\nsample()\n",
                       "assertions": [[1, 2, "source.vibescript - meta.function.signature - string - variable.parameter"]],
                       "literal_runtime": True})
    for pattern in (r"/examples\[/", r"/(end|else)/", r"/[a-z#]+/i"):
        result.append({"name": "literal:regex:" + pattern, "source": pattern + "\n",
                       "assertions": [[0, 1, "string.regexp"]], "indentation_assertions": [[0, 1, DISABLED]],
                       "literal_runtime": True})
    for quote, kind, selector in [('"', "string", "string.quoted.double"),
                                  ("'", "string", "string.quoted.single"),
                                  (':"', "symbol", "constant.other.symbol.double-quoted"),
                                  (":'", "symbol", "constant.other.symbol.single-quoted")]:
        for suffix, tail in [(" # comment", "  value\nend\nsample\n"), ("; value", "end\nsample\n")]:
            source = (f"def sample -> {kind}\n  value = {quote}first\nexamples [\n  end\n"
                      f"  closing{quote[-1]}{suffix}\n{tail}")
            result.append({"name": f"literal:closing suffix:{quote}:{suffix}", "source": source,
                           "assertions": [[row, 2 if row in (3, 4) else 0, selector] for row in (2, 3, 4)],
                           "indentation_assertions": [[row, 2 if row in (3, 4) else 0, DISABLED]
                                                      for row in (2, 3, 4)],
                           "literal_runtime": True})
    return result


def render():
    header = '# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"\n'
    return header + "".join(syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1]
                            for case in cases())


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"cases": cases()}, indent=2) if args.manifest else render(), end="\n" if args.manifest else "")
