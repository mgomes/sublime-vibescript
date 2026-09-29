"""Compare complete token scope stacks across inline and continued layouts."""

from pathlib import Path
import re

from operators import ASSIGNMENT_OPERATORS, BINARY_OPERATORS, METHOD_OPERATORS, SYMBOL_OPERATORS
from ternary_cases import examples as ternary_examples, PREFIX as TERNARY_PREFIX


def required_scopes():
    syntax = (Path(__file__).resolve().parent.parent / "Vibescript.sublime-syntax").read_text()
    return sorted(set(re.findall(r"\b(?:keyword|punctuation|constant|string)\.[\w.]+\.vibescript\b", syntax)))


def inventory():
    tokens = []

    def add(name, before, token, after, scope, *, unit=None, breaks=True):
        tokens.append(dict(name=name, before=before, token=token, after=after,
                           scope=scope, unit=unit or token, breaks=breaks))

    for operator, (category, left, right) in BINARY_OPERATORS.items():
        add("binary " + operator, f"value = ({left} ", operator, f" {right})\n", "keyword.operator." + category)
    for operator in sorted(ASSIGNMENT_OPERATORS):
        category = "assignment" if operator == "=" else "assignment.augmented"
        add("assignment " + operator, "value = 1\n(value ", operator, " 2)\n", "keyword.operator." + category)
    for operator in sorted(SYMBOL_OPERATORS):
        add("symbol " + operator, "private ", ":" + operator, "\n", "constant.other.symbol.operator")
    for operator in sorted(METHOD_OPERATORS):
        add("method " + operator, "def ", operator, "(other)\n  other\nend\n", "entity.name.function")

    for words, category in [
        ("if elsif else case when then", "conditional"), ("while for in", "loop"),
        ("begin rescue ensure", "exception"), ("return yield raise break next retry", "flow"),
        ("end", "block"), ("require", "import"),
    ]:
        for word in words.split():
            add("keyword " + word, "(", word, " 1)\n", "keyword.control." + category)
    for word, rest, category in [
        ("def", " sample\nend", "function"), ("class", " Sample\nend", "class"),
        ("module", " Sample\nend", "module"), ("enum", " Sample\nValue\nend", "enum"),
        ("export", " def sample\nend", "export"),
        ("private", " def sample\nend", "visibility"),
        ("public", " def sample\nend", "visibility"),
        ("protected", " def sample\nend", "visibility"),
        ("property", " sample: int", "member"), ("getter", " sample: int", "member"),
        ("setter", " sample: int", "member"),
        ("alias", " old_name new_name", "alias"), ("alias_method", " :old_name, :new_name", "alias"),
    ]:
        unit = {"module": "module Sample", "alias": "alias old_name new_name"}.get(word)
        add("keyword " + word, "", word, rest + "\n", "keyword.declaration." + category, unit=unit)
    add("keyword type", "", "type", " Id = int\n", "keyword.declaration.type", unit="type Id =")

    for literal, scope in [
        ("true", "constant.language.boolean"), ("false", "constant.language.boolean"),
        ("nil", "constant.language.null"), ("self", "variable.language.self"),
        ("42", "constant.numeric.integer"), ("1_024", "constant.numeric.integer"),
        ("0xAf", "constant.numeric.integer.hexadecimal"), ("0b10", "constant.numeric.integer.binary"),
        ("0o17", "constant.numeric.integer.octal"), ("0d12", "constant.numeric.integer.decimal"),
        ("1.25", "constant.numeric.float"), ("1.2e-3", "constant.numeric.float"), ("1e3", "constant.numeric.float"),
        (":name?", "constant.other.symbol"), (':"quoted"', "constant.other.symbol.double-quoted"),
        (":'quoted'", "constant.other.symbol.single-quoted"),
        ('"text"', "string.quoted.double"), ("'text'", "string.quoted.single"),
        (r'"\n\x41\u0042\#"', "string.quoted.double"), (r"'don\'t\\'", "string.quoted.single"),
        ('"#{1 + 2}"', "string.quoted.double"), (r"/a[\d#]+/im", "string.regexp"),
    ]:
        add("literal " + literal, "value = (", literal, ")\n", scope)

    for name, before, token, after, scope in [
        ("not", "value = (", "!", "true)\n", "keyword.operator.logical"),
        ("ternary", "value = (true ", "?", " 1 : 2)\n", "keyword.operator.ternary"),
        ("rescue binding", "begin; rescue Error ", "=>", " error; end\n", "keyword.operator.rescue-binding"),
        ("arrow", "(", "->", " int)\n", "keyword.operator.arrow"),
        ("namespace", "value = (Module", "::", "Value)\n", "punctuation.accessor.double-colon"),
        ("member", "value = (object", ".", "method)\n", "punctuation.accessor.dot"),
        ("safe member", "value = (object", "&.", "method)\n", "punctuation.accessor.safe-navigation"),
        ("union", "type Id = [int ", "|", " string]\n", "keyword.operator.union"),
        ("optional", "type Id = [int", "?", "]\n", "keyword.operator.optional"),
        ("open shape", "type Id = {a: int, ", "...", "}\n", "keyword.operator.open-shape"),
        ("type arrow", "def f(&block: (int) ", "->", " int)\nend\n", "punctuation.separator.annotation.return-type"),
        ("return arrow", "def f(value: int) ", "->", " int\n  1\nend\n", "punctuation.separator.annotation.return-type"),
        ("type accessor", "type Id = [Module", "::", "Id]\n", "punctuation.accessor"),
        ("type dot", "type Id = [Module", ".", "Id]\n", "punctuation.accessor"),
        ("parameter comma", "def f(a: int", ",", " b: int)\nend\n", "punctuation.separator.parameter"),
        ("annotation", "def f(a", ":", " int)\nend\n", "punctuation.separator.annotation.type"),
        ("tuple comma", "type Id = [int", ",", " string]\n", "punctuation.separator.sequence"),
        ("field colon", "value = {name", ":", " 1}\n", "punctuation.definition.constant"),
        ("comma", "value = [1", ",", " 2]\n", "punctuation.separator"),
        ("ternary colon", "value = (true ? 1 ", ":", " 2)\n", "punctuation.separator"),
        ("named ternary colon", "value = (true ? left", ":", " right)\n", "punctuation.separator"),
        ("pipe begin", "[1].each { ", "|", "item| item }\n", "punctuation.separator.block-parameters.begin"),
        ("pipe end", "[1].each { |item", "|", " item }\n", "punctuation.separator.block-parameters.end"),
        ("block comma", "[1].each { |a", ",", " b| a }\n", "punctuation.separator.parameter"),
        ("pipe separator", "(", "|", ")\n", "punctuation.separator"),
    ]:
        unit = {"return arrow": ") ->"}.get(name)
        add(name, before, token, after, scope, unit=unit)
    for operator in ("*", "**", "&"):
        add("parameter " + operator, "def f(", operator, "items: any)\nend\n", "keyword.operator.parameter")

    for name, opening, closing, prefix, body, suffix, begin_scope, end_scope in [
        ("group", "(", ")", "value = ", "1", "\n", "punctuation.section.brackets", "punctuation.section.brackets"),
        ("array", "[", "]", "value = ", "1", "\n", "punctuation.section.brackets", "punctuation.section.brackets"),
        ("hash", "{", "}", "value = ", "a: 1", "\n", "punctuation.section.brackets", "punctuation.section.brackets"),
        ("parameters", "(", ")", "def f", "value: int", "\nend\n", "punctuation.section.group.begin", "punctuation.section.group.end"),
        ("function type", "(", ")", "def f(&block: ", "int", " -> int)\nend\n", "punctuation.section.group.begin", "punctuation.section.group.end"),
        ("type tuple", "[", "]", "type Id = ", "int", "\n", "punctuation.section.brackets.begin", "punctuation.section.brackets.end"),
        ("type shape", "{", "}", "type Id = ", "a: int", "\n", "punctuation.section.braces.begin", "punctuation.section.braces.end"),
        ("generic", "<", ">", "type Id = array", "int", "\n", "punctuation.section.generic.begin", "punctuation.section.generic.end"),
    ]:
        unit = {"parameters": "def f(", "function type": "&block: ("}.get(name)
        add(name + " begin", prefix, opening, body + closing + suffix, begin_scope, unit=unit)
        add(name + " end", prefix + opening + body, closing, suffix, end_scope)

    # These lexical units cannot be split without changing their language role.
    for name, unit, token, scope in [
        ("double quote begin", '"text"', '"', "punctuation.definition.string.begin"),
        ("single quote begin", "'text'", "'", "punctuation.definition.string.begin"),
        ("escape", r'"\n"', r"\n", "constant.character.escape"),
        ("regex flag", "/a/i", "i", "keyword.other.flag"),
        ("interpolation begin", '"#{1}"', "#{", "punctuation.section.interpolation.begin"),
        ("interpolation end", '"#{1}"', "}", "punctuation.section.interpolation.end"),
        ("interpolation brace begin", '"#{{a: 1}}"', "{a", "punctuation.section.braces.begin"),
        ("interpolation brace end", '"#{{a: 1}}"', "}}", "punctuation.section.braces.end"),
    ]:
        offset = unit.index(token)
        add(name, "value = (" + unit[:offset], token, unit[offset + len(token):] + ")\n", scope, unit=unit)
    for directive in ("vibe", "uses"):
        add("directive " + directive, "# ", directive, ": " + ("0.80" if directive == "vibe" else "time") + "\n",
            "keyword.other.directive", breaks=False)
    add("directive colon", "# vibe", ":", " 0.80\n", "punctuation.separator.key-value", breaks=False)
    add("directive version", "# vibe: ", "0.80", "\n", "constant.numeric.version", breaks=False)
    add("comment marker", "1 ", "#", " comment\n", "punctuation.definition.comment")
    add("enum value", "enum Color\n", "Red", "\nend\n", "constant.other.enum")
    for name, source, marked_tokens in ternary_examples():
        for index, (offset, token, scope) in enumerate(marked_tokens):
            add(f"ternary {name} token {index}", TERNARY_PREFIX + source[:offset], token,
                source[offset + len(token):] + "\n", scope)
    return tokens


def cases():
    result = []
    for item in inventory():
        before, token, after = item["before"], item["token"], item["after"]
        fragment = before + token + after
        token_offset = len(before)
        unit_start = fragment.index(item["unit"], max(0, token_offset - len(item["unit"])))
        unit_end = unit_start + len(item["unit"])
        variants = [("inline", fragment, token_offset)]
        if item["breaks"]:
            leading = fragment[:unit_start].rstrip(" \t")
            variants += [
                ("trailing", fragment[:unit_end] + "\n" + fragment[unit_end:], token_offset),
                ("trailing-comment", fragment[:unit_end] + " # continued\n" + fragment[unit_end:], token_offset),
                ("leading", leading + "\n" + fragment[unit_start:], token_offset + 1 - unit_start + len(leading)),
            ]
        else:
            variants += [("trailing", fragment, token_offset), ("leading", "\n" + fragment, token_offset + 1)]
        variants += [("continued-" + name, "0 +\n" + source, offset + 4) for name, source, offset in variants[:]]
        if item["name"].startswith(("binary ", "assignment ")):
            opening = before.rindex("(") + 1
            for name, text, offset in variants[:4]:
                variants.append(("extended-" + name, text[:opening] + "0 +\n" + text[opening:], offset + 4))
        source, locations, assertions = "", [], []
        for layout, text, offset in variants:
            row = source.count("\n") + text[:offset].count("\n")
            column = len(text[:offset].rsplit("\n", 1)[-1])
            locations.append({"layout": layout, "position": [row, column]})
            assertions.append([row, column, item["scope"]])
            source += text + "\n"
        result.append({"name": "layout:" + item["name"], "source": source, "reindent": False,
                       "assertions": assertions, "equal_scopes": [{"token": token, "locations": locations}]})
    return result


def render():
    from corpus_fixtures import syntax_test
    header = '# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"\n'
    return (header + "".join(syntax_test(case["source"], case["assertions"], case["name"]).split("\n", 1)[1]
                             for case in cases())).rstrip() + "\n"


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--syntax", action="store_true")
    args = parser.parse_args()
    print(render() if args.syntax else json.dumps({"cases": cases(), "required_scopes": required_scopes()}, indent=2),
          end="" if args.syntax else "\n")
