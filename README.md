# Vibescript package for Sublime Text

Adds [Vibescript](https://github.com/mgomes/vibescript) syntax support to Sublime Text.

## Features

- Syntax highlighting for `.vibe` files, including strings with interpolation,
  regex literals, `%w[...]` / `%i(...)` arrays, symbols, enums, typed
  signatures, and directive comments
- Comment toggling and indentation rules
- Symbol indexing for classes, methods, and enums

## Language server

Diagnostics, hover documentation, and completions live in the separate
[LSP-vibescript](https://github.com/mgomes/LSP-vibescript) package, so this
package works standalone for highlighting. Install LSP-vibescript alongside
Sublime's `LSP` package to add language-server features.

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

## Known limitations

Regex literals are detected with a heuristic (a `/` that does not follow a
value and is not followed by a space or `=`), so half-spaced division like
`a /b` may highlight as a regex. `a / b` and `a/b` highlight correctly.
