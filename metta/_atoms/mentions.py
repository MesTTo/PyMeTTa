"""Purpose: bind source-described standard callables to their MeTTa mentions.

Guarantees: callable identity, aliases and accepted positional shapes are
projections of the locked source inventory [source:
extensions/python/metta/_atoms/_python_protocols.py:CALLABLES; commit=WORKTREE].
Decides: the math table names the engine's fourteen math meanings. Operator
term mentions use the joined atom policy; exact Python calls use the existing
py-operator service. Runtime bindings contain only exported module attributes,
so the pinned reference does not raise the package's supported Python floor.
"""

from __future__ import annotations

import builtins
import math
import operator
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any, Final

from metta._atoms._python_protocols import BY_CALLABLE, CALLABLES, PythonCallable
from metta._atoms.operators import OPERATOR_LOWERINGS, selector

_EXPORTED_OPERATORS = vars(operator)
OPERATOR_CALLABLES: Final[Mapping[str, Callable[..., Any]]] = MappingProxyType({
    row.selector: _EXPORTED_OPERATORS[row.id[1]]
    for row in CALLABLES
    if row.id[0] == operator.__name__ and not row.id[1].startswith("__")
    and row.id[1] in _EXPORTED_OPERATORS
})

_SYMBOL_OPERATOR_MENTIONS: Final[dict[Any, str]] = {
    getattr(operator, entry.source.callable[1]): entry.form
    for entry in OPERATOR_LOWERINGS
    if entry.source.callable[0] == operator.__name__
    # policy-inventory-exempt: mechanism-internal; reason=these atom policy shapes denote one callable head; evidence=extensions/python/metta/_atoms/model.py:_operator_method
    and entry.kind in {"symbol", "provided"} and isinstance(entry.form, str)
}

# closed-set: decides; policy=which Python math function has the same meaning as each engine math head; reads=extensions/python/metta/_atoms/_python_protocols.py:BY_CALLABLE supplies its Python signature
MATH_CALLABLE_MENTIONS: Final[dict[Any, str]] = {
    math.pow: "pow-math",
    math.sqrt: "sqrt-math",
    math.fabs: "abs-math",
    math.log: "log-math",
    math.trunc: "trunc-math",
    math.ceil: "ceil-math",
    math.floor: "floor-math",
    builtins.round: "round-math",
    math.sin: "sin-math",
    math.asin: "asin-math",
    math.cos: "cos-math",
    math.acos: "acos-math",
    math.tan: "tan-math",
    math.atan: "atan-math",
}

CALLABLE_MENTIONS: Final[dict[Any, str]] = _SYMBOL_OPERATOR_MENTIONS | MATH_CALLABLE_MENTIONS
_CALLABLE_MENTIONS_BY_ID: Final[dict[int, tuple[Any, str]]] = {
    id(value): (value, mention) for value, mention in CALLABLE_MENTIONS.items()
}
_CALLABLE_SHAPES_BY_ID: Final[dict[int, tuple[Any, PythonCallable]]] = {
    id(_EXPORTED_OPERATORS[row.id[1]]): (_EXPORTED_OPERATORS[row.id[1]], row)
    for row in CALLABLES
    if row.id[0] == operator.__name__ and row.id[1] in _EXPORTED_OPERATORS
}
_CALLABLE_SHAPES_BY_ID.update({
    id(value): (value, BY_CALLABLE[(value.__module__, value.__name__)])
    for value in MATH_CALLABLE_MENTIONS
})
_OPERATOR_SELECTORS_BY_ID: Final[dict[int, tuple[Any, str]]] = {
    id(value): (value, name) for name, value in OPERATOR_CALLABLES.items()
}
# Several exported aliases can denote one object. The atom operation's exact
# source alias supplies its canonical selector. Distinct C wrappers keep
# distinct identities even when their fallback Python bodies were aliases.
_OPERATOR_SELECTORS_BY_ID.update({
    id(value): (value, selector(entry))
    for entry in OPERATOR_LOWERINGS
    if entry.source.callable[0] == operator.__name__
    for value in (getattr(operator, entry.source.callable[1]),)
})


def callable_mention(value: Any) -> str | None:
    """Return the MeTTa symbol named by one exact standard callable."""
    entry = _CALLABLE_MENTIONS_BY_ID.get(id(value))
    return entry[1] if entry is not None and entry[0] is value else None


def callable_accepts_positional(value: Any, count: int) -> bool:
    """Recognize a source call shape without introducing an argument binder."""
    entry = _CALLABLE_SHAPES_BY_ID.get(id(value))
    return entry is not None and entry[0] is value and entry[1].accepts_positional(count)


def operator_callable_selector(value: Any) -> str | None:
    """Return the existing runtime selector for one exact operator callable."""
    entry = _OPERATOR_SELECTORS_BY_ID.get(id(value))
    return entry[1] if entry is not None and entry[0] is value else None


__all__ = [
    "CALLABLE_MENTIONS", "MATH_CALLABLE_MENTIONS", "OPERATOR_CALLABLES",
    "callable_accepts_positional", "callable_mention", "operator_callable_selector",
]
