"""Sublime plugin used by run-native-tests.py in an isolated test profile."""

import difflib
import json
from pathlib import Path
import traceback

import sublime
import sublime_api


PROFILE = Path(__file__).resolve().parents[2]
LAST_REQUEST = None


def write_result(request, result):
    path = Path(request["output"])
    path.write_text(json.dumps({"id": request["id"], **result}, indent=2) + "\n")


def run_request(request):
    try:
        if request["action"] == "syntax":
            tests = {}
            for resource in sublime.find_resources("syntax_test_*.vibe"):
                if resource.startswith(("Packages/Vibescript/", "Packages/VibescriptCorpus/")):
                    count, failures = sublime_api.run_syntax_test(resource)
                    tests[resource] = {"assertions": count, "failures": failures}
            write_result(request, {"tests": tests})
        else:
            cases = json.loads(Path(request["manifest"]).read_text())["cases"]
            run_case(request, cases, 0, [])
    except Exception:
        write_result(request, {"error": traceback.format_exc()})


def run_case(request, cases, index, results):
    if index == len(cases):
        write_result(request, {"cases": results})
        return
    window = sublime.active_window()
    if window is None:
        sublime.run_command("new_window")
        sublime.set_timeout(lambda: run_case(request, cases, index, results), 50)
        return
    view = window.new_file()
    view.set_scratch(True)
    view.settings().set("tab_size", 2)
    view.settings().set("translate_tabs_to_spaces", True)
    view.settings().set("detect_indentation", False)
    view.assign_syntax("Packages/Vibescript/Vibescript.sublime-syntax")
    case = cases[index]
    source = Path(case["path"]).read_text() if "path" in case else case["source"]
    view.run_command("append", {"characters": source})
    sublime.set_timeout(lambda: check_case(request, cases, index, results, view, source), 10)


def check_case(request, cases, index, results, view, source):
    try:
        case = cases[index]
        failures = []
        for assertion in case.get("assertions", []):
            row, column, selector = assertion
            point = view.text_point(row, column)
            if not view.match_selector(point, selector):
                failures.append({"row": row, "column": column, "expected": selector,
                                 "actual": view.scope_name(point)})
        result = {"name": case["name"], "assertions": len(case.get("assertions", [])),
                  "failures": failures}
        if case.get("debug"):
            result["metadata"] = []
            for line in view.lines(sublime.Region(0, view.size())):
                point = line.begin() + len(view.substr(line)) - len(view.substr(line).lstrip())
                result["metadata"].append({"line": view.substr(line), "start": view.scope_name(point),
                                          "end": view.scope_name(line.end()),
                                          "preserve": view.meta_info("preserveIndent", line.end()),
                                          "ignore": view.meta_info("unIndentedLinePattern", point)})
        if case.get("reindent", True):
            view.run_command("reindent", {"single_line": False})
            actual = view.substr(sublime.Region(0, view.size()))
            expected = case.get("expected", source)
            result["indent_passed"] = actual == expected
            if actual != expected:
                result["diff"] = "".join(difflib.unified_diff(
                    expected.splitlines(True), actual.splitlines(True),
                    fromfile=case["name"], tofile="reindented"))
                result["actual"] = actual
        results.append(result)
        view.close()
        (PROFILE / "progress.json").write_text(json.dumps({"done": index + 1, "total": len(cases)}) + "\n")
        sublime.set_timeout(lambda: run_case(request, cases, index + 1, results), 1)
    except Exception:
        view.close()
        write_result(request, {"error": traceback.format_exc()})


def poll():
    global LAST_REQUEST
    try:
        request = json.loads((PROFILE / "request.json").read_text())
        if request["id"] != LAST_REQUEST:
            LAST_REQUEST = request["id"]
            run_request(request)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    sublime.set_timeout(poll, 100)


def plugin_loaded():
    sublime.load_settings("Preferences.sublime-settings").set("close_windows_when_empty", False)
    sublime.set_timeout(poll, 500)
