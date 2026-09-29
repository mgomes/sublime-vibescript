"""Native scope and reindent cases for the generated type inventory."""

from corpus_fixtures import syntax_test


TYPE = "meta.annotation.type support.type"
EXPRESSION = "source.vibescript - meta.annotation.type"


def cases(types):
    result = []

    def add(name, value, tokens, key="field", multiline=False):
        field = f"{key}: {value}"
        source = (f"schema = {{ # shape\n  {field} # field\n}}\n" if multiline
                  else f"schema = {{ {field} }} # shape\n") + 'puts "after"\n'
        row = 1 if multiline else 0
        line = source.splitlines()[row]
        start = line.index(value, line.index(":") + 1)
        key_scope = "string.quoted" if key[0] in "\"'" else "variable.other.member"
        assertions = [[row, line.index(key), "meta.annotation.type " + key_scope],
                      [len(source.splitlines()) - 1, 6, "string.quoted - meta.annotation.type"]]
        for token, selector in tokens:
            assertions.append([row, start + value.index(token), selector])
        for i, text in enumerate(source.splitlines()):
            if " # " in text:
                assertions.append([i, text.index(" # ") + 2, "comment.line"])
        result.append({"name": name, "source": source, "assertions": assertions})

    for name in types["builtins"]:
        arity = types["generics"].get(name)
        value = name + ("<" + ", ".join(["string"] * arity) + ">" if arity else "")
        # The compiler reads a bare nil field as a hash value, not a shape.
        if name == "nil":
            value = "nil | int"
        selector = "meta.annotation.type constant.language.null" if name == "nil" else TYPE
        for key in ("field", '"quoted field"'):
            for optional in (False, True):
                spelling = value + ("?" if optional else "")
                tokens = [(name, selector)]
                if optional:
                    tokens.append(("?", "keyword.operator.optional"))
                add(f"{name}, key={key}, optional={optional}", spelling, tokens, key, optional)
        for context, source, assertions in [
            ("local", f"local: {value} = value\n", [[0, 0, "variable.other - constant.other.symbol"]]),
            ("block union", f"items.each {{ |item: int | {value}| item }}\n",
             [[0, 24, "keyword.operator.union"],
              [0, len(f"items.each {{ |item: int | {value}"), "punctuation.separator.block-parameters.end"]]),
        ]:
            column = source.rindex(value)
            assertions.append([0, column, selector])
            result.append({"name": context + " type " + name, "source": source, "assertions": assertions})

    for name in types["generics"]:
        add("bare generic " + name, name, [(name, TYPE)])
        value = name + "<" + ", ".join(["string"] * types["generics"][name]) + ">"
        result.append({"name": "generic literal " + name, "source": f"schema = {value}\n",
                       "assertions": [[0, 9, "support.type"], [0, 10 + len(name), TYPE]]})
    for key in ("field?", "Field", "'single key'", r'"escaped\"key"', '"hash#key"'):
        add("field key " + key, "number", [("number", TYPE)], key)
    for value, tokens in [
        ("number | string", [("number", TYPE), ("|", "keyword.operator.union"), ("string", TYPE)]),
        ("array<hash<string, int?>>", [("array", TYPE), ("hash", TYPE), ("int", TYPE)]),
        ("[int, string]", [("int", TYPE), ("string", TYPE)]),
        ("[[int, string], bool]", [("int", TYPE), ("bool", TYPE)]),
        ("() -> int", [("->", "punctuation.separator.annotation.return-type"), ("int", TYPE)]),
        ("(int, string) -> bool", [("int", TYPE), ("string", TYPE), ("bool", TYPE)]),
        ('{ "child": number, ... }', [("number", TYPE), ("...", "keyword.operator.open-shape")]),
        ("{ ... }", [("...", "keyword.operator.open-shape")]),
    ]:
        add("compound " + value, value, tokens, multiline=True)
    result.append({"name": "open shape first", "source": 'schema = { ... } # shape\nputs "after"\n',
                   "assertions": [[0, 11, "meta.annotation.type keyword.operator.open-shape"],
                                  [0, 20, "comment.line"], [1, 6, "string.quoted - meta.annotation.type"]]})

    for value in ["nil", "User", "[User]", "[]", "{}", "(User)", '"text"', "42", "true", ":fast",
                  "numbered", "number()", "number.call", "number[0]", "number + 1", "number..3",
                  "number ? yes : no", "[number, 1]", "{ child: User }", "int, other: lookup()",
                  "int, other: nil", 'int, other: "text"']:
        for key in ("field", '"quoted field"'):
            source = f"opts = {{ {key}: {value} }}\nputs \"after\"\n"
            key_scope = "string.quoted" if key.startswith('"') else "constant.other.symbol"
            result.append({"name": f"expression fallback {key}: {value}", "source": source,
                           "assertions": [[0, source.index(key), key_scope + " - meta.annotation.type"],
                                          [0, source.index(value, source.index(":") + 1), EXPRESSION],
                                          [1, 6, "string.quoted - meta.annotation.type"]]})
    return result


def render(types):
    output = '# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"\n'
    return output + "".join(syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1]
                            for case in cases(types))


if __name__ == "__main__":
    import json
    from type_inventory import inventory
    print(json.dumps({"cases": cases(inventory())}, indent=2))
