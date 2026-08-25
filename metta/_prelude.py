"""Purpose: the runtime-backed operations compiled Python lowers to when no
engine function carries the exact Python semantics: truthiness, equality,
text building, membership, banker's rounding, range and slicing. Each one
is the Python behavior itself, so the compiled equations and the Python
twin cannot disagree; a Defined lists the ones it leans on as runtime_ops,
so the dependency on this runtime is visible rather than ambient.
Guarantees:
  - runtime operations receive evaluated Atom wrappers through matchable
    `(arguments name atoms)` policies instead of a boolean registration flag
    [tested: test_fstrings_str_round_range_slices,
    test_mixed_numeric_equality_and_membership;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the internal prelude publishes those policies in &petta without leaking
    implementation annotations or helper documentation into &self [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the shipped Python-only operations receive catalog visibility after the
    registration batch, so public-surface generators see the complete runtime
    inventory [tested: test_internal_catalog_names_stay_exact_but_leave_public_outputs;
    commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import ops as _ops_module
from ._api_types import _OperationName
from .atoms import Expression, Grounded, S, Symbol, _expr

__all__ = ["NAMES", "install", "pythonic"]

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
_NO_BOUND = Symbol("py-no-bound")


def pythonic(value: Any) -> Any:
    """An atom as the Python value the twin computes with: grounded values
    unwrap, expressions become tuples, a symbol stays itself (the twin
    cannot hold one, and hazard tracking keeps it out of twin paths).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Grounded):
        return value.value
    if isinstance(value, Expression):
        return tuple(pythonic(c) for c in value)
    return value


def install(runtime) -> None:  # noqa: C901  -- install keeps the prelude registration table together so its branches share one state
    """Register the prelude on the shared engine, once per process."""

    def _subscript(value, key, what):
        """One subscript, with an error that names the type rather than the
        repr. A million-element array printed into a TypeError is not a
        message anybody reads.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        try:
            return value[key]
        except TypeError as exc:
            msg = (
                f"a {type(value).__name__} cannot be {what}ed by "
                f"{type(key).__name__}"
            )
            raise TypeError(
                msg
            ) from exc
        except (KeyError, IndexError) as exc:
            msg = f"{key!r} is not in this {type(value).__name__}"
            raise type(exc)(
                msg
            ) from exc

    def py_truthy(value):
        return bool(pythonic(value))

    def py_eq(a, b):
        return pythonic(a) == pythonic(b)

    def py_str(value):
        v = pythonic(value)
        return v.name if isinstance(v, Symbol) else str(v)

    def py_repr(value):
        v = pythonic(value)
        return v.name if isinstance(v, Symbol) else repr(v)

    def py_format(value, spec):
        return format(pythonic(value), pythonic(spec))

    def py_str_join(parts):
        return "".join(
            p.name if isinstance(p, Symbol) else str(p) for p in (pythonic(c) for c in parts)
        )

    def py_in(item, container):
        return pythonic(item) in pythonic(container)

    def py_len(value):
        return len(pythonic(value))

    def py_round(value, digits=None):
        if digits is None:
            return round(pythonic(value))
        return round(pythonic(value), pythonic(digits))

    def py_range(*bounds):
        return Expression([Grounded(i) for i in range(*(pythonic(b) for b in bounds))])

    # Index anything Python can index, plus a MeTTa expression. `py-call`
    # hands back objects themselves, so Python owns every non-Expression subscript.
    # Keep this as a comment: internal helper prose is not a user declaration
    # and must not become an @doc atom in every program space.
    def py_at(sequence, index):
        i = pythonic(index)
        if isinstance(sequence, Expression):
            return sequence.children[i]
        return _subscript(pythonic(sequence), i, "index")

    def py_slice(sequence, start, stop):
        lower = None if start == _NO_BOUND else pythonic(start)
        upper = None if stop == _NO_BOUND else pythonic(stop)
        if isinstance(sequence, Expression):
            return Expression(list(sequence.children[lower:upper]))
        return _subscript(pythonic(sequence), slice(lower, upper), "slice")

    # register is typed as the identity it is, so the table has to say its
    # element type or a checker picks the first function's signature and
    # rejects the other eleven for not having it. A list rather than a tuple
    # because ty keeps a tuple literal's precise heterogeneous type and
    # ignores the declaration; the list form both checkers honour.
    prelude: list[tuple[Callable[..., Any], str, list[int] | None]] = [
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
    ]
    for fn, name, arities in prelude:
        _ops_module.register(
            runtime,
            fn,
            name=_OperationName(name),
            effect="oracleIO",
            declarations=[_expr(S.arguments, S[name], S.atoms)],
            arities=arities,
        )
    runtime.must("spaces:petta_publish_builtin_visibility")
