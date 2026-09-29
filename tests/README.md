# Corpus checks

`corpus_cases.json` preserves real Rust test and website programs, their origins,
and parser-derived scope assertions. `syntax_test_corpus.vibe` renders those same
assertions for the native syntax-test runner used in CI. The Python 3.11+ suite checks
that they agree and tests the indentation expressions:

```sh
python3 -m unittest discover -s tests
```

The operator inventory in `scripts/operators.py` cross-checks symbol and method
spellings, binary scopes, and both continuation matchers. Its native syntax
fixture covers each complete token. Regenerate it with:

```sh
python3 scripts/operators.py > tests/syntax_test_operators.vibe
```

`scripts/indentation.py` generates the bounded opener/closer pattern rather than
maintaining an expanded regex by hand. `scripts/semicolon_cases.py` enumerates
mixed `if`, `while`, `def` and brace-block nesting through three levels, both
fully closed and with an outer block still open. It includes statement prefixes,
trailing comments, literals containing delimiters, and postfix conditions. The
Python suite cross-checks these cases and the generated preference. The bounded
rule applies to lines containing a separator outside literals/comments; other
lines retain the existing indentation heuristics:

```sh
python3 scripts/indentation.py
```

## Type inventory

`syntax/type_inventory.json` is extracted from type positions in Rust's
`vibes prelude`: receivers, aliases, parameters, generic constraints and return
types. The extractor also records generic arities. Method names, parameter names,
symbol literals and default values do not contribute type names.

Regenerate the inventory, prelude snapshot, shared syntax variables and native
type cases together, then compare with the live compiler during the test run:

```sh
python3 scripts/type_inventory.py --vibes "$rust/target/gate/vibes" --write
VIBES="$rust/target/gate/vibes" python3 -m unittest discover -s tests
```

Without `VIBES`, the suite compares against `fixtures/prelude.vibe`, so CI needs
no compiler installation. The same inventory drives annotation, block-union,
generic-literal and standalone-shape starts, including quoted field keys,
optional types, open shapes, tuples and function types. The corpus generator's
type expectations consume it too. Native tests cover every builtin as the first
field with both bare and quoted keys, and fall back to expression scopes for
constants, calls and ordinary literal values, even in later fields. As in the
compiler, a bare `nil` field is a hash value; `nil | int` tests nil in a type.

`scripts/type_cases.py` emits the additional scope/reindent manifest. These
lexical regression cases include incomplete or invalid expressions to exercise
fallback; they are separate from the compiler-accepted corpus sample.

`scripts/alias_cases.py` generates compiler-checked aliases with lowercase,
uppercase, underscore and Unicode names, and uses in local, parameter, return,
block and qualified annotations. The Python suite checks their source with the
live compiler when `VIBES` is set. Alias names have no generic parameter list;
generic method declarations such as `def p<T>` remain prelude-only notation.
Alias names use ordinary identifiers; the language's method-only `?`/`!` suffix
rule still applies, while `id?` in an annotation is an optional alias type.
The full corpus audit includes these alias scope/reindent cases too.

## Nested signatures and expressions

`scripts/nested_cases.py` generates 60 compiler-checked cases with independently
written indentation: method parameter lists containing function types, all pairs
of nested tuple/shape types, alternating types three levels deep, structured
return types, and calls and defaults containing nested blocks and parentheses.
The cases cover outer `)` and `) -> T` closers, inner function-type `) -> T`
closers, module methods, and trailing comments on every line.

The signature scope survives the complete parameter and return type. Its
indentation preference reopens the method body only after leaving both the
parameter list and the nested annotation. Ordinary parenthesis closers use the
base rule; their text alone cannot distinguish a function type from a method.
Native assertions check this scope distinction at line ends, and the corpus
audit requires every generated case to remain byte-for-byte stable on reindent.

```sh
python3 scripts/nested_cases.py > tests/syntax_test_nested.vibe
python3 scripts/nested_cases.py --manifest > "$cache/nested-cases.json"
python3 scripts/run-native-tests.py "$profile" \
  --manifest "$cache/nested-cases.json" --output "$cache/nested.json"
```

## Native scope and reindent checks

Use an isolated Sublime Text profile containing `Packages/Vibescript` linked to
this repository. Copy `scripts/native_runner.py` (not a symlink) to
`Packages/User/editor_tooling_test.py`, then start Sublime with that profile and
an open window. `profile` below is the directory containing `Packages`.

```sh
python3 scripts/run-native-tests.py "$profile" --output "$cache/syntax.json"
python3 scripts/run-native-tests.py "$profile" \
  --manifest tests/corpus_cases.json --output "$cache/regressions.json"
python3 scripts/operators.py --manifest > "$cache/operator-cases.json"
python3 scripts/run-native-tests.py "$profile" \
  --manifest "$cache/operator-cases.json" --output "$cache/operators.json"
python3 scripts/semicolon_cases.py > "$cache/semicolon-cases.json"
python3 scripts/run-native-tests.py "$profile" \
  --manifest "$cache/semicolon-cases.json" --output "$cache/semicolons.json"
```

The plugin creates scratch buffers, asserts scopes against the original source,
runs Sublime's `reindent` command, and compares every byte with the input. It never
rewrites the source files. The report includes scope mismatches and indentation
diffs. Do not submit concurrent requests to the same profile.

## Generate the broad sample

The generator requires the Rust `target/gate/vibes` binary, the accepted manifest
produced by tree-sitter-vibescript's corpus checker, the migrated website content,
and the matching Tree-sitter grammar. Put generated files in a cache directory.

```sh
python3.13 -m venv "$cache/venv"
"$cache/venv/bin/pip" install -r scripts/requirements-corpus.txt
cc -O2 -dynamiclib -fPIC -I "$grammar/src" \
  "$grammar/src/parser.c" "$grammar/src/scanner.c" \
  -o "$cache/vibescript.dylib"
"$cache/venv/bin/python" scripts/generate-corpus-tests.py \
  --rust-repo "$rust" --accepted-manifest "$cache/corpora/manifest.json" \
  --website "$site/internal/catalog/content" \
  --library "$cache/vibescript.dylib" --output "$cache/sublime-corpus"
```

On Linux use `-shared` instead of `-dynamiclib`. The Python binding is pinned:
0.26.0 crashed while traversing these trees; 0.25.2 passed the audit.

The deterministic sample spans Rust `tests/`, `corpus/glue/`, and `examples/`,
with targeted inclusion of typed block unions and block comments. All website
examples are included. Each standalone program is checked with `vibes check`.
Website examples requiring injected host capabilities remain in the editor tests;
their compiler diagnostics are recorded in the manifest.

Embedded Rust strings often omit indentation, so their copies first receive
compiler formatting and indentation derived independently from the parse tree.
They are checked again after formatting. Website examples retain their original
bytes. No expected indentation is generated by Sublime.

The parser supplies positive and negative assertions for local annotations,
hash/keyword labels, types, block parameters and union delimiters, strings,
regex bodies, comments, and ordinary expressions. The generator also appends
comments to lines opening syntax contexts and checks the variants with the
compiler. Invalidating an accepted program fails generation. Coverage counters
and source provenance appear in `manifest.json`.

The broad sample also includes 92 compiler-checked operator cases: every binary
operator at a line ending, both starting and extending a continuation, with and
without trailing comments. Their expected hanging indentation is independent
of the normalizer. Range expressions use parentheses to keep the right operand
inside a bounded range.

The generator also checks all 684 semicolon nesting cases with the Rust compiler
and includes it in the native reindent audit. Their indentation is written by
the fixture generator, independently of both the regex and the AST normalizer.

Link `$cache/sublime-corpus/syntax` to `Packages/VibescriptCorpus` in the test
profile, then run:

```sh
python3 scripts/run-native-tests.py "$profile" --output "$cache/all-syntax.json"
python3 scripts/run-native-tests.py "$profile" \
  --manifest "$cache/sublime-corpus/manifest.json" \
  --output "$cache/all-reindent.json"
```

The September 2026 audit used Sublime build 4215, Rust Vibescript v0.80.0,
365 Rust programs and all 203 website examples. Its 561 added-comment variants,
92 operator cases and 684 semicolon cases brought the native audit to 1,905 cases.
Seven website examples require host capabilities and therefore have no
compiler-accepted comment variant.
