"""Generate bounded line-balancing indentation preferences."""

from pathlib import Path
import plistlib


MAX_DEPTH = 3
METHOD_SCOPE = "source.vibescript meta.function.signature - meta.group.parameters - meta.annotation.type"
STRING = r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])*'"
REGEX = r'''(?<![\w)\]}"/])/(?![\s=/])(?:\\.|\[(?:\\.|[^\]\\])*\]|[^/\\\n])+/[a-z]*'''
SYMBOL = r':(?:[a-zA-Z_]\w*[!?]?|\[\]=?|<=>|===|\*\*|//|<<|<=|>=|==|!=|&&|\|\||[+*/%<>&|!\-])'
BOUNDARY = r'\b(?![!?]|[ \t]*:)'
# Postfix conditions do not open blocks. Leading branch clauses reopen after
# Sublime's decrease rule has outdented them.
OPEN = (
    r'(?<![\w.:])(?:def|class|module|enum)' + BOUNDARY
    + r'|(?:^|(?<=[;=(,:\[{|])|(?<=\bthen)|(?<=\belse))[ \t]*(?:if|while|for|case|begin)' + BOUNDARY
    + r'|^[ \t]*(?:elsif|else|when|rescue|ensure)' + BOUNDARY
    + r'|[\[({]'
)
CLOSE = r'(?<![\w.:])end' + BOUNDARY + r'|[\])}]'
LITERAL = f'(?:{STRING}|{REGEX}|{SYMBOL})'
OPEN = f'(?:{OPEN})'
CLOSE = f'(?:{CLOSE})'
# A recognized literal must stay opaque even when a later balance check fails.
ATOM = f'(?>{LITERAL}|(?!{OPEN}|{CLOSE}|{LITERAL})' + r'''[^#"'\\\r\n])'''
BEFORE_SEPARATOR = f'(?>{LITERAL}|(?!{LITERAL})' + r'''[^;#"'\\\r\n])*;'''


def ordinary_increase_pattern():
    scan = f'(?:{STRING}|{REGEX}|' + r'''[^#"'\\])*'''
    return (
        r'^\s*(?:(export\s+)?((private|public|protected)\s+)?def|class|module|enum|if|elsif|else|while|for|case|when|begin|rescue|ensure)\b(?!\s*:)'
        + f'(?!{scan}' + r'\bend\b(?=[ \t]*(?:;|#|$)))'
        + r'|^(?!\s*=(?:begin|end)\b)' + scan + r'[;=(]\s*(?:begin|case|if|while|for)\b'
        + f'(?!{scan}' + r'\bend\b)'
        + r'|^(?!\s*=(?:begin|end)\b)' + scan + r'[\[({]\s*(?:\|[^#]*\|\s*)?(?:#.*)?$'
    )


def increase_pattern():
    balanced = f'(?:{ATOM})*'
    for _ in range(MAX_DEPTH):
        balanced = f'(?:{ATOM}|{OPEN}{balanced}{CLOSE})*'
    return (
        r'^' + f'(?={BEFORE_SEPARATOR})'
        + r'(?![ \t]*=(?:begin|end)\b)'
        + f'(?:{balanced}{CLOSE})*{balanced}(?:{OPEN}{balanced}){{1,{MAX_DEPTH}}}'
        + r'[ \t]*(?:#.*)?$'
        + f'|^(?!{BEFORE_SEPARATOR})(?:{ordinary_increase_pattern()})'
    )


def method_increase_pattern():
    return r'^\s*[)\]}]|' + increase_pattern()


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent.parent / 'preferences'
    path = directory / 'Indentation Rules.tmPreferences'
    settings = plistlib.loads(path.read_bytes())
    settings['settings']['increaseIndentPattern'] = increase_pattern()
    path.write_bytes(plistlib.dumps(settings, sort_keys=False))
    path = directory / 'Indentation Rules - Method Closers.tmPreferences'
    path.write_bytes(plistlib.dumps({
        'name': 'Method Signature Closers', 'scope': METHOD_SCOPE,
        'settings': {'increaseIndentPattern': method_increase_pattern()},
    }, sort_keys=False))
