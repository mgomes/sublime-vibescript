"""Render parser-derived scope assertions as native Sublime syntax tests."""

from collections import defaultdict


def syntax_test(source, assertions, origin):
    by_row = defaultdict(list)
    for row, column, selector in assertions:
        by_row[row].append((column, selector))
    lines = ['# SYNTAX TEST "Packages/Vibescript/Vibescript.sublime-syntax"', '# ' + origin, '']
    for row, line in enumerate(source.splitlines()):
        lines.append(line)
        for column, selector in by_row[row]:
            lines.append(("# <- " if column == 0 else "#" + " " * (column - 1) + "^ ") + selector)
    return "\n".join(lines) + "\n"
