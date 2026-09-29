"""Verify literal bytes and compiler results after native Sublime reindentation."""

import argparse
import ctypes
import json
from pathlib import Path
import subprocess


LITERALS = {"string", "quoted_symbol", "regex"}


def parser_for(library):
    from tree_sitter import Language, Parser
    handle = ctypes.CDLL(str(Path(library).resolve()))
    handle.tree_sitter_vibescript.restype = ctypes.c_void_p
    capsule = ctypes.pythonapi.PyCapsule_New
    capsule.restype = ctypes.py_object
    capsule.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]
    return Parser(Language(capsule(handle.tree_sitter_vibescript(), b"tree_sitter.Language", None)))


def literal_bytes(source, parser):
    """Capture complete literal lexemes, including nested interpolation strings."""
    tree = parser.parse(source.encode())
    if tree.root_node.has_error:
        raise ValueError("Cannot audit literals in a program with parse errors")
    result, pending = [], [tree.root_node]
    while pending:
        node = pending.pop()
        if node.type in LITERALS:
            result.append((node.type, node.text))
        pending.extend(reversed(node.children))
    return result


def source_for(case):
    return Path(case["path"]).read_text() if "path" in case else case["source"]


def mark_cases(cases, parser):
    count = 0
    for case in cases:
        if not case.get("reindent", True):
            continue
        try:
            literals = literal_bytes(source_for(case), parser)
        except ValueError:
            if "path" in case or case.get("literal_runtime") or case.get("preserve_literals"):
                raise
            continue
        if case.get("literal_runtime") or any(b"\n" in text for _, text in literals):
            case["preserve_literals"] = True
            count += 1
    return count


def verify_case(case, result, parser, compiler, cwd):
    before = source_for(case)
    failures = []
    checked = {"name": case["name"], "failures": failures}
    if "literal_source" not in result:
        failures.append("Native runner did not return the reindented source")
        return checked
    after = result["literal_source"]
    try:
        original = literal_bytes(before, parser)
        reindented = literal_bytes(after, parser)
    except ValueError as error:
        failures.append(str(error))
        return checked
    checked["literals"] = len(original)
    checked["literal_bytes"] = sum(len(text) for _, text in original)
    checked["bytes_preserved"] = original == reindented
    if original != reindented:
        failures.append("String, quoted symbol or regex literal bytes changed")
    directory = case.get("cwd", cwd)
    original_check = subprocess.run([compiler, "check", "--eval", before], cwd=directory, capture_output=True, timeout=30)
    checked["compiler_accepted"] = original_check.returncode == 0
    if original_check.returncode == 0:
        after_check = subprocess.run([compiler, "check", "--eval", after], cwd=directory, capture_output=True, timeout=30)
        if after_check.returncode:
            failures.append("Reindented source no longer passes vibes check: " + after_check.stderr.decode())
    if case.get("literal_runtime"):
        command = [compiler, "run", "--profile", "low", "--step-quota", "100000", "-e"]
        runs = [subprocess.run(command + [source], cwd=directory, capture_output=True, timeout=10)
                for source in (before, after)]
        checked["value_preserved"] = all(run.returncode == 0 for run in runs) and runs[0].stdout == runs[1].stdout
        if not checked["value_preserved"]:
            failures.append("Runtime result changed or execution failed: " + b"\n".join(run.stderr for run in runs).decode())
    return checked


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--results", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    manifest, results = json.loads(args.manifest.read_text()), json.loads(args.results.read_text())
    config = manifest["literal_audit"]
    parser = parser_for(config["library"])
    mark_cases(manifest["cases"], parser)
    checks = []
    for case, result in zip(manifest["cases"], results["cases"], strict=True):
        if case["name"] != result["name"]:
            raise ValueError("Manifest and native results refer to different cases")
        if case.get("preserve_literals"):
            checks.append(verify_case(case, result, parser, config["vibes"], config["cwd"]))
    failures = sum(len(check["failures"]) for check in checks)
    args.output.write_text(json.dumps({"checks": checks, "failures": failures}, indent=2) + "\n")
    print(f"{len(checks)} literal-preservation cases; {sum(check.get('literals', 0) for check in checks)} literals; {failures} failures")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
