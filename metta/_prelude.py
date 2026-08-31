"""Purpose: the runtime-backed operations compiled Python lowers to when no
engine function carries the exact Python semantics: truthiness, equality,
text building, membership, banker's rounding, range, slicing, and the
mettafied exception vocabulary behind a compiled try — `except`, the
class-lattice test over MRO names, and `error-payload`, the live instance
an error atom carries or describes. Each one is the Python behavior
itself, so the compiled equations and the Python twin cannot disagree; a
Defined lists the ones it leans on as runtime_ops, so the dependency on
this runtime is visible rather than ambient.
Guarantees:
  - runtime operations receive evaluated Atom wrappers through matchable
    `(arguments name atoms)` policies instead of a boolean registration flag
    [tested: test_fstrings_str_round_range_slices,
    test_mixed_numeric_equality_and_membership;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the internal prelude publishes those policies in &metta without leaking
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

import builtins
import functools
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
    "py-global-read",
    "py-global-write",
    "except",
    "error-payload",
)

# The compiler's spelling for an absent slice bound; never user-visible.
_NO_BOUND = Symbol("py-no-bound")

# What a reified engine error means in Python's exception lattice. The
# functor rows are SWI's ISO error terms as `catch` reifies them,
# (Error (type_error ...) context); the symbol rows are the engine's own
# error-data reasons from the he algebra, (Error culprit BadType). A
# compiled `except ZeroDivisionError` must catch the engine's zero divide
# exactly as Python's would, and `except Exception` catches every error.
_ENGINE_ERROR_FUNCTORS: dict[str, type[BaseException]] = {
    "type_error": TypeError,
    "domain_error": ValueError,
    "existence_error": NameError,
    "instantiation_error": TypeError,
    "resource_error": RecursionError,
    "representation_error": OverflowError,
    "permission_error": PermissionError,
    "syntax_error": SyntaxError,
}

_ENGINE_ERROR_SYMBOLS: dict[str, type[BaseException]] = {
    "BadType": TypeError,
    "BadArgType": TypeError,
    "AssertionError": AssertionError,
    "DivisionByZero": ZeroDivisionError,
    "zero_divisor": ZeroDivisionError,
}


def _named_exception(name: str) -> type[BaseException] | str:
    """A class for an exception NAME: the explicit map, then the builtin
    exception zoo, then the bare name itself, which py-except-match
    compares against the arm's own class names, so a custom class raised
    across a host crossing is still caught by the arm that spells it.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    mapped = _ENGINE_ERROR_SYMBOLS.get(name)
    if mapped is not None:
        return mapped
    built = getattr(builtins, name, None)
    if isinstance(built, type) and issubclass(built, BaseException):
        return built
    return name


def _functor_class(
    head: str, child: Expression
) -> type[BaseException] | str | None:
    """The exception a classifiable error functor names, else None.

    evaluation_error reads its reason parts and python_error its reified
    class name; then the engine functor map; then constructor data, where
    a capitalized head IS the kind: a compiled raise produces the term
    (ValueError "why"), and an unresolvable capitalized head matches arms
    by its name. `Error` itself is the algebra's wrapper, never a kind: a
    strict position rewraps an error it meets (BadArgType around a
    DivisionByZero), and the caller's recursion finds the ORIGINAL, which
    is the one Python would propagate.
    """
    if head == "evaluation_error":
        parts = child.children[1:]
        if any(isinstance(part, Symbol) and part.name == "zero_divisor" for part in parts):
            return ZeroDivisionError
        return ArithmeticError
    if head == "python_error":
        for part in child.children[1:]:
            if isinstance(part, Symbol):
                return _named_exception(part.name)
        return None
    mapped = _ENGINE_ERROR_FUNCTORS.get(head)
    if mapped is not None:
        return mapped
    if head[:1].isupper() and head != "Error":
        return _named_exception(head)
    return None


def _error_class(error: Any) -> BaseException | type[BaseException] | str | None:
    """The Python exception an (Error ...) atom stands for, if any.

    An error atom carries its classifiable part in no fixed slot: the he
    algebra writes (Error culprit reason), catch reifies a host exception
    as (Error type context), a host crossing reifies as
    (python_error Name message), and a compiled `raise` produces the
    grounded instance itself. Scanning the children finds whichever
    arrived: a live BaseException wins, then an error functor, then a
    reason symbol. Nothing classifiable means the payload is MeTTa's own
    data, which only the Exception and BaseException arms may catch.
    """
    if not isinstance(error, Expression):
        return None
    for child in error.children[1:]:
        if isinstance(child, Grounded) and isinstance(child.value, BaseException):
            return child.value
        if isinstance(child, Expression) and child.children:
            head = child.children[0]
            if isinstance(head, Symbol):
                named = _functor_class(head.name, child)
                if named is not None:
                    return named
            nested = _error_class(child)
            if nested is not None:
                return nested
        if isinstance(child, Symbol):
            mapped = _ENGINE_ERROR_SYMBOLS.get(child.name)
            if mapped is not None:
                return mapped
    return None


def _described_exception(error: Any) -> tuple[str | None, str | None]:
    """The (name, message) an error atom describes without carrying: a
    (python_error Name "message") reification, or raised constructor data
    (ValueError "why").
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if not isinstance(error, Expression):
        return None, None
    for child in error.children[1:]:
        if isinstance(child, Expression) and child.children:
            head = child.children[0]
            if isinstance(head, Symbol) and (
                head.name == "python_error" or head.name[:1].isupper()
            ):
                name = (
                    head.name
                    if head.name != "python_error"
                    else next(
                        (
                            part.name
                            for part in child.children[1:]
                            if isinstance(part, Symbol)
                        ),
                        None,
                    )
                )
                message = next(
                    (
                        part.value
                        for part in child.children[1:]
                        if isinstance(part, Grounded) and isinstance(part.value, str)
                    ),
                    None,
                )
                if name is not None:
                    return name, message
            nested = _described_exception(child)
            if nested[0] is not None:
                return nested
    return None, None


def _error_instance(error: Any) -> BaseException | None:
    """The live exception an error atom carries or describes, if any.

    A grounded instance answers itself; a described one reconstructs
    Name(message) when the name resolves to a class, so a handler's
    ``as e`` holds something whose str() reads as Python's would. An
    atom describing nothing stays an atom.
    """
    kind = _error_class(error)
    if isinstance(kind, BaseException):
        return kind
    name, message = _described_exception(error)
    resolved: type[BaseException] | str | None = (
        _named_exception(name) if name is not None else kind
    )
    if not isinstance(resolved, type):
        return None
    try:
        return resolved(message) if message is not None else resolved()
    except Exception:  # noqa: BLE001  -- a custom constructor signature refuses reconstruction; the atom stands
        return None


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


def _carried_error(operands: tuple[Any, ...]) -> Expression | None:
    """The first (Error ...) operand, which the operation must pass through.

    The engine's own strict positions propagate error data railway-style: an
    Error operand refuses onward rather than computing. The prelude's
    boolean, arithmetic and container operations are the strict positions of
    compiled Python, so they follow the same law; without it, an error
    reaching a compiled `if` test would read as a truthy tuple and take a
    branch Python's own raise would have skipped. The text operations stay
    exempt: printing an error a handler holds is legitimate consumption.
    """
    for operand in operands:
        if (
            isinstance(operand, Expression)
            and operand.children
            and operand.children[0] == Symbol("Error")
        ):
            return operand
    return None


def _railway(operation: Callable[..., Any]) -> Callable[..., Any]:
    # functools.wraps carries the original signature through __wrapped__,
    # which is what the registrar's arity reader inspects.
    @functools.wraps(operation)
    def carried(*operands: Any) -> Any:
        error = _carried_error(operands)
        if error is not None:
            return error
        return operation(*operands)

    return carried


def install(runtime) -> None:
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

    # A declared-global read against the definition module's own dict. The
    # dict crossed as a grounded reference when the function compiled, so
    # this reads the live module whichever Python context the engine's
    # callbacks run in; an island's globals() can be a replica there. A
    # missing name raises Python's own NameError. Comments, not docstrings:
    # helper prose must not become an @doc atom in every program space.
    def py_global_read(store, key):
        bindings = pythonic(store)
        name = pythonic(key)
        try:
            return bindings[name]
        except KeyError:
            msg = f"name {name!r} is not defined"
            raise NameError(msg) from None

    def py_global_write(store, key, value):
        pythonic(store)[pythonic(key)] = pythonic(value)
        return True

    # `(except $err Kind)`: the mettafied class test, on NAMES. The arm's
    # classinfo is the class's own name as a symbol (or an expression of
    # them), so the equation is data; the lattice is walked by MRO NAMES,
    # so a custom hierarchy matches exactly as Python's isinstance would,
    # without the class object crossing.
    def except_matches(error, classinfo):
        names = classinfo
        if isinstance(names, Expression):
            wanted = [child.name for child in names.children if isinstance(child, Symbol)]
        elif isinstance(names, Symbol):
            wanted = [names.name]
        else:
            wanted = [str(pythonic(names))]
        kind = _error_class(error)
        lattice: tuple[str, ...]
        if isinstance(kind, BaseException):
            lattice = tuple(cls.__name__ for cls in type(kind).__mro__)
        elif isinstance(kind, type):
            lattice = tuple(cls.__name__ for cls in kind.__mro__)
        elif isinstance(kind, str):
            resolved = getattr(builtins, kind, None)
            if isinstance(resolved, type) and issubclass(resolved, BaseException):
                lattice = tuple(cls.__name__ for cls in resolved.__mro__)
            else:
                lattice = (kind, "Exception", "BaseException")
        else:
            # MeTTa's own thrown data classifies as an error, nothing more.
            lattice = ("Exception", "BaseException")
        return any(name in lattice for name in wanted)

    def error_payload(error):
        instance = _error_instance(error)
        return error if instance is None else instance

    # register is typed as the identity it is, so the table has to say its
    # element type or a checker picks the first function's signature and
    # rejects the other eleven for not having it. A list rather than a tuple
    # because ty keeps a tuple literal's precise heterogeneous type and
    # ignores the declaration; the list form both checkers honour.
    # The strict rows carry the railway guard; the text rows and the
    # except family consume error atoms deliberately and stay bare.
    prelude: list[tuple[Callable[..., Any], str, list[int] | None]] = [
        (_railway(py_truthy), "py-truthy", None),
        (_railway(py_eq), "py-eq", None),
        (py_str, "py-str", None),
        (py_repr, "py-repr", None),
        (py_format, "py-format", None),
        (py_str_join, "py-str-join", None),
        (_railway(py_in), "py-in", None),
        (_railway(py_len), "py-len", None),
        (_railway(py_round), "py-round", None),
        (_railway(py_range), "py-range", [1, 2, 3]),
        (_railway(py_at), "py-at", None),
        (_railway(py_slice), "py-slice", None),
        (py_global_read, "py-global-read", None),
        (py_global_write, "py-global-write", None),
        (except_matches, "except", None),
        (error_payload, "error-payload", None),
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
    runtime.must("spaces:metta_publish_builtin_visibility")
