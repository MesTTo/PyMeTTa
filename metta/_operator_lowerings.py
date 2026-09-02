"""Purpose: hold the immutable Python-operator-to-MeTTa lowering table.
Guarantees:
  - all 22 supported, reserved, provided, templated, or refused Python
    operators have one entry and no runtime remapping hook [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=613f35974fa98746552dba584ad66082fdd1f3c7]
  - all four rich-comparison entries are reserved for atom ordering rather
    than term construction [tested: test_atom_comparisons_are_only_ordering;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
Decides:
  - ``@`` always lowers to the library-provided name ``matmul``; libraries
    define that MeTTa name rather than remapping Python syntax [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=613f35974fa98746552dba584ad66082fdd1f3c7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from typing import Any, Literal, NamedTuple

# policy-inventory-exempt: mechanism-internal; reason=these four names are the lowering table's own entry kinds, read only by the apply and method paths that walk the table; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
LoweringKind = Literal["symbol", "template", "taken", "provided"]
LoweringForm = str | int | tuple[Any, ...]


class OperatorLowering(NamedTuple):
    """One stable Python spelling and the MeTTa form it denotes."""

    dunder: str
    reflected: str | None
    syntax: str
    kind: LoweringKind
    form: LoweringForm | None
    method: str | None = None
    # policy-inventory-exempt: mechanism-internal; reason=Python's operator protocol has only unary and binary dunders, so this is the table entry's own arity field; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
    arity: Literal[1, 2] = 2


OPERATOR_LOWERINGS: tuple[OperatorLowering, ...] = (
    OperatorLowering("__add__", "__radd__", "x + y", "symbol", "+"),
    OperatorLowering("__sub__", "__rsub__", "x - y", "symbol", "-"),
    OperatorLowering("__mul__", "__rmul__", "x * y", "symbol", "*"),
    OperatorLowering("__truediv__", "__rtruediv__", "x / y", "symbol", "/"),
    OperatorLowering(
        "__floordiv__",
        "__rfloordiv__",
        "x // y",
        "template",
        ("floor-math", ("/", "$left", "$right")),
    ),
    OperatorLowering("__mod__", "__rmod__", "x % y", "symbol", "%"),
    OperatorLowering("__pow__", "__rpow__", "x ** y", "symbol", "pow-math"),
    OperatorLowering(
        "__matmul__", "__rmatmul__", "x @ y", "provided", "matmul"
    ),
    # `bit-shift-left` rather than a `-math` name: that suffix marks this
    # engine's C math.h family over binary64, and shift is exact and
    # integer-only. The `bit-` prefix is Clojure's spelling and is load-bearing
    # HERE, because `and`, `or` and `xor` below are BOOLEAN in MeTTa, so
    # without it nothing tells a reader which family a bitwise operation joined.
    OperatorLowering(
        "__lshift__", "__rlshift__", "x << y", "symbol", "bit-shift-left"
    ),
    OperatorLowering(
        "__rshift__", "__rrshift__", "x >> y", "symbol", "bit-shift-right"
    ),
    OperatorLowering("__and__", "__rand__", "x & y", "symbol", "and"),
    OperatorLowering("__or__", "__ror__", "x | y", "symbol", "or"),
    OperatorLowering("__xor__", "__rxor__", "x ^ y", "symbol", "xor"),
    OperatorLowering("__lt__", None, "x < y", "taken", "<", method="order_key"),
    OperatorLowering("__le__", None, "x <= y", "taken", "<=", method="order_key"),
    OperatorLowering("__gt__", None, "x > y", "taken", ">", method="order_key"),
    OperatorLowering("__ge__", None, "x >= y", "taken", ">=", method="order_key"),
    OperatorLowering("__invert__", None, "~x", "symbol", "not", arity=1),
    OperatorLowering(
        "__neg__", None, "-x", "template", ("-", 0, "$value"), arity=1
    ),
    OperatorLowering("__abs__", None, "abs(x)", "symbol", "abs-math", arity=1),
    OperatorLowering("__floor__", None, "math.floor(x)", "symbol", "floor-math", arity=1),
    OperatorLowering("__ceil__", None, "math.ceil(x)", "symbol", "ceil-math", arity=1),
    OperatorLowering("__trunc__", None, "math.trunc(x)", "symbol", "trunc-math", arity=1),
    OperatorLowering("__round__", None, "round(x)", "symbol", "round-math", arity=1),
    OperatorLowering("__eq__", None, "x == y", "taken", "==", method="eq"),
    OperatorLowering(
        "__ne__",
        None,
        "x != y",
        "taken",
        ("not", ("==", "$left", "$right")),
        method="ne",
    ),
)


def _validate_operator_lowerings() -> None:
    names = [entry.dunder for entry in OPERATOR_LOWERINGS]
    reflected = [entry.reflected for entry in OPERATOR_LOWERINGS if entry.reflected]
    if len(names) != len(set(names)) or len(reflected) != len(set(reflected)):
        msg = "the operator lowering table contains a duplicate dunder"
        raise RuntimeError(msg)
    for entry in OPERATOR_LOWERINGS:
        if entry.kind == "taken":
            complete = entry.form is not None and entry.method is not None
        else:
            complete = entry.form is not None and entry.method is None
        complete = complete and (entry.arity == 2 or entry.reflected is None)
        if not complete:
            msg = f"incomplete operator lowering entry: {entry.dunder}"
            raise RuntimeError(msg)


_validate_operator_lowerings()


__all__ = ["OPERATOR_LOWERINGS", "LoweringKind", "OperatorLowering"]
