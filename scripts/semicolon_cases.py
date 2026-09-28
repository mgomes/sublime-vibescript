"""Generate semicolon-joined nesting cases with independent expected indentation."""

from itertools import product


KINDS = ("if", "while", "def", "block")


def delimiters(kind, level):
    return {
        "if": ("if true", "end"),
        "while": ("while false", "end"),
        "def": (f"def nested_{level} -> int", "end"),
        "block": (f"[1].each {{ |item_{level}|", "}"),
    }[kind]


def closed(kinds, level=0):
    if not kinds:
        return "1"
    start, end = delimiters(kinds[0], level)
    separator = " " if kinds[0] == "block" else "; "
    return f"{start}{separator}{closed(kinds[1:], level + 1)}; 1; {end}"


def semicolon_cases():
    cases = []
    for depth in range(1, 4):
        for kinds in product(KINDS, repeat=depth):
            for prefix in ("", "count = 1; "):
                for comment in ("", " # if; end; ["):
                    for opened in (False, True):
                        if opened:
                            start, end = delimiters(kinds[0], 0)
                            separator = " " if kinds[0] == "block" else "; "
                            line = f"{prefix}{start}{separator}{closed(kinds[1:], 1)};{comment}"
                            source = f"{line}\n  1\n{end}\nputs 1\n"
                            assertions = [[1, 2, "constant.numeric"]]
                        else:
                            line = prefix + closed(kinds) + comment
                            source = line + "\nputs 1\n"
                            assertions = [[1, 5, "constant.numeric"]]
                        cases.append({
                            "name": f"semicolons:{'/'.join(kinds)}:prefix={bool(prefix)}:comment={bool(comment)}:open={opened}",
                            "source": source,
                            "assertions": assertions,
                            "increase": [0] if opened else [],
                        })
    for name, line in [
        ("empty inner", "if true; if false; end"),
        ("statement after closure", "if true; if false; end; puts 1"),
        ("sibling closures", "if true; if true; end; while false; end"),
        ("closed prefix", "if true; end; if true; if false; end"),
        ("postfix condition", "if true; puts 1 if true; if false; end"),
        ("postfix loop", "if true; puts 1 while false; if false; end"),
        ("double-quoted delimiters", 'if true; text = "if; end; [{"; if true; end'),
        ("single-quoted delimiters", "if true; text = 'if; end; [{'; if true; end"),
        ("regex delimiters", r"if true; pattern = /end; if; [#{}]/; if true; end"),
        ("symbol delimiter", "if true; marker = :end; if true; end"),
        ("keyword labels", "if true; record = {end: 1, if: 2}; if true; end"),
    ]:
        cases.append({"name": "semicolons:" + name, "source": line + "\n  1\nend\nputs 1\n",
                      "assertions": [[1, 2, "constant.numeric"]], "increase": [0]})
    cases.append({
        "name": "semicolons:close previous and reopen",
        "source": "if true\n  1\nend; if true; if false; end\n  1\nend\nputs 1\n",
        "assertions": [[3, 2, "constant.numeric"]], "increase": [0, 2],
    })
    return cases


if __name__ == "__main__":
    import json

    print(json.dumps({"cases": semicolon_cases()}, indent=2))
