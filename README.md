# Vibescript package for Sublime Text

Adds [Vibescript](https://github.com/mgomes/vibescript) language support to Sublime Text, mirroring the existing Zed extension with syntax highlighting and `vibes lsp` integration.

## Features

- Syntax highlighting for `.vibe` files
- Comment toggling and indentation rules
- Symbol indexing for classes and methods
- Diagnostics, hover information, and completions through Sublime's `LSP` package

## Prerequisites

- [LSP](https://packagecontrol.io/packages/LSP) installed in Sublime Text
- The `vibes` binary available on your `PATH`

## Development install

1. Clone this repo into `~/Library/Application Support/Sublime Text/Packages/`
2. Install the `LSP` package through Package Control
3. Restart Sublime Text

The package checkout directory does not need a special name. The bundled LSP helper resolves its settings path dynamically.

## Configuration

The default language server command is:

```json
["vibes", "lsp"]
```

Override it in `Preferences > Package Settings > sublime-vibescript > Settings` by editing `LSP-vibescript.sublime-settings` if your `vibes` binary lives elsewhere.
