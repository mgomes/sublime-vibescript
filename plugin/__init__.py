from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin

from .plugin import Vibescript

__all__ = (
    "plugin_loaded",
    "plugin_unloaded",
)


def plugin_loaded() -> None:
    register_plugin(Vibescript)


def plugin_unloaded() -> None:
    unregister_plugin(Vibescript)
