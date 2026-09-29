#!/usr/bin/env python3
"""Request tests from native_runner.py installed in a Sublime test profile."""

import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = {"id": uuid.uuid4().hex, "action": "samples" if args.manifest else "syntax",
               "output": str(args.output.resolve())}
    if args.manifest:
        request["manifest"] = str(args.manifest.resolve())
    (args.profile / "request.json").write_text(json.dumps(request) + "\n")
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            result = json.loads(args.output.read_text())
            if result.get("id") == request["id"]:
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(0.2)
    else:
        raise SystemExit("Native Sublime tests timed out")
    if "error" in result:
        raise SystemExit(result["error"])
    tests = list(result.get("tests", {}).values()) + result.get("cases", [])
    if not tests:
        raise SystemExit("Native Sublime runner found no tests")
    assertions = sum(test["assertions"] for test in tests)
    failures = sum(len(test["failures"]) for test in tests)
    changed = sum(test.get("indent_passed") is False for test in tests)
    print(f"{len(tests)} files; {assertions} scope assertions; {failures} failures; {changed} indentation changes")
    print(f"Results: {args.output}")
    missing = result.get("missing_scopes", [])
    if missing:
        print("Untested scopes: " + ", ".join(missing))
    literal_failure = False
    if args.manifest:
        manifest = json.loads(args.manifest.read_text())
        if config := manifest.get("literal_audit"):
            literal_failure = subprocess.run([
                config["python"], str(Path(__file__).with_name("literal_audit.py")),
                "--manifest", str(args.manifest), "--results", str(args.output),
                "--output", str(args.output.with_suffix(".literals.json")),
            ]).returncode != 0
    return bool(failures or changed or missing or literal_failure)


if __name__ == "__main__":
    raise SystemExit(main())
