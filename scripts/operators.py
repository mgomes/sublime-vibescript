"""Operator expectations and native reindent cases shared by the audit tools."""

import re

BINARY_OPERATORS = {
    "+": ("arithmetic", "9", "2"),
    "-": ("arithmetic", "9", "2"),
    "*": ("arithmetic", "9", "2"),
    "**": ("arithmetic", "9", "2"),
    "/": ("arithmetic", "9", "2"),
    "//": ("arithmetic", "9", "2"),
    "%": ("arithmetic", "9", "2"),
    "==": ("comparison", "9", "2"),
    "===": ("comparison", "9", "2"),
    "!=": ("comparison", "9", "2"),
    "<": ("comparison", "9", "2"),
    "<=": ("comparison", "9", "2"),
    ">": ("comparison", "9", "2"),
    ">=": ("comparison", "9", "2"),
    "<=>": ("comparison", "9", "2"),
    "=~": ("match", '"abc"', "/a/"),
    "!~": ("match", '"abc"', "/a/"),
    "&&": ("logical", "true", "false"),
    "||": ("logical", "true", "false"),
    "<<": ("bitwise", "[1]", "2"),
    "&": ("bitwise", "[1, 2]", "[2, 3]"),
    "..": ("range", "1", "3"),
    "...": ("range", "1", "3"),
}

# Ranges and regex matches have no operator-symbol spelling.
SYMBOL_OPERATORS = set(BINARY_OPERATORS) - {"..", "...", "=~", "!~"} | {"[]", "[]=", "!", "|"}
METHOD_OPERATORS = SYMBOL_OPERATORS - {"===", "&&", "||", "!", "|"}
ASSIGNMENT_OPERATORS = {"=", "+=", "-=", "*=", "/=", "//=", "%=", "**=", "&&=", "||="}
BINARY_LINE_END = re.compile(
    "(?:" + "|".join(re.escape(operator) for operator in sorted(BINARY_OPERATORS, key=len, reverse=True))
    + r")[ \t]*(?:#.*)?$"
)


def continuation_cases():
    cases = []
    for operator, (category, left, right) in BINARY_OPERATORS.items():
        prefix = {"logical": "false ||", "match": '"" +', "bitwise": "[] +"}.get(category, "0 +")
        for existing in (False, True):
            for comment in ("", " # continued"):
                if existing:
                    lines = ["def sample", "  value = (", "    " + prefix + comment,
                             f"      {left} {operator}{comment}", f"        {right}",
                             "  )", "  puts value", "end"]
                    row = 3
                    column = 6 + len(left) + 1
                else:
                    lines = ["def sample", "  value = (", f"    {left} {operator}{comment}",
                             f"      {right}", "  )", "  puts value", "end"]
                    row = 2
                    column = 4 + len(left) + 1
                assertions = [
                    [row, column + offset, f"keyword.operator.{category}"] for offset in range(len(operator))
                ]
                assertions.append([row + 1, len(lines[row + 1]) - len(right), "meta.expression.continuation"])
                assertions.append([len(lines) - 2, 2, "source.vibescript - meta.expression.continuation"])
                cases.append({
                    "name": f"operator:{operator}:existing={existing}:comment={bool(comment)}",
                    "source": "\n".join(lines) + "\n",
                    "assertions": assertions,
                })
    return cases


def scope_cases():
    cases = []
    for operator, (category, left, right) in BINARY_OPERATORS.items():
        column = len("value = " + left + " ")
        cases.append({
            "name": "inline operator:" + operator,
            "source": f"value = {left} {operator} {right}\n",
            "assertions": [[0, column + offset, f"keyword.operator.{category}"]
                           for offset in range(len(operator))],
        })
    for operator in sorted(SYMBOL_OPERATORS):
        cases.append({
            "name": "operator symbol:" + operator,
            "source": f"alias_method :operation, :{operator}\nprivate :{operator}\n",
            "assertions": [[row, column + offset, "constant.other.symbol.operator - keyword.operator"]
                           for row, column in [(0, len("alias_method :operation, ")), (1, len("private "))]
                           for offset in range(len(operator) + 1)],
        })
    for operator in sorted(METHOD_OPERATORS):
        cases.append({
            "name": "operator method:" + operator,
            "source": f"def {operator}(other)\n  other\nend\n",
            "assertions": [[0, 4 + offset, "entity.name.function"] for offset in range(len(operator))],
        })
    return cases


if __name__ == "__main__":
    import argparse
    import json

    from corpus_fixtures import syntax_test

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="store_true", help="emit native reindent cases instead of syntax tests")
    args = parser.parse_args()
    if args.manifest:
        print(json.dumps({"cases": continuation_cases()}, indent=2))
    else:
        print('# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"')
        for case in scope_cases() + continuation_cases():
            print(syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1], end="")
