#!/usr/bin/env python3
"""Generate scope and reindent fixtures from compiler-accepted real programs."""

import argparse
from collections import Counter, defaultdict
import ctypes
import hashlib
import json
from pathlib import Path
import re
import subprocess

from tree_sitter import Language, Parser

from corpus_fixtures import syntax_test
from operators import BINARY_LINE_END, continuation_cases


BUILTINS = set("any array bool comparable duration enum_type enum_value error float hash int match_data money number range regex string symbol time type nil".split())
TYPE_NODES = {"type_annotation", "type_alias", "block_type", "return_type", "type_literal"}
PARAMETERS = {"typed_parameter", "splat_parameter", "double_splat_parameter", "block_parameter"}
CONTEXTS = {"method", "class", "module", "enum", "type_alias", "typed_assignment",
            "type_arguments", "type_tuple", "type_shape", "block_type", "parameters",
            "typed_parameter", "block", "block_parameters", "string", "regex",
            "property", "getter", "setter", "alias", "interpolation", "call",
            "computed_call", "array", "hash", "parenthesized", "return_type"}


def language(library):
    handle = ctypes.CDLL(str(library.resolve()))
    handle.tree_sitter_vibescript.restype = ctypes.c_void_p
    capsule = ctypes.pythonapi.PyCapsule_New
    capsule.restype = ctypes.py_object
    capsule.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]
    return Language(capsule(handle.tree_sitter_vibescript(), b"tree_sitter.Language", None))


def walk(node, ancestors=()):
    yield node, ancestors
    for child in node.children:
        yield from walk(child, (*ancestors, node))


def normalize_indentation(source, parser):
    """Indent embedded fixtures from their syntax tree, independently of Sublime."""
    tree = parser.parse(source.encode())
    lines = source.splitlines()
    levels = [set() for _ in lines]
    brackets = defaultdict(list)
    continuations = {}
    branches = []
    protected = set()
    blocks = {"class", "module", "enum", "if", "while", "for", "case", "begin", "block"}
    containers = {"parameters", "argument_list", "array", "hash", "parenthesized",
                  "type_arguments", "type_tuple", "type_shape", "block_type"}
    for node, ancestors in walk(tree.root_node):
        if not node.is_named:
            continue
        start, end = node.start_point.row, node.end_point.row
        if node.type == "string" and start != end:
            protected.update(range(start + 1, end + 1))
        if node.type == "block_comment":
            protected.update(range(start, end + 1))
        if node.type == "method":
            signature_end = max((child.end_point.row for child in node.named_children
                                 if child.type in ("parameters", "bare_parameters", "return_type")), default=start)
            for row in range(signature_end + 1, end):
                levels[row].add(start)
        elif node.type in blocks:
            for row in range(start + 1, end):
                levels[row].add(start)
        elif node.type in ("else", "elsif", "when", "rescue", "ensure"):
            owner = next((parent for parent in reversed(ancestors) if parent.type in blocks or parent.type == "method"), None)
            if owner:
                branches.append((start, owner.start_point.row))
        elif node.type in containers and start != end:
            brackets[start].append(end)
        elif node.type == "binary" and start != end and not (ancestors and ancestors[-1].type == "binary"):
            first = node
            while first.type == "binary":
                first = first.named_children[0]
            if BINARY_LINE_END.search(lines[first.end_point.row]):
                continuations[first.end_point.row] = end
    for start, ends in brackets.items():
        for row in range(start + 1, max(ends) + 1):
            if row not in ends or not re.match(r'\s*(?:[\])}>]|end\b)', lines[row]):
                levels[row].add(start)
    for row, owner in branches:
        levels[row].discard(owner)
    for start, end in continuations.items():
        for row in range(start + 1, end + 1):
            levels[row].add(("continuation", start))
    return "\n".join(line if row in protected else "  " * len(levels[row]) + line.lstrip() if line.strip() else ""
                     for row, line in enumerate(lines)) + "\n"


def expectations(source, parser):
    data = source.encode()
    tree = parser.parse(data)
    if tree.root_node.has_error:
        raise ValueError("Tree-sitter could not parse the fixture")
    lines = source.splitlines()
    assertions = set()
    features = Counter()
    comment_rows = set()
    context_rows = set()
    multiline_string_rows = set()

    def schema(entry):
        container = entry.parent
        values = [child.child_by_field_name("value") for child in container.named_children if child.type == "hash_entry"]
        return bool(values) and all(value and (value.type in ("type_annotation", "type_literal") or value.text.decode() in BUILTINS - {"nil"}) for value in values)

    def add(node, selector, category, offset=0):
        row, byte_column = node.start_point
        column = len(lines[row].encode()[:byte_column + offset].decode())
        assertions.add((row, column, selector))
        features[category] += 1

    for node, ancestors in walk(tree.root_node):
        kinds = {parent.type for parent in ancestors}
        parent = ancestors[-1] if ancestors else None
        call = next((ancestor for ancestor in reversed(ancestors) if ancestor.type == "call"), None)
        text = data[node.start_byte:node.end_byte].decode()
        if node.type in CONTEXTS:
            context_rows.add(node.start_point.row)
            features["context:" + node.type] += 1
        if node.type in ("string", "regex") and node.start_point.row != node.end_point.row:
            multiline_string_rows.update(range(node.start_point.row, node.end_point.row))
        if node.type in ("comment", "directive_comment", "block_comment"):
            comment_rows.update(range(node.start_point.row, node.end_point.row + 1))
            add(node, "comment", "comment")
            features["context:" + node.type] += 1
        elif node.type == "string_content" and "string" in kinds:
            string = next(ancestor for ancestor in reversed(ancestors) if ancestor.type == "string")
            quote = "single" if data[string.start_byte:string.start_byte + 1] == b"'" else "double"
            add(node, "string.quoted." + quote, "string")
        elif node.type == "regex" and len(text) > 2:
            add(node, "string.regexp - comment", "regex", 1)
            for marker in re.finditer(rb'[#\\]', node.text):
                add(node, "string.regexp - comment", "regex", marker.start())
        elif node.type == "typed_assignment":
            add(node.child_by_field_name("name"), "variable.other - constant.other.symbol", "typed-local")
        elif node.type in PARAMETERS:
            add(node.child_by_field_name("name"), "variable.parameter", "parameter")
        elif parent and parent.type in ("block_parameters", "destructured_parameter") and node.type in ("identifier", "constant"):
            add(node, "variable.parameter", "block-parameter")
        elif node.type == "|" and parent and parent.type == "block_parameters":
            delimiter = "begin" if node == parent.children[0] else "end"
            add(node, "punctuation.separator.block-parameters." + delimiter, "block-delimiter")
        elif parent and parent.type in ("hash_entry", "keyword_argument") and node == parent.child_by_field_name("key") and node.type in ("identifier", "constant"):
            # Expression-position schemas are ambiguous in the concrete tree.
            is_schema = parent.type == "hash_entry" and schema(parent)
            if not is_schema:
                add(node, "constant.other.symbol - meta.annotation.type", "hash-key")
        elif parent and parent.type == "type_name" and node.type in ("identifier", "constant", "nil") and TYPE_NODES.intersection(kinds):
            scope = "constant.language.null" if text == "nil" else "support.class" if node.type == "constant" else "support.type"
            add(node, "meta.annotation.type " + scope, "type")
        elif node.type == "|" and TYPE_NODES.intersection(kinds):
            add(node, "keyword.operator.union", "union")
            if "block_parameters" in kinds:
                features["block-union"] += 1
        elif node.type == "?" and TYPE_NODES.intersection(kinds):
            add(node, "keyword.operator.optional", "optional")
        elif node.type == "identifier" and parent and parent.type == "hash_entry" and text in BUILTINS and node == parent.child_by_field_name("value") and schema(parent):
            add(node, "meta.annotation.type support.type", "type")
        elif node.type == "identifier" and call and call.child_by_field_name("method") and call.child_by_field_name("method").text == b"as":
            if text != "as" and parent and parent.type == "argument_list":
                add(node, "meta.annotation.type support.type", "type")
        elif node.type == "identifier" and not TYPE_NODES.intersection(kinds) and not {"typed_assignment", "parameters", "bare_parameters", "block_parameters", "destructured_parameter", "string", "symbol", "quoted_symbol", "regex"}.intersection(kinds):
            add(node, "source.vibescript - meta.annotation.type - meta.block.parameters - string - comment", "expression")
    return sorted(assertions), features, sorted(context_rows - comment_rows - multiline_string_rows)



def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--rust-repo", type=Path, required=True)
    cli.add_argument("--accepted-manifest", type=Path, required=True)
    cli.add_argument("--website", type=Path, required=True)
    cli.add_argument("--library", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--rust-limit", type=int, default=300)
    args = cli.parse_args()
    output = args.output.resolve()
    (output / "sources").mkdir(parents=True, exist_ok=True)
    (output / "syntax").mkdir(exist_ok=True)
    parser = Parser(language(args.library))
    compiler = args.rust_repo / "target/gate/vibes"
    entries = json.loads(args.accepted_manifest.read_text())
    entries.sort(key=lambda entry: hashlib.sha256(entry["origin"].encode() + Path(entry["path"]).name.encode()).digest())
    selected = []
    origins = Counter()
    union_samples = 0
    block_comments = 0
    for entry in entries:
        group = entry["origin"].split(":", 1)[0]
        source = Path(entry["path"]).read_text()
        comment_sample = block_comments < 4 and re.search(r'^=begin\b', source, re.MULTILINE)
        if (len(source) < 40 and not comment_sample) or len(source) > 6000 or source.count("\n") < 2:
            continue
        targeted = union_samples < 8 and re.search(r'\{\s*\|[^|\n]*:[^|\n]*\|[^|\n]+\|', source)
        if targeted:
            _, features, _ = expectations(source, parser)
            targeted = features["block-union"] > 0
        union_samples += bool(targeted)
        block_comments += bool(comment_sample)
        targeted = targeted or comment_sample
        if not targeted and origins[group] >= (4 if group.endswith((".rs", ".json", ".gz", ".jsonl")) else 1):
            continue
        if not targeted and len(selected) >= args.rust_limit and not group.startswith(("examples/", "corpus/glue/")):
            continue
        origins[group] += 1
        selected.append(("rust:" + entry["origin"], source, args.rust_repo / Path(group).parent))
    website = sorted(args.website.rglob("*.vibe"))
    selected.extend(("site:" + str(path.relative_to(args.website)), path.read_text(), path.parent) for path in website)
    cases = []
    coverage = Counter()
    rejected = []
    for index, (origin, source, cwd) in enumerate(selected):
        checked = subprocess.run([str(compiler), "check", "--eval", source], cwd=cwd, capture_output=True, text=True)
        if checked.returncode:
            rejected.append({"origin": origin, "diagnostics": checked.stdout + checked.stderr})
            if origin.startswith("rust:"):
                continue
        path = output / "sources" / f"{index:04}.vibe"
        path.write_text(source)
        if origin.startswith("rust:"):
            # Embedded Rust test strings often deliberately omit indentation.
            formatted = subprocess.run([str(compiler), "fmt", str(path)], capture_output=True, text=True, check=True)
            source = normalize_indentation(formatted.stdout, parser)
            path.write_text(source)
            subprocess.run([str(compiler), "check", "--eval", source], cwd=cwd,
                           capture_output=True, text=True, check=True)
        assertions, features, context_rows = expectations(source, parser)
        coverage.update(features)
        cases.append({"name": origin, "path": str(path), "assertions": assertions, "reindent": True,
                      "formatting": "compiler formatting plus AST indentation" if origin.startswith("rust:") else "original"})
        (output / "syntax" / f"syntax_test_{index:04}.vibe").write_text(syntax_test(source, assertions, origin))
        lines = source.splitlines()
        for row in context_rows:
            lines[row] += " # context boundary"
        commented = "\n".join(lines) + "\n"
        result = subprocess.run([str(compiler), "check", "--eval", commented], cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0:
            comment_assertions, _, _ = expectations(commented, parser)
            comment_path = output / "sources" / f"{index:04}-comments.vibe"
            comment_path.write_text(commented)
            cases.append({"name": origin + " + trailing comments", "path": str(comment_path),
                          "assertions": comment_assertions, "reindent": True})
            coverage["trailing-comment-variants"] += 1
        elif checked.returncode == 0:
            raise ValueError(f"Adding comments invalidated {origin}: {result.stdout}{result.stderr}")
        if index % 100 == 0:
            print(f"Generated {index + 1}/{len(selected)} programs", flush=True)
    for index, case in enumerate(continuation_cases()):
        subprocess.run([str(compiler), "check", "--eval", case["source"]], cwd=args.rust_repo,
                       capture_output=True, text=True, check=True)
        cases.append(case)
        (output / "syntax" / f"syntax_test_operator_{index:03}.vibe").write_text(
            syntax_test(case["source"], case["assertions"], case["name"]))
        coverage["binary-operator-continuations"] += 1
    manifest = {"website_count": len(website), "rust_origins": dict(origins), "coverage": dict(coverage),
                "compiler": subprocess.check_output([str(compiler), "--version"], text=True).strip(),
                "rejected": rejected, "cases": cases}
    for category in ("typed-local", "hash-key", "type", "block-union", "block-parameter", "string", "regex", "comment", "context:block_comment"):
        if not coverage[category]:
            raise ValueError("No coverage for " + category)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(cases)} cases from {len(selected)} programs; {len(rejected)} compiler rejections")
    print(json.dumps(coverage, sort_keys=True))


if __name__ == "__main__":
    main()
