"""Check argument scopes across call spacing, including incomplete newline calls."""

from corpus_fixtures import syntax_test


TYPE_CALLS = {"T.as": [0], "JSON.parse_as": [1]}
GAPS = {"inline": "", "space": " ", "tab": "\t", "newline": "\n", "comment": " # call boundary\n"}
PREFIX = '''type Status = int
number = 1
value = JSON.parse("1")
def identity(item: any) -> any
  item
end
module Other
  def self.parse_as(text: string, schema: any) -> any
    text
  end
end
class Example
  def as?(item: int) -> int
    item
  end
end
example = Example.new
'''


def specifications():
    result = []
    for type_name in ("int", "Status", "array<int>", "[int, string]", '{ "field": int }'):
        result.append(("as " + type_name, "value.as", [(type_name, "meta.annotation.type")], True, False))
        result.append(("JSON.parse_as " + type_name, "JSON.parse_as",
                       [('"1"', "string.quoted - meta.annotation.type"), ", ", (type_name, "meta.annotation.type")], True, False))
    result.append(("JSON.parse_as nested first argument", "JSON.parse_as",
                   ['JSON.stringify([1, 2])', ", ", ("array<int>", "meta.annotation.type")], True, False))
    result.append(("safe as", "value&.as", [("Status", "meta.annotation.type")], True, False))
    result.append(("safe JSON.parse_as", "JSON&.parse_as",
                   [('"1"', "string.quoted - meta.annotation.type"), ", ", ("Status", "meta.annotation.type")], True, False))
    for name, argument, scope, bare in [
        ("number.is_type?", ":int", "constant.other.symbol - meta.annotation.type", False),
        ("identity", "1", "constant.numeric - meta.annotation.type", True),
        ("JSON.stringify", "1", "constant.numeric - meta.annotation.type", False),
        ("[1].include?", "1", "constant.numeric - meta.annotation.type", False),
        ("example.as?", "1", "constant.numeric - meta.annotation.type", False),
    ]:
        result.append((name, name, [(argument, scope)], False, bare))
    result.append(("Other.parse_as", "Other.parse_as",
                   [('"1"', "string.quoted - meta.annotation.type"), ", ", ("Status", "support.class - meta.annotation.type")], False, False))
    return result


def variants(specification):
    name, callee, arguments, typed, bare = specification
    result = []
    for layout, gap in GAPS.items():
        source = PREFIX + callee
        method = callee.rsplit(".", 1)[-1]
        method_scope = "source.vibescript - variable.function" if bare and "\n" in gap else "variable.function"
        marks = [(len(source) - len(method), method, method_scope, not bare)]
        source += gap
        opening_scope = "punctuation.section.group.begin" if typed else "punctuation.section.brackets"
        closing_scope = "punctuation.section.group.end" if typed else "punctuation.section.brackets"
        for part in [("(", opening_scope), *arguments, (")", closing_scope)]:
            if isinstance(part, tuple):
                token, scope = part
                marks.append((len(source), token, scope, True))
                source += token
            else:
                source += part
        source += "\nafter = :after\n"
        assertions = []
        locations = []
        for offset, token, scope, compare in marks:
            row, column = source[:offset].count("\n"), len(source[:offset].rsplit("\n", 1)[-1])
            assertions.append([row, column, scope])
            locations.append((token, [row, column], compare))
        assertions.append([source.count("\n") - 1, 8, "constant.other.symbol - meta.annotation.type"])
        result.append({"name": f"call:{name}:{layout}", "source": source, "assertions": assertions,
                       "reindent": layout in ("inline", "space"), "compiler_accepted": "\n" not in gap,
                       "locations": locations, "layout": layout})
    return result


def cases():
    return [{key: value for key, value in case.items() if key not in ("locations", "layout")}
            for specification in specifications() for case in variants(specification)]


def layouts():
    result = []
    for specification in specifications():
        source, assertions, groups = "", [], []
        for case in variants(specification):
            shift = source.count("\n")
            assertions.extend([row + shift, column, scope] for row, column, scope in case["assertions"])
            if not groups:
                groups = [{"token": token, "locations": []} if compare else None for token, _, compare in case["locations"]]
            for group, (_, (row, column), _) in zip(groups, case["locations"]):
                if group is not None:
                    group["locations"].append({"layout": case["layout"], "position": [row + shift, column]})
            source += case["source"] + "\n"
        result.append({"name": "layout:call " + specification[0], "source": source, "assertions": assertions,
                       "reindent": False, "layout_kind": "call-spacing", "equal_scopes": [group for group in groups if group]})
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
