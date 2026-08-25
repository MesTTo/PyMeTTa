"""Purpose: name lib_strategy's reified strategy constructors in Python.

The values are Symbols. Calling one builds an ordinary Expression, so Python
and MeTTa store, query, serialize, and apply the same plans. Import the runtime
basis into a space with ``m += metta.lib.strategy`` before evaluating them.

Guarantees:
  - every export is a Symbol and importing this module neither creates an
    engine nor registers a callback [tested:
    test_strategy_exports_are_reified_atoms; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
  - ``try_`` is the exact ``try`` atom, following the keyword-collision spelling
    rule, and the two Stratego aliases keep their hyphenated atom names [tested:
    test_python_strategy_terms_use_the_shipped_basis; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import Final

from .atoms import S, Symbol

__all__ = [
    "TP",
    "TU",
    "all",
    "bottomup",
    "choice",
    "fail",
    "id",
    "innermost",
    "one",
    "repeat",
    "seq",
    "stratego_all",
    "stratego_one",
    "topdown",
    "try_",
]

id: Final[Symbol] = S["id"]  # noqa: A001 -- this is the strategy atom's public name
fail: Final[Symbol] = S["fail"]
seq: Final[Symbol] = S["seq"]
choice: Final[Symbol] = S["choice"]
try_: Final[Symbol] = S["try"]
repeat: Final[Symbol] = S["repeat"]
all: Final[Symbol] = S["all"]  # noqa: A001 -- this is the strategy atom's public name
one: Final[Symbol] = S["one"]
topdown: Final[Symbol] = S["topdown"]
bottomup: Final[Symbol] = S["bottomup"]
innermost: Final[Symbol] = S["innermost"]
stratego_all: Final[Symbol] = S["stratego-all"]
stratego_one: Final[Symbol] = S["stratego-one"]
TP: Final[Symbol] = S["TP"]
TU: Final[Symbol] = S["TU"]
