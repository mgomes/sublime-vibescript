"""Generate nested scope and reindent cases independently of indentation rules."""

from itertools import product
import re

from corpus_fixtures import syntax_test


def nested_type(kinds):
    if not kinds:
        return ["int"]
    child = nested_type(kinds[1:])
    if kinds[0] == "tuple":
        return ["[", "  int,"] + ["  " + line for line in child] + ["]"]
    return ["{", "  child: " + child[0]] + ["  " + line for line in child[1:]] + ["}"]


def cases():
    result = []

    def add(name, lines, signature_closers=(), type_rows=()):
        for comments in (False, True):
            source = [line + (" # nested boundary" if comments else "") for line in lines]
            assertions = []
            for row, line in enumerate(lines):
                column = len(line) - len(line.lstrip())
                if line.lstrip().startswith((")", "]", "}")):
                    selector = "meta.function.signature - meta.group.parameters - meta.annotation.type"
                    assertions.append([row, len(source[row]), selector if row in signature_closers else
                                       "source.vibescript - (meta.function.signature - meta.group.parameters - meta.annotation.type)"])
                if row in type_rows:
                    for match in re.finditer(r"\bint\b", line):
                        assertions.append([row, match.start(), "meta.annotation.type support.type"])
                if line.lstrip() == "1":
                    assertions.append([row, column, "constant.numeric - meta.annotation.type"])
                if line.lstrip().startswith("raise "):
                    assertions.append([row, column, "keyword.control.flow - meta.annotation.type - meta.function.signature"])
                    assertions.append([row, line.index('"'), "string.quoted - meta.annotation.type"])
                if comments:
                    assertions.append([row, len(line) + 1, "comment.line"])
            result.append({"name": f"nested:{name}:comments={comments}", "source": "\n".join(source) + "\n",
                           "assertions": assertions})

    for arrow in ("", " -> int"):
        lines = ["def apply(", "  &block: (", "    int", "  ) -> int", ")" + arrow, "  1", "end"]
        add("function parameter outer arrow=" + str(bool(arrow)), lines, [4], [2, 3, 4])

    kinds = list(product(("tuple", "shape"), repeat=2))
    kinds += [("tuple", "shape", "tuple"), ("shape", "tuple", "shape")]
    for nesting in kinds:
        value = nested_type(nesting)
        for where in ("block parameter", "return"):
            if where == "block parameter":
                lines = ["def apply(", "  &block: ("] + ["    " + line for line in value]
                lines += ["  ) -> int", ") -> int", "  1", "end"]
                closer = len(lines) - 3
            else:
                lines = ["def apply(", "  &block: (", "    int", "  ) -> int", ") -> " + value[0]]
                lines += value[1:] + ['  raise "unused"', "end"]
                closer = len(lines) - 3
            for wrapped in (False, True):
                source = (["module Nested", "  def self.apply("] + ["  " + line for line in lines[1:]] + ["end"]
                          if wrapped else lines)
                shift = int(wrapped)
                add(f'{where}:{"/".join(nesting)}:module={wrapped}', source, [closer + shift],
                    range(shift + 1, shift + closer + 1))

    for depth in (2, 3):
        expression = ["(", "  1", ")"]
        for level in range(depth):
            expression = [f"[1].map {{ |item_{level}|"] + ["  " + line for line in expression] + ["}"]
            expression = ["identity("] + ["  " + line for line in expression] + [")"]
        prelude = ["def identity(value: any) -> any", "  value", "end"]
        add(f"call arguments with blocks:depth={depth}", prelude + expression)
        lines = prelude + ["def apply(", "  value: any = " + expression[0]]
        lines += ["  " + line for line in expression[1:]] + [") -> int", "  1", "end"]
        add(f"parameter default calls with blocks:depth={depth}", lines, [len(lines) - 3])
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
