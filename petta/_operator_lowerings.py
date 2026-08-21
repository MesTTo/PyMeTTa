"""Purpose: hold the immutable Python-operator-to-MeTTa lowering table.
Guarantees:
  - all 22 supported, reserved, provided, templated, or refused Python
    operators have one entry and no runtime remapping door [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=613f35974fa98746552dba584ad66082fdd1f3c7]
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

LoweringKind = Literal["symbol", "template", "absent", "taken", "provided"]
LoweringForm = str | int | tuple[Any, ...]


class OperatorLowering(NamedTuple):
    """One stable Python spelling and the MeTTa form it denotes."""

    dunder: str
    reflected: str | None
    syntax: str
    kind: LoweringKind
    form: LoweringForm | None
    method: str | None = None
    reason: str | None = None
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
    OperatorLowering(
        "__lshift__",
        "__rlshift__",
        "x << y",
        "absent",
        None,
        reason="MeTTa has no integer-left-shift operation",
    ),
    OperatorLowering(
        "__rshift__",
        "__rrshift__",
        "x >> y",
        "absent",
        None,
        reason="MeTTa has no integer-right-shift operation",
    ),
    OperatorLowering("__and__", "__rand__", "x & y", "symbol", "and"),
    OperatorLowering("__or__", "__ror__", "x | y", "symbol", "or"),
    OperatorLowering("__xor__", "__rxor__", "x ^ y", "symbol", "xor"),
    OperatorLowering("__lt__", None, "x < y", "symbol", "<"),
    OperatorLowering("__le__", None, "x <= y", "symbol", "<="),
    OperatorLowering("__gt__", None, "x > y", "symbol", ">"),
    OperatorLowering("__ge__", None, "x >= y", "symbol", ">="),
    OperatorLowering("__invert__", None, "~x", "symbol", "not", arity=1),
    OperatorLowering(
        "__neg__", None, "-x", "template", ("-", 0, "$value"), arity=1
    ),
    OperatorLowering("__abs__", None, "abs(x)", "symbol", "abs-math", arity=1),
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
        if entry.kind == "absent":
            complete = entry.form is None and entry.reason is not None
        elif entry.kind == "taken":
            complete = entry.form is not None and entry.method is not None
        else:
            complete = entry.form is not None and entry.method is None
        complete = complete and (entry.arity == 2 or entry.reflected is None)
        if not complete:
            msg = f"incomplete operator lowering entry: {entry.dunder}"
            raise RuntimeError(msg)


_validate_operator_lowerings()


__all__ = ["OPERATOR_LOWERINGS", "LoweringKind", "OperatorLowering"]
