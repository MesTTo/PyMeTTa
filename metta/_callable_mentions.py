"""Purpose: map standard Python callables to the MeTTa functions they mention.

Guarantees:
  - encoding and compiled attribute calls consult this one identity table
    [tested: test_callable_mentions_share_operator_and_fourteen_math_names,
    test_callable_mentions_require_identity_even_when_equality_is_spoofed;
    commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
Decides:
  - the fourteen math names are the declarations in
    ``lib/lib_builtin_types/lib_builtin_types.metta`` from ``pow-math`` through ``atan-math``
    [source: lib/lib_builtin_types/lib_builtin_types.metta:45; commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
"""

from __future__ import annotations

import builtins
import math
import operator
from typing import Any, Final

from ._operator_lowerings import OPERATOR_LOWERINGS

_OPERATOR_CALLABLES: Final[dict[str, Any]] = {
    "__abs__": operator.abs,
    "__add__": operator.add,
    "__and__": operator.and_,
    "__ge__": operator.ge,
    "__gt__": operator.gt,
    "__invert__": operator.invert,
    "__le__": operator.le,
    "__lt__": operator.lt,
    "__matmul__": operator.matmul,
    "__mod__": operator.mod,
    "__mul__": operator.mul,
    "__or__": operator.or_,
    "__pow__": operator.pow,
    "__sub__": operator.sub,
    "__truediv__": operator.truediv,
    "__xor__": operator.xor,
}

_SYMBOL_OPERATOR_MENTIONS: Final[dict[Any, str]] = {
    _OPERATOR_CALLABLES[entry.dunder]: entry.form
    for entry in OPERATOR_LOWERINGS
    if entry.dunder in _OPERATOR_CALLABLES
    # policy-inventory-exempt: mechanism-internal; reason=only table rows whose form is one callable head can be mentioned as one Symbol; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
    and entry.kind in {"symbol", "provided"}
    and isinstance(entry.form, str)
}

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

CALLABLE_MENTIONS: Final[dict[Any, str]] = (
    _SYMBOL_OPERATOR_MENTIONS | MATH_CALLABLE_MENTIONS
)

_CALLABLE_MENTIONS_BY_ID: Final[dict[int, tuple[Any, str]]] = {
    id(value): (value, mention) for value, mention in CALLABLE_MENTIONS.items()
}

_CALLABLE_ARITIES_BY_ID: Final[dict[int, tuple[Any, tuple[int, ...]]]] = {
    # policy-inventory-exempt: mechanism-internal; reason=abs and invert are the two unary callables in the closed operator mention table and every other mentioned operator is binary; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
    id(value): (value, (1,) if dunder in {"__abs__", "__invert__"} else (2,))
    for dunder, value in _OPERATOR_CALLABLES.items()
    if value in CALLABLE_MENTIONS
}
_CALLABLE_ARITIES_BY_ID.update(
    {
        # policy-inventory-exempt: mechanism-internal; reason=log and round are the two mentioned standard callables with both one- and two-argument Python forms; evidence=extensions/python/metta/_define_expression.py:_adapt_mentioned_call
        id(value): (value, (1, 2) if value in {math.log, builtins.round} else (2,)
                    if value is math.pow else (1,))
        for value in MATH_CALLABLE_MENTIONS
    }
)


def callable_mention(value: Any) -> str | None:
    """Return the MeTTa symbol named by one exact standard callable."""
    if not callable(value):
        return None
    entry = _CALLABLE_MENTIONS_BY_ID.get(id(value))
    if entry is None or entry[0] is not value:
        return None
    return entry[1]


def callable_arities(value: Any) -> tuple[int, ...] | None:
    """Return accepted positional arities for one exact mentioned callable."""
    entry = _CALLABLE_ARITIES_BY_ID.get(id(value))
    if entry is None or entry[0] is not value:
        return None
    return entry[1]


__all__ = ["CALLABLE_MENTIONS", "MATH_CALLABLE_MENTIONS", "callable_mention"]
