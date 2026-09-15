"""Purpose: join Python's generated operator facts to their MeTTa meanings.

Assumes: tools/protocolgen.py has checked the locked CPython source inventory.
Guarantees: protocol names, reflected and augmented partners, callable shapes
and AST forms come from that inventory; atom, compiler and word projections
read the same joined rows [source:
extensions/python/tools/protocolgen.py:operator_rows; commit=f866cc992295171a9a9e97417514f31597181e7b].
Decides: atom images, reserved methods, exact numeric heads and public operator
words are MeTTa policy. They are written once in _POLICIES. A callable's full
Python signature remains distinct from an atom image's minimum operand count.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final, Literal, NamedTuple

from metta._atoms._python_protocols import BY_OPERATOR, PythonOperator

# policy-inventory-exempt: mechanism-internal; reason=these are the atom image shapes consumed by the existing method emitter; evidence=extensions/python/metta/_atoms/model.py:_operator_method
LoweringKind = Literal["symbol", "template", "taken", "provided"]
LoweringForm = str | int | tuple[Any, ...]


class AtomPolicy(NamedTuple):
    """The choices Python's source cannot make for a MeTTa atom."""

    kind: LoweringKind
    form: LoweringForm
    method: str | None = None
    native: str | None = None
    word: bool = False
    word_head: str | None = None


class OperatorLowering(NamedTuple):
    """A source operation and its atom policy, exposed through derived views."""

    source: PythonOperator
    policy: AtomPolicy

    @property
    def dunder(self) -> str:
        """Python's special method for the source operation."""
        return self.source.member[1]

    @property
    def reflected(self) -> str | None:
        """The right operand's paired method, when the protocol has one."""
        return self.source.reflected[1] if self.source.reflected is not None else None

    @property
    def syntax(self) -> str:
        """The Python source form recorded by the inventory."""
        return self.source.syntax

    @property
    def arity(self) -> int:
        """The operand count of the atom image's source form."""
        return self.source.arity

    @property
    def node(self) -> str | None:
        """The AST operator class name, when syntax has a dedicated node."""
        return self.source.node

    @property
    def augmented(self) -> bool:
        """Whether the source operation has an in-place counterpart."""
        return self.source.inplace is not None

    @property
    def kind(self) -> LoweringKind:
        """The existing atom emitter shape selected by MeTTa policy."""
        return self.policy.kind

    @property
    def form(self) -> LoweringForm:
        """The native head or expression template built by the atom surface."""
        return self.policy.form

    @property
    def method(self) -> str | None:
        """The reserved atom method used by a taken Python spelling."""
        return self.policy.method

    @property
    def native(self) -> str | None:
        """The native head admitted for operands proven exactly numeric."""
        return self.policy.native

    @property
    def word(self) -> bool:
        """Whether the operation supplies a public symbol-factory word."""
        return self.policy.word

    @property
    def word_head(self) -> str | None:
        """The public word's head when it differs from the atom image."""
        return self.policy.word_head


# closed-set: decides; policy=the MeTTa image and reserved atom behavior of each supported Python operation; reads=extensions/python/metta/_atoms/_python_protocols.py:BY_OPERATOR supplies all Python facts
_POLICIES: Final[Mapping[str, AtomPolicy]] = MappingProxyType({
    "__add__": AtomPolicy("symbol", "+", native="+", word=True),
    "__sub__": AtomPolicy("symbol", "-", native="-", word=True),
    "__mul__": AtomPolicy("symbol", "*", native="*", word=True),
    "__truediv__": AtomPolicy("symbol", "/", native="/", word=True),
    "__floordiv__": AtomPolicy("template", ("floor-math", ("/", "$left", "$right")), native="floor-div"),
    "__mod__": AtomPolicy("symbol", "%", native="%", word=True),
    "__pow__": AtomPolicy("symbol", "pow-math", word=True),
    "__matmul__": AtomPolicy("provided", "matmul"),
    # MeTTa's and/or/xor heads are Boolean; the bit prefix distinguishes shifts.
    "__lshift__": AtomPolicy("symbol", "bit-shift-left"),
    "__rshift__": AtomPolicy("symbol", "bit-shift-right"),
    "__and__": AtomPolicy("symbol", "and"),
    "__or__": AtomPolicy("symbol", "or"),
    "__xor__": AtomPolicy("symbol", "xor"),
    "__lt__": AtomPolicy("taken", "<", method="order_key", native="<", word=True),
    "__le__": AtomPolicy("taken", "<=", method="order_key", native="<=", word=True),
    "__gt__": AtomPolicy("taken", ">", method="order_key", native=">", word=True),
    "__ge__": AtomPolicy("taken", ">=", method="order_key", native=">=", word=True),
    "__invert__": AtomPolicy("symbol", "not"),
    "__neg__": AtomPolicy("template", ("-", 0, "$value"), word=True),
    "__abs__": AtomPolicy("symbol", "abs-math"),
    "__floor__": AtomPolicy("symbol", "floor-math"),
    "__ceil__": AtomPolicy("symbol", "ceil-math"),
    "__trunc__": AtomPolicy("symbol", "trunc-math"),
    "__round__": AtomPolicy("symbol", "round-math"),
    "__eq__": AtomPolicy("taken", "==", method="eq", word=True),
    "__ne__": AtomPolicy("taken", ("not", ("==", "$left", "$right")), method="ne", word=True, word_head="!="),
})

OPERATOR_LOWERINGS: Final[tuple[OperatorLowering, ...]] = tuple(
    OperatorLowering(BY_OPERATOR[("object", name)], policy)
    for name, policy in _POLICIES.items()
)


def selector(entry: OperatorLowering) -> str:
    """The public word derived from the exact source callable alias."""
    return entry.source.selector


def augmented_selector(entry: OperatorLowering) -> str:
    """The in-place callable joined through its source AST and slot role."""
    if entry.source.inplace_selector is None:
        msg = f"{entry.dunder} has no augmented source form"
        raise ValueError(msg)
    return entry.source.inplace_selector


BY_SELECTOR: Final[Mapping[str, OperatorLowering]] = MappingProxyType({
    selector(entry): entry for entry in OPERATOR_LOWERINGS
})
BY_NODE: Final[Mapping[str, OperatorLowering]] = MappingProxyType({
    entry.node: entry for entry in OPERATOR_LOWERINGS if entry.node is not None
})


def selectors(*, augmented: bool = False) -> tuple[str, ...]:
    """Project ordinary or in-place source selectors from the policy join."""
    return tuple(
        augmented_selector(entry) if augmented else selector(entry)
        for entry in OPERATOR_LOWERINGS
        if entry.augmented or not augmented
    )


def _validate_operator_lowerings() -> None:
    reflected = [entry.reflected for entry in OPERATOR_LOWERINGS if entry.reflected]
    if len(reflected) != len(set(reflected)):
        msg = "the operator policy join contains a duplicate reflected member"
        raise RuntimeError(msg)
    for entry in OPERATOR_LOWERINGS:
        if (entry.kind == "taken") != (entry.method is not None):
            msg = f"incomplete operator lowering entry: {entry.dunder}"
            raise RuntimeError(msg)
        if entry.arity not in (1, 2) or (entry.arity == 1 and entry.reflected is not None):
            msg = f"atom method emitter cannot represent the source shape for {entry.dunder}"
            raise RuntimeError(msg)


_validate_operator_lowerings()

__all__ = [
    "BY_NODE", "BY_SELECTOR", "OPERATOR_LOWERINGS", "LoweringKind",
    "OperatorLowering", "augmented_selector", "selector", "selectors",
]
