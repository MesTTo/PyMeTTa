"""Purpose: the runtime-backed operations compiled Python lowers to when no
engine function carries the exact Python semantics: truthiness, equality,
text building, membership, banker's rounding, range, slicing, and the
operator data model used by compiled Python expressions, and the
mettafied exception vocabulary behind a compiled try — `except`, the
live class-identity and inheritance test, and `error-payload`, the live instance
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
  - compiled exception dispatch compares live exception classes by identity
    and inheritance [tested:
    test_compiled_except_uses_exception_class_identity_not_bare_name;
    commit=e7919ef660e1c2b31a307187c0237823daccdbd4]
  - compiled operators invoke the corresponding Python protocol exactly once
    and preserve set/dict space images at their boundary [tested:
    test_compiled_operators_follow_python_protocols_and_result_species;
    commit=e3787593132a7ece2d300397045f7415709847c9]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import builtins
import functools
import operator
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
    "py-operator",
    "py-set",
    "py-set-pairs",
    "py-dict-pairs",
    "py-container-kind",
    "except",
    "error-payload",
)

# The compiler's spelling for an absent slice bound; never user-visible.
_NO_BOUND = Symbol("py-no-bound")

_PYTHON_OPERATORS: dict[str, Callable[..., Any]] = {
    "abs": operator.abs,
    "add": operator.add,
    "and": operator.and_,
    "eq": operator.eq,
    "floordiv": operator.floordiv,
    "ge": operator.ge,
    "gt": operator.gt,
    "iadd": operator.iadd,
    "iand": operator.iand,
    "ifloordiv": operator.ifloordiv,
    "ilshift": operator.ilshift,
    "imatmul": operator.imatmul,
    "imod": operator.imod,
    "imul": operator.imul,
    "invert": operator.invert,
    "ior": operator.ior,
    "ipow": operator.ipow,
    "irshift": operator.irshift,
    "isub": operator.isub,
    "itruediv": operator.itruediv,
    "ixor": operator.ixor,
    "le": operator.le,
    "lshift": operator.lshift,
    "lt": operator.lt,
    "matmul": operator.matmul,
    "max": builtins.max,
    "min": builtins.min,
    "mod": operator.mod,
    "mul": operator.mul,
    "ne": operator.ne,
    "neg": operator.neg,
    "or": operator.or_,
    "pos": operator.pos,
    "pow": operator.pow,
    "rshift": operator.rshift,
    "sorted": builtins.sorted,
    "sub": operator.sub,
    "sum": builtins.sum,
    "truediv": operator.truediv,
    "xor": operator.xor,
}

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
) -> BaseException | type[BaseException] | str | None:
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
            if isinstance(part, Grounded) and isinstance(part.value, BaseException):
                return part.value
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
                        (part.name for part in child.children[1:] if isinstance(part, Symbol)),
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


def _exception_targets(
    classinfo: Any,
) -> tuple[tuple[type[BaseException], ...], tuple[str, ...]]:
    """Live classes plus legacy symbolic names from one except arm."""
    classes: list[type[BaseException]] = []
    names: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, Expression):
            for child in value.children:
                collect(child)
            return
        candidate = value.value if isinstance(value, Grounded) else value
        if isinstance(candidate, tuple):
            for member in candidate:
                collect(member)
            return
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            classes.append(candidate)
            return
        name = candidate.name if isinstance(candidate, Symbol) else str(pythonic(candidate))
        built = getattr(builtins, name, None)
        if isinstance(built, type) and issubclass(built, BaseException):
            classes.append(built)
        else:
            names.append(name)

    collect(classinfo)
    return tuple(classes), tuple(names)


# Invoke one compiler-selected function from Python's operator module. This is
# a comment because internal prelude prose must not become a public @doc atom.
def _py_operator(selector, *operands):
    if not isinstance(selector, Symbol) or selector.name not in _PYTHON_OPERATORS:
        msg = f"unknown compiled Python operator selector: {selector!r}"
        raise ValueError(msg)
    error = _carried_error(operands)
    if error is not None:
        return error
    operation = _PYTHON_OPERATORS[selector.name]
    try:
        return operation(*(pythonic(operand) for operand in operands))
    except Exception as error:  # noqa: BLE001 -- Python's operator protocol defines the caught data
        call = Expression([Symbol("py-operator"), selector, *operands])
        reason = Expression(
            [
                Symbol("python_error"),
                Symbol(type(error).__name__),
                Grounded(str(error)),
                Grounded(error),
            ]
        )
        return Expression([Symbol("Error"), call, reason])


# Restore a Python set from the dict-space pair representation.
def _py_set(pairs):
    if not isinstance(pairs, Expression):
        msg = "py-set takes the expression returned by dict-pairs"
        raise TypeError(msg)
    error = _carried_error(tuple(pairs.children))
    if error is not None:
        return error
    members = []
    for pair in pairs.children:
        if not isinstance(pair, Expression) or len(pair.children) != 2:
            msg = "py-set takes two-element member/truth pairs"
            raise TypeError(msg)
        members.append(pythonic(pair.children[0]))
    return set(members)


# Project a Python set into the dict-space pair representation.
def _py_set_pairs(value):
    carried = _carried_error((value,))
    if carried is not None:
        return carried
    members = pythonic(value)
    if not isinstance(members, set):
        msg = f"py-set-pairs takes a set, not {type(members).__name__}"
        raise TypeError(msg)
    return Expression([_expr(member, True) for member in members])  # noqa: FBT003 -- boolean atom payload


# Project a Python dict into the dict-space pair representation.
def _py_dict_pairs(value):
    carried = _carried_error((value,))
    if carried is not None:
        return carried
    mapping = pythonic(value)
    if not isinstance(mapping, dict):
        msg = f"py-dict-pairs takes a dict, not {type(mapping).__name__}"
        raise TypeError(msg)
    return Expression([_expr(key, item) for key, item in mapping.items()])


# Name the Python container species that needs a space-image restore.
def _py_container_kind(value):
    carried = _carried_error((value,))
    if carried is not None:
        return carried
    container = pythonic(value)
    if isinstance(container, set):
        return Symbol("set")
    if isinstance(container, dict):
        return Symbol("dict")
    return Symbol("other")


# Match one error against live Python classes and legacy symbol names.
def _except_matches(error, classinfo):
    classes, names = _exception_targets(classinfo)
    kind = _error_class(error)
    if isinstance(kind, BaseException):
        return (bool(classes) and isinstance(kind, classes)) or any(
            name in {cls.__name__ for cls in type(kind).__mro__} for name in names
        )
    if isinstance(kind, type):
        return (bool(classes) and issubclass(kind, classes)) or any(
            name in {cls.__name__ for cls in kind.__mro__} for name in names
        )
    if isinstance(kind, str):
        resolved = getattr(builtins, kind, None)
        if isinstance(resolved, type) and issubclass(resolved, BaseException):
            return (bool(classes) and issubclass(resolved, classes)) or any(
                name in {cls.__name__ for cls in resolved.__mro__} for name in names
            )
        return (
            kind in names
            or any(issubclass(Exception, candidate) for candidate in classes)
            # policy-inventory-exempt: mechanism-internal; reason=Exception and BaseException are the two symbolic catch-all names that may classify legacy string errors; evidence=extensions/python/metta/_prelude.py:_except_matches
            or any(name in {"Exception", "BaseException"} for name in names)
        )
    # MeTTa's own thrown data classifies only as a generic error.
    return any(issubclass(Exception, candidate) for candidate in classes) or any(
        # policy-inventory-exempt: mechanism-internal; reason=Exception and BaseException are the two symbolic catch-all names permitted to classify non-Python thrown data; evidence=extensions/python/metta/_prelude.py:_except_matches
        name in {"Exception", "BaseException"} for name in names
    )


# Return the original Python exception when an error carries one.
def _error_payload(error):
    instance = _error_instance(error)
    return error if instance is None else instance


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
            msg = f"a {type(value).__name__} cannot be {what}ed by {type(key).__name__}"
            raise TypeError(msg) from exc
        except (KeyError, IndexError) as exc:
            msg = f"{key!r} is not in this {type(value).__name__}"
            raise type(exc)(msg) from exc

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
        (_py_operator, "py-operator", [2, 3]),
        (_py_set, "py-set", None),
        (_py_set_pairs, "py-set-pairs", None),
        (_py_dict_pairs, "py-dict-pairs", None),
        (_py_container_kind, "py-container-kind", None),
        (_except_matches, "except", None),
        (_error_payload, "error-payload", None),
    ]
    for fn, name, arities in prelude:
        declarations = [_expr(S.arguments, S[name], S.atoms)]
        _ops_module.register(
            runtime,
            fn,
            name=_OperationName(name),
            effect="oracleIO",
            declarations=declarations,
            arities=arities,
        )
    runtime.must("spaces:metta_publish_builtin_visibility")
