"""Adapters that keep CacheSage-UC aligned with the NutShell/Toffee flow."""

from .nutshell_example import ExampleNutShellLayout, inspect_example_tree
from .toffee_bridge import to_toffee_case, to_toffee_cases

__all__ = [
    "ExampleNutShellLayout",
    "inspect_example_tree",
    "to_toffee_case",
    "to_toffee_cases",
]
