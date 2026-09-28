# Vibescript package for Sublime Text

Adds [Vibescript](https://github.com/xipkit/vibescript) syntax support to Sublime Text.

## Features

- Syntax highlighting for `.vibe` files, including strings with interpolation,
  regex literals, symbols, enums, typed locals and signatures, generics,
  unions, optionals, tuples, record shapes, type aliases, and brace blocks
- Comment toggling and indentation rules
- Symbol indexing for classes, methods, and enums

## Language server

Diagnostics, hover documentation, and completions live in the separate
[LSP-vibescript](https://github.com/mgomes/LSP-vibescript) package, so this
package works standalone for highlighting. Install LSP-vibescript alongside
Sublime's `LSP` package to add language-server features.

Supports the Rust implementation of Vibescript v0.80.0. Install its CLI and
language server with:

```sh
cargo install --git https://github.com/xipkit/vibescript --tag v0.80.0 vibes
```

Add Cargo's bin directory (`~/.cargo/bin` by default) to your editor's `PATH`.
The server command remains `vibes lsp`. Replace any path to the retired Go binary.

## Development install

1. Clone this repo into `~/Library/Application Support/Sublime Text/Packages/` as `Vibescript`:

   ```sh
   git clone https://github.com/mgomes/sublime-vibescript.git \
     "$HOME/Library/Application Support/Sublime Text/Packages/Vibescript"
   ```

2. Restart Sublime Text

The syntax tests expect the package to be installed as `Vibescript`.

## Syntax tests

Open `tests/syntax_test_vibescript.vibe` and run Build (`⌘B`) to execute the
assertions in-editor. CI runs the same tests with Sublime's headless
`syntax_tests` binary.

Run `python3 -m unittest discover -s tests` for indentation-rule checks, operator
consistency, and fixture consistency. The checked-in corpus tests contain 30
real-code cases, including trailing-comment variants, plus scope and continuation
tests for every binary operator. See [the corpus audit instructions](tests/README.md)
to generate a broader sample and verify scopes and whole-file reindentation
with the native editor.

## Known limitations

Regex literals are detected with a heuristic (a `/` that does not follow a
value and is not followed by a space or `=`), so half-spaced division like
`a /b` may highlight as a regex. `a / b` and `a/b` highlight correctly.

The `# vibe: 0.80` first-line marker still identifies extensionless scripts.
It is an ordinary comment to the Rust compiler, not a version constraint.
Removed syntax (`unless`, `until`, `do ... end`, percent literals and symbol
hash keys) is no longer highlighted as supported language syntax. Use `vibes fix`
to migrate old programs.

Bare zero-argument function calls and local references share the same spelling;
lexical highlighting cannot distinguish them. Dotted calls remain highlighted.
