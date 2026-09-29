"""Compiler-checked alias names and uses for native syntax and reindent tests."""

from corpus_fixtures import syntax_test


def cases():
    result = []
    for name in ("id", "Id", "ID", "_id", "_", "id2", "λ", "Λ", "名字", "𝔦𝔡", "id٢", "Idλ", "module", "public", "not"):
        scope = "support.class" if name[0].isascii() and name[0].isupper() else "support.type"
        source = (f"type {name} = int # alias\n"
                  f"value: {name} = 1\n"
                  f"def echo(item: {name}) -> {name}\n"
                  "  item\nend\necho(value)\n")
        result.append({"name": "alias name " + name, "source": source, "assertions": [
            [0, 0, "keyword.declaration.type"], [0, 5, "entity.name.type"],
            [0, 8 + len(name), "meta.annotation.type support.type"],
            [0, 14 + len(name), "comment.line"],
            [1, 0, "variable.other - constant.other.symbol"],
            [1, 7, "meta.annotation.type " + scope],
            [1, 10 + len(name), "constant.numeric - meta.annotation.type"],
            [2, 15, "meta.annotation.type " + scope],
            [2, 20 + len(name), "meta.annotation.type " + scope],
            [3, 2, "source.vibescript - meta.annotation.type"],
        ]})

    def add(name, source, tokens):
        lines = source.splitlines()
        assertions = [[row, lines[row].index(token), scope] for row, token, scope in tokens]
        result.append({"name": name, "source": source, "assertions": assertions})

    add("generic-free aliases with structured right-hand sides", '''type id = int
type ids = array<id>
type record = { id: id, ... }
type pair = [id, string]
type maybe = id | nil
items: ids = [1]
entry: record = { id: 1 }
tuple: pair = [1, "one"]
optional: maybe = nil
''', [(row, name, "entity.name.type") for row, name in enumerate(("id", "ids", "record", "pair", "maybe"))]
         + [(row, name, "meta.annotation.type support.type") for row, name in ((5, "ids"), (6, "record"), (7, "pair"), (8, "maybe"))])
    add("qualified lowercase aliases", '''module Types
  type id = int
end
value: Types::id = 1
''', [(1, "type", "keyword.declaration.type"), (1, "id", "entity.name.type"),
      (3, "value", "variable.other - constant.other.symbol"),
      (3, "Types", "meta.annotation.type support.class"), (3, "id", "meta.annotation.type support.type")])
    add("lowercase aliases in block annotations", '''type id = int
type text = string
values: array<int | string> = [1, "two"]
values.each { |value: id | text| puts value }
def visit(&block: id -> id) -> id
  yield 1
end
''', [(3, "id", "meta.annotation.type support.type"), (3, "text", "meta.annotation.type support.type"),
      (3, "| text", "keyword.operator.union"), (3, "| puts", "punctuation.separator.block-parameters.end"),
      (3, "puts", "source.vibescript - meta.annotation.type - meta.block.parameters"),
      (4, "id", "meta.annotation.type support.type")])
    add("optional alias annotation", '''type id = int
value: id? = nil
''', [(1, "value", "variable.other - constant.other.symbol"), (1, "id", "meta.annotation.type support.type"),
      (1, "?", "keyword.operator.optional"), (1, "nil", "constant.language.null - meta.annotation.type")])
    add("semicolon aliases and trailing comments", '''type id=int; type label=string # aliases
value: id = 1
name: label = "one"
puts name
''', [(0, "id", "entity.name.type"), (0, "int", "meta.annotation.type support.type"),
      (0, "label", "entity.name.type"), (0, "string", "meta.annotation.type support.type"),
      (0, "#", "comment.line"), (1, "value", "variable.other - constant.other.symbol"),
      (2, "name", "variable.other - constant.other.symbol"), (3, "name", "source.vibescript - meta.annotation.type")])
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
