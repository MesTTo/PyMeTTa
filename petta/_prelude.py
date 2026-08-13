"""Purpose: the runtime-backed operations compiled Python lowers to when no
engine function carries the exact Python semantics: truthiness, equality,
text building, membership, banker's rounding, range and slicing. Each one
is the Python behavior itself, so the compiled equations and the Python
twin cannot disagree; a Defined lists the ones it leans on as runtime_ops,
so the dependency on this runtime is visible rather than ambient.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from .atoms import Expr, Gnd, Sym, Var

__all__ = ["install", "NAMES", "pythonic"]

NAMES = (
    "py-truthy",
    "py-eq",
    "py-str",
    "py-repr",
    "py-format",
    "py-str-join",
    "py-in",
    "py-len",
    "py-round",
    "py-range",
    "py-at",
    "py-slice",
)

# The compiler's spelling for an absent slice bound; never user-visible.
_NO_BOUND = Sym("py-no-bound")


def pythonic(value: Any) -> Any:
    """An atom as the Python value the twin computes with: grounded values
    unwrap, expressions become tuples, a symbol stays itself (the twin
    cannot hold one, and hazard tracking keeps it out of twin paths)."""
    if isinstance(value, Gnd):
        return value.value
    if isinstance(value, Expr):
        return tuple(pythonic(c) for c in value)
    return value


def install(runtime) -> None:
    """Register the prelude on the shared engine, once per process."""

    def py_truthy(value) -> bool:
        return bool(pythonic(value))

    def py_eq(a, b) -> bool:
        return pythonic(a) == pythonic(b)

    def py_str(value) -> str:
        v = pythonic(value)
        return v.name if isinstance(v, Sym) else str(v)

    def py_repr(value) -> str:
        v = pythonic(value)
        return v.name if isinstance(v, Sym) else repr(v)

    def py_format(value, spec) -> str:
        return format(pythonic(value), pythonic(spec))

    def py_str_join(parts) -> str:
        return "".join(
            p.name if isinstance(p, Sym) else str(p)
            for p in (pythonic(c) for c in parts)
        )

    def py_in(item, container) -> bool:
        return pythonic(item) in pythonic(container)

    def py_len(value) -> int:
        return len(pythonic(value))

    def py_round(value, digits=None):
        if digits is None:
            return round(pythonic(value))
        return round(pythonic(value), pythonic(digits))

    def py_range(*bounds):
        return Expr([Gnd(i) for i in range(*(pythonic(b) for b in bounds))])

    def py_at(sequence, index):
        i = pythonic(index)
        if isinstance(sequence, Expr):
            return sequence.children[i]
        v = pythonic(sequence)
        if isinstance(v, str):
            return v[i]
        raise TypeError(f"{v!r} is not indexable")

    def py_slice(sequence, start, stop):
        lower = None if start == _NO_BOUND else pythonic(start)
        upper = None if stop == _NO_BOUND else pythonic(stop)
        if isinstance(sequence, Expr):
            return Expr(list(sequence.children[lower:upper]))
        v = pythonic(sequence)
        if isinstance(v, str):
            return v[lower:upper]
        raise TypeError(f"{v!r} is not sliceable")

    from . import ops as _ops_module

    for fn, name, arities in (
        (py_truthy, "py-truthy", None),
        (py_eq, "py-eq", None),
        (py_str, "py-str", None),
        (py_repr, "py-repr", None),
        (py_format, "py-format", None),
        (py_str_join, "py-str-join", None),
        (py_in, "py-in", None),
        (py_len, "py-len", None),
        (py_round, "py-round", None),
        (py_range, "py-range", [1, 2, 3]),
        (py_at, "py-at", None),
        (py_slice, "py-slice", None),
    ):
        _ops_module.register(
            runtime, fn, name=name, typed=False, pass_atoms=True, arities=arities
        )
