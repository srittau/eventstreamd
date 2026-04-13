from importlib import import_module
from typing import Any

from evtstrd.exc import PluginError


def load_plugin(plugin: str, obj: str) -> Any | None:
    try:
        pkg = import_module("." + plugin, "evtstrd.plugins")
    except ImportError:
        return None
    if not hasattr(pkg, obj):
        raise PluginError(plugin, f"object '{obj}' not found")
    return getattr(pkg, obj)
