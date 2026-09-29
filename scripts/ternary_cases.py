"""Exercise ternary operands and separators with independent scope expectations."""

from corpus_fixtures import syntax_test


PREFIX = "ready = true\nmodule Codes\n  OK = 1\n  ERROR = 2\nend\n"
QUESTION = ("?", "keyword.operator.ternary")
COLON = (":", "punctuation.separator - constant.other.symbol")


def symbol(text):
    return text, "constant.other.symbol"


def examples():
    result = []

    def add(name, parts):
        source, tokens = "", []
        for part in parts:
            if isinstance(part, tuple):
                token, scope = part
                tokens.append((len(source), token, scope))
                source += token
            else:
                source += part
        result.append((name, source, tokens))

    for left, right in [(":ok", ":error"), (":save!", ":valid?"), (':"ok"', ":'error'"), (":+", ":error")]:
        add("symbols " + left, ["(ready ", QUESTION, " ", symbol(left), " ", COLON, " ", symbol(right), ")"])
    add("nested true", ["(ready ", QUESTION, " ready ", QUESTION, " ", symbol(":inner"), " ", COLON,
                        " ", symbol(":fallback"), " ", COLON, " ", symbol(":outer"), ")"])
    add("nested false", ["(ready ", QUESTION, " ", symbol(":outer"), " ", COLON, " ready ", QUESTION,
                         " ", symbol(":inner"), " ", COLON, " ", symbol(":fallback"), ")"])
    add("grouped branches", ["(ready ", QUESTION, " (ready ", QUESTION, " ", symbol(":one"), " ", COLON,
                             " ", symbol(":two"), ") ", COLON, " (ready ", QUESTION, " ", symbol(":three"),
                             " ", COLON, " ", symbol(":four"), "))"])
    add("binary operands", ["(ready ", QUESTION, " ", symbol(":one"), " == ", symbol(":two"), " ", COLON,
                            " ", symbol(":three"), " != ", symbol(":four"), ")"])
    add("unary operand", ["(ready ", QUESTION, " ![", symbol(":one"), "].empty? ", COLON, " ![", symbol(":two"), "].empty?)"])
    constant = lambda name: [ ("Codes", "support.class"), ("::", "punctuation.accessor.double-colon"), (name, "support.class") ]
    add("qualified constants", ["(ready ", QUESTION, " ", *constant("OK"), " ", COLON, " ", *constant("ERROR"), ")"])
    add("constant and symbol", ["(ready ", QUESTION, " ", *constant("OK"), " ", COLON, " ", symbol(":error"), ")"])
    add("symbol and constant", ["(ready ", QUESTION, " ", symbol(":ok"), " ", COLON, " ", *constant("ERROR"), ")"])
    key = [("next", "constant.other.symbol"), (":", "punctuation.definition.constant")]
    add("hash key after ternary", ["{value: ready ", QUESTION, " ", symbol(":ok"), " ", COLON, " ", symbol(":error"),
                                   ", ", *key, " ", symbol(":next"), "}"])
    add("hash in true branch", ["(ready ", QUESTION, " {", *key, " ", symbol(":ok"), "} ", COLON, " ", symbol(":error"), ")"])
    add("hash in false branch", ["(ready ", QUESTION, " ", symbol(":ok"), " ", COLON, " {", *key, " ", symbol(":error"), "})"])
    return result


def cases():
    result = []
    for name, expression, tokens in examples():
        for comment in ("", " # ternary boundary"):
            source = PREFIX + expression + comment + "\nafter = :after\n"
            assertions = [[PREFIX.count("\n"), offset + i, scope] for offset, token, scope in tokens for i in range(len(token))]
            assertions.append([PREFIX.count("\n") + 1, 8, "constant.other.symbol"])
            result.append({"name": "ternary:" + name + comment, "source": source, "assertions": assertions})
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
