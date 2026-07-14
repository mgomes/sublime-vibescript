# Vibescript package for Sublime Text

Adds [Vibescript](https://github.com/mgomes/vibescript) language support to Sublime Text, mirroring the existing Zed extension with syntax highlighting and `vibes lsp` integration.

## Features

- Syntax highlighting for `.vibe` files, including typed signatures, regex
  literals, `%w[...]` / `%i(...)` arrays, symbols, and directive comments
- Comment toggling and indentation rules
- Symbol indexing for classes and methods
- Diagnostics, hover information, and completions through Sublime's `LSP` package

## Prerequisites

- [LSP](https://packagecontrol.io/packages/LSP) installed in Sublime Text
- The `vibes` binary available on your `PATH`

## Development install

1. Clone this repo into `~/Library/Application Support/Sublime Text/Packages/` as `Vibescript`:

   ```sh
   git clone https://github.com/mgomes/sublime-vibescript.git \
     "$HOME/Library/Application Support/Sublime Text/Packages/Vibescript"
   ```

2. Install the `LSP` package through Package Control
3. Restart Sublime Text

The LSP helper resolves its settings path dynamically and works under any
package directory name; only the syntax tests expect the package to be
installed as `Vibescript`.

## Configuration

The default language server command is:

```json
["vibes", "lsp"]
```

Override it in `Preferences > Package Settings > sublime-vibescript > Settings` by editing `LSP-vibescript.sublime-settings` if your `vibes` binary lives elsewhere.

## Syntax tests

Open `tests/syntax_test_vibescript.vibe` and run Build (`⌘B`) to execute the
assertions in-editor. CI runs the same tests with Sublime's headless
`syntax_tests` binary.

## Known limitations

Regex literals are detected with a heuristic (a `/` that does not follow a
value and is not followed by a space or `=`), so half-spaced division like
`a /b` may highlight as a regex. `a / b` and `a/b` highlight correctly.
