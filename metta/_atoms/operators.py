"""Purpose: ONE table for one relation: how a Python operator spells in MeTTa.

Every consumer of that relation reads this. There used to be eight tables for
it -- this one, `_prelude._PYTHON_OPERATORS`, `_name_mapping.OPERATOR_WORDS`,
and `_define_expression`'s `_BINOPS`, `_NATIVE_BINOPS`, `_COMPARE`,
`_NATIVE_COMPARE` and `_INPLACE_BINOPS` -- each keyed differently (by dunder,
by `operator`-module selector, by word, by `ast` node class) and each holding
its own copy of the MeTTa head. A row here carries every key and every
spelling, and each of those tables is now a projection of it, so a head that
moves moves once.

Two spellings are DERIVED rather than carried: the `operator`-module selector
is the dunder without its underscores (`__add__` is `add`), and the augmented
form is that selector with an `i` in front (`iadd`), which is Python's own rule
for both [source: https://docs.python.org/3/library/operator.html].

Guarantees:
  - all 22 supported, reserved, provided, templated, or refused Python
    operators have one entry and no runtime remapping hook [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=613f35974fa98746552dba584ad66082fdd1f3c7]
  - all four rich-comparison entries are reserved for atom ordering rather
    than term construction [tested: test_atom_comparisons_are_only_ordering;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - every projection this table publishes -- by selector, by `ast` node, the
    word door, the exactly-numeric heads and the augmented forms -- is derived
    from these rows rather than restated
    [tested: test_every_operator_projection_is_this_table; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
Decides:
  - ``@`` always lowers to the library-provided name ``matmul``; libraries
    define that MeTTa name rather than remapping Python syntax [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=613f35974fa98746552dba584ad66082fdd1f3c7]
  - `word` marks the rows whose `operator`-module name is a public door, which
    `S.add` reaches. It is a curation rather than every row: the spellings
    that door admits are settled one at a time, and `floordiv`'s composite
    image is the one that is not
    [source: extensions/python/metta/_atoms/names.py:81, _COMPOSITE_OPERATOR_IMAGES; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Final, Literal, NamedTuple

# policy-inventory-exempt: mechanism-internal; reason=these four names are the lowering table's own entry kinds, read only by the apply and method paths that walk the table; evidence=extensions/python/metta/_atoms/operators.py:OperatorLowering
LoweringKind = Literal["symbol", "template", "taken", "provided"]
LoweringForm = str | int | tuple[Any, ...]


class OperatorLowering(NamedTuple):
    """One stable Python spelling and every form that one operator denotes.

    `dunder` is Python's protocol name and `syntax` how an author writes it.
    `kind` and `form` are what the atom surface builds; `method` is the atom
    method a `taken` spelling keeps for itself. `node` is the `ast` class the
    compiler dispatches on, `native` the MeTTa head an exactly-numeric operand
    pair may use instead of the protocol path, and `word` whether the
    `operator`-module name is a public door.

    `word_head` is the head that door reaches when it is NOT the form, which
    is one row: `x != y` on atoms builds `(not (== x y))`, because Python's
    `!=` has to answer a bool, while `S.ne` names the engine's own `!=` head.
    Every other door reaches its row's form, so nothing spells it twice.

    The selector and the augmented selector are DERIVED, by `selector()` and
    `augmented()`, because Python derives them the same way.
    """

    dunder: str
    reflected: str | None
    syntax: str
    kind: LoweringKind
    form: LoweringForm | None
    method: str | None = None
    # policy-inventory-exempt: mechanism-internal; reason=Python's operator protocol has only unary and binary dunders, so this is the table entry's own arity field; evidence=extensions/python/metta/_atoms/operators.py:OperatorLowering
    arity: Literal[1, 2] = 2
    node: str | None = None
    native: str | None = None
    word: bool = False
    word_head: str | None = None
    augmented: bool = False


def selector(entry: OperatorLowering) -> str:
    """The `operator`-module name of one row: `__add__` is `add`.

    Python's own rule, applied rather than restated: the protocol name without
    its underscores IS the function's name in `operator`, `and_`, `or_` and
    `not_`'s trailing underscore excepted, which is a keyword escape rather
    than a different name
    [source: https://docs.python.org/3/library/operator.html].
    """
    return entry.dunder.strip("_")


def augmented_selector(entry: OperatorLowering) -> str:
    """The augmented form's name: `add` is `iadd`, Python's own rule."""
    return f"i{selector(entry)}"


# closed-set: decides; policy=how every Python operator spells in MeTTa, which is the ONE table every other spelling of that relation is a projection of; reads=none, it is the source
OPERATOR_LOWERINGS: tuple[OperatorLowering, ...] = (
    OperatorLowering(
        "__add__", "__radd__", "x + y", "symbol", "+", node="Add", native="+", word=True, augmented=True
    ),
    OperatorLowering(
        "__sub__", "__rsub__", "x - y", "symbol", "-", node="Sub", native="-", word=True, augmented=True
    ),
    OperatorLowering(
        "__mul__", "__rmul__", "x * y", "symbol", "*", node="Mult", native="*", word=True, augmented=True
    ),
    OperatorLowering(
        "__truediv__", "__rtruediv__", "x / y", "symbol", "/", node="Div", native="/", word=True, augmented=True
    ),
    OperatorLowering(
        "__floordiv__",
        "__rfloordiv__",
        "x // y",
        "template",
        ("floor-math", ("/", "$left", "$right")),
        node="FloorDiv",
        native="floor-div",
        augmented=True,
    ),
    OperatorLowering(
        "__mod__", "__rmod__", "x % y", "symbol", "%", node="Mod", native="%", word=True, augmented=True
    ),
    OperatorLowering(
        "__pow__", "__rpow__", "x ** y", "symbol", "pow-math", node="Pow", word=True, augmented=True
    ),
    OperatorLowering(
        "__matmul__", "__rmatmul__", "x @ y", "provided", "matmul",
        node="MatMult", augmented=True,
    ),
    # `bit-shift-left` rather than a `-math` name: that suffix marks this
    # engine's C math.h family over binary64, and shift is exact and
    # integer-only. The `bit-` prefix is Clojure's spelling and is load-bearing
    # HERE, because `and`, `or` and `xor` below are BOOLEAN in MeTTa, so
    # without it nothing tells a reader which family a bitwise operation joined.
    OperatorLowering(
        "__lshift__", "__rlshift__", "x << y", "symbol", "bit-shift-left",
        node="LShift", augmented=True,
    ),
    OperatorLowering(
        "__rshift__", "__rrshift__", "x >> y", "symbol", "bit-shift-right",
        node="RShift", augmented=True,
    ),
    OperatorLowering(
        "__and__", "__rand__", "x & y", "symbol", "and", node="BitAnd", augmented=True
    ),
    OperatorLowering(
        "__or__", "__ror__", "x | y", "symbol", "or", node="BitOr", augmented=True
    ),
    OperatorLowering(
        "__xor__", "__rxor__", "x ^ y", "symbol", "xor", node="BitXor", augmented=True
    ),
    OperatorLowering(
        "__lt__", None, "x < y", "taken", "<", method="order_key",
        node="Lt", native="<", word=True,
    ),
    OperatorLowering(
        "__le__", None, "x <= y", "taken", "<=", method="order_key",
        node="LtE", native="<=", word=True,
    ),
    OperatorLowering(
        "__gt__", None, "x > y", "taken", ">", method="order_key",
        node="Gt", native=">", word=True,
    ),
    OperatorLowering(
        "__ge__", None, "x >= y", "taken", ">=", method="order_key",
        node="GtE", native=">=", word=True,
    ),
    OperatorLowering("__invert__", None, "~x", "symbol", "not", arity=1, node="Invert"),
    OperatorLowering(
        "__neg__", None, "-x", "template", ("-", 0, "$value"), arity=1,
        node="USub", word=True,
    ),
    OperatorLowering("__abs__", None, "abs(x)", "symbol", "abs-math", arity=1),
    OperatorLowering("__floor__", None, "math.floor(x)", "symbol", "floor-math", arity=1),
    OperatorLowering("__ceil__", None, "math.ceil(x)", "symbol", "ceil-math", arity=1),
    OperatorLowering("__trunc__", None, "math.trunc(x)", "symbol", "trunc-math", arity=1),
    OperatorLowering("__round__", None, "round(x)", "symbol", "round-math", arity=1),
    OperatorLowering(
        "__eq__", None, "x == y", "taken", "==", method="eq", node="Eq", word=True,
    ),
    OperatorLowering(
        "__ne__",
        None,
        "x != y",
        "taken",
        ("not", ("==", "$left", "$right")),
        method="ne",
        node="NotEq",
        word=True,
        word_head="!=",
    ),
)


#: One row per `operator`-module selector, which is the key the runtime
#: dispatch and the word door both use.
BY_SELECTOR: Final[_collections_abc.Mapping[str, OperatorLowering]] = MappingProxyType(
    {selector(entry): entry for entry in OPERATOR_LOWERINGS}
)

#: One row per `ast` node CLASS NAME, which is the key the compiler dispatches
#: on. The name rather than the class, so this module imports no `ast`: the
#: compiler resolves it with `getattr(ast, name)` where it already has it, and
#: a table read at package import stays free of a 400 KB stdlib module.
BY_NODE: Final[_collections_abc.Mapping[str, OperatorLowering]] = MappingProxyType(
    {entry.node: entry for entry in OPERATOR_LOWERINGS if entry.node is not None}
)


def selectors(*, augmented: bool = False) -> tuple[str, ...]:
    """Every selector this table names, or every AUGMENTED one.

    `x += y` reaches `operator.iadd`, and which operators have an augmented
    form is Python's own answer rather than a list: the thirteen that do are
    the rows marked so.
    """
    return tuple(
        augmented_selector(entry) if augmented else selector(entry)
        for entry in OPERATOR_LOWERINGS
        if entry.augmented or not augmented
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


__all__ = [
    "BY_NODE",
    "BY_SELECTOR",
    "OPERATOR_LOWERINGS",
    "LoweringKind",
    "OperatorLowering",
    "augmented_selector",
    "selector",
    "selectors",
]

# Resolve annotations after definitions so peer imports can finish.
import collections.abc as _collections_abc  # noqa: E402 -- deferred annotation bindings
