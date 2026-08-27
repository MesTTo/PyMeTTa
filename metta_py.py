"""Purpose: the Python half of MeTTa's Python surface, so that resolving a
    name, reading an attribute, building a container and calling a callable are
    each ONE crossing instead of a conversation.
Assumes:
  - janus is importing this module by name after bindings/python/bridge.pl adds this directory to
    sys.path with py_add_lib_dir/1, so it must not import anything from the
    `metta` package: the engine runs with janus alone and the package need not
    be installed [tested: examples/ch11-python-as-a-notation/04-py_surface.metta under run.sh]
Guarantees:
  - resolve() imports the longest importable prefix of a dotted path and
    getattrs the rest, so a path of any depth works [tested: B26 in
    tests/prolog/suites/host/python_surface.plt]
  - resolve_grounded() and evaluate_grounded() retain an exact Python tuple
    behind a Python object reference, despite Janus translating base tuples
    eagerly [tested: test_a_python_tuple_answers_the_same_through_both_doors;
    commit=89374a7ed8eec75e26ea595f2c6e55665f80d6fc]
  - every function here returns the OBJECT, never a converted copy, so the
    caller decides what crosses; bindings/python/bridge.pl asks janus for py_object(true)
  - numeric_operation() uses Python's operator protocol and an object's array
    namespace for math functions, retaining reflected dispatch and library
    result types [tested: test_numpy_numeric_family_keeps_python_result_types
    and test_user_numeric_subclass_uses_its_own_operator; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
Fails when:
  - a name does not resolve. It raises rather than answering None, because a
    typo in a module path is not a value.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import builtins
import importlib
import math
import numbers
import operator
from collections.abc import Sequence
from typing import Any, Self


class _GroundedTuple(tuple):
    """A tuple subclass Janus carries as an object reference.

    Janus always translates an exact ``tuple`` to ``-/N``, even under
    ``py_object(true)``, but applies that rule to no tuple subclass.  Keeping
    the exact source tuple lets calls through this bridge receive that value,
    while the subclass supplies ordinary tuple behaviour to any other host
    path that receives the reference directly.
    """

    original: tuple

    def __new__(cls, value: tuple) -> Self:
        grounded = super().__new__(cls, value)
        grounded.original = value
        return grounded

    @property
    def __metta_wire_value__(self) -> tuple:
        """The exact tuple represented by this Janus-safe carrier."""
        return self.original


def _grounded(value: Any) -> Any:
    return _GroundedTuple(value) if type(value) is tuple else value


def _wire_value(value: Any) -> tuple[bool, Any]:
    wire_value = getattr(type(value), "__metta_wire_value__", None)
    if isinstance(wire_value, property):
        return True, wire_value.__get__(value, type(value))
    return False, value


def _needs_unwrap(value: Any, seen: set[int]) -> bool:
    wrapped, _ = _wire_value(value)
    if wrapped:
        return True
    if type(value) not in (list, tuple, dict, set, frozenset):
        return False
    identity = id(value)
    if identity in seen:
        return False
    seen.add(identity)
    if type(value) is dict:
        return any(
            _needs_unwrap(key, seen) or _needs_unwrap(item, seen)
            for key, item in value.items()
        )
    return any(_needs_unwrap(item, seen) for item in value)


def _unwrap(value: Any, active: set[int] | None = None) -> Any:
    if not _needs_unwrap(value, set()):
        return value
    wrapped, transported = _wire_value(value)
    if wrapped:
        return _unwrap(transported, active)

    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise ValueError(
            "a cyclic Python container containing a grounded transport value "
            "cannot cross the Python call boundary"
        )
    active.add(identity)
    try:
        return _unwrap_container(value, active)
    finally:
        active.remove(identity)


def _unwrap_container(value: Any, active: set[int]) -> Any:
    if type(value) is list:
        return [_unwrap(item, active) for item in value]
    if type(value) is tuple:
        return tuple(_unwrap(item, active) for item in value)
    if type(value) is dict:
        return {
            _unwrap(key, active): _unwrap(item, active)
            for key, item in value.items()
        }
    if type(value) is set:
        return {_unwrap(item, active) for item in value}
    return frozenset(_unwrap(item, active) for item in value)


def class_names(obj: Any) -> list[str]:
    """The visible MRO after removing transport and tuple carrier layers."""
    return [kind.__name__ for kind in type(_unwrap(obj)).__mro__ if kind is not object]


def is_numeric(value: Any) -> bool:
    """Whether a transported value implements Python's numeric tower."""
    return isinstance(_unwrap(value), numbers.Number)


_BINARY_NUMERIC_OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "min": builtins.min,
    "max": builtins.max,
    "pow-math": operator.pow,
}

_ARRAY_NUMERIC_OPERATORS = {
    "sqrt-math": "sqrt",
    "abs-math": "abs",
    "exp": "exp",
    "exp-math": "exp",
    "trunc-math": "trunc",
    "ceil-math": "ceil",
    "floor-math": "floor",
    "round-math": "round",
    "sin-math": "sin",
    "asin-math": "asin",
    "cos-math": "cos",
    "acos-math": "acos",
    "tan-math": "tan",
    "atan-math": "atan",
    "isnan-math": "isnan",
    "isinf-math": "isinf",
}

_UNARY_NUMERIC_OPERATORS = {
    "sqrt-math": math.sqrt,
    "abs-math": operator.abs,
    "exp": math.exp,
    "exp-math": math.exp,
    "trunc-math": math.trunc,
    "ceil-math": math.ceil,
    "floor-math": math.floor,
    "round-math": builtins.round,
    "sin-math": math.sin,
    "asin-math": math.asin,
    "cos-math": math.cos,
    "acos-math": math.acos,
    "tan-math": math.tan,
    "atan-math": math.atan,
    "isnan-math": math.isnan,
    "isinf-math": math.isinf,
}


def _array_namespace(values: tuple[Any, ...]) -> Any | None:
    for value in values:
        namespace = getattr(value, "__array_namespace__", None)
        if callable(namespace):
            return namespace()
    return None


def numeric_operation(name: str, args: Sequence[Any]) -> Any:
    """Apply one MeTTa numeric operation through Python's own protocols."""
    values = tuple(_unwrap(arg) for arg in args)
    binary = _BINARY_NUMERIC_OPERATORS.get(name)
    if binary is not None:
        if name in ("min", "max"):
            return binary(values)
        return binary(*values)

    namespace = _array_namespace(values)
    if name == "log-math":
        base, value = values
        if namespace is not None:
            log = namespace.log
            return operator.truediv(log(value), log(base))
        return math.log(value, base)

    array_name = _ARRAY_NUMERIC_OPERATORS.get(name)
    if namespace is not None and array_name is not None:
        return getattr(namespace, array_name)(*values)
    return _UNARY_NUMERIC_OPERATORS[name](*values)


def resolve(path: str) -> Any:
    """A dotted Python name of any depth, resolved to the object it names.

    `numpy.absolute` is a module attribute, `numpy.random.randint` is an
    attribute of a SUBMODULE that importing `numpy` alone does not bind, and
    `len` is a builtin. One rule covers all three: import the longest prefix
    that imports, then getattr the rest.

    That is what pydoc's `locate` and setuptools' entry points both do, and it
    is why `(py-atom numpy.random.randint)` works where splitting on the first
    dot cannot.
    """
    parts = path.split(".")
    if not all(parts):
        raise ValueError(f"{path!r} is not a dotted Python name")
    for cut in range(len(parts), 0, -1):
        try:
            found: Any = importlib.import_module(".".join(parts[:cut]))
        except ImportError:
            continue
        return _walk(found, parts[cut:], path)
    return _walk(builtins, parts, path)


def resolve_grounded(path: str) -> Any:
    """Resolve while retaining an exact tuple behind an object reference."""
    return _grounded(resolve(path))


def _walk(root: Any, attrs: list[str], path: str) -> Any:
    found = root
    for index, attr in enumerate(attrs):
        try:
            found = getattr(found, attr)
        except AttributeError as exc:
            reached = ".".join(attrs[:index]) or getattr(root, "__name__", root)
            raise AttributeError(
                f"{path!r} does not resolve: {reached} has no attribute {attr!r}"
            ) from exc
    return found


def evaluate(source: str) -> Any:
    """A Python expression, evaluated. `(py-atom "[1, 2, 3]")` in MeTTa.

    Separate from resolve() because the two answer different questions and a
    string that happens to parse as a name should still be evaluated: `"len"`
    is the builtin and `"len(x)"` is a call.
    """
    return eval(source, {"__builtins__": builtins})  # noqa: S307


def evaluate_grounded(source: str) -> Any:
    """Evaluate while retaining an exact tuple behind an object reference."""
    return _grounded(evaluate(source))


def dot(obj: Any, attr: str) -> Any:
    """An attribute, READ rather than called.

    `py-call`'s `.name` spelling always applies, so reading a property or
    getting a bound method as a value needed `getattr` by hand.
    """
    return getattr(_unwrap(obj), attr)


def apply(fn: Any, args: list, kwargs: dict | None = None) -> Any:
    """Call a resolved Python object. Kwargs arrive as a dict or not at all."""
    return _unwrap(fn)(
        *(_unwrap(arg) for arg in args),
        **{name: _unwrap(value) for name, value in (kwargs or {}).items()},
    )


def is_callable(obj: Any) -> bool:
    return callable(_unwrap(obj))


def unboxed(value: Any) -> Any:
    """The transport envelope removed, for the goal-term call route.

    bridge.pl's py-call builds a Python goal term whose arguments janus
    converts directly, so a metta Box reference reached the callee AS the
    Box; setattr on a crossed object raised 'Box' object has no attribute
    [measured 2026-08-25, integration/python.py's three-statement chain].
    apply() unwraps its own arguments; this hands the same _unwrap to the
    engine-side normalizer so both call routes see one law.
    """
    return _unwrap(value)


def build_list(items: list) -> list:
    return list(items)


def build_tuple(items: list) -> tuple:
    return tuple(items)


def build_dict(pairs: list) -> dict:
    """Pairs arrive as two-element sequences, which is how MeTTa spells a
    mapping: `(py-dict (("a" 1) ("b" 2)))`."""
    out = {}
    for pair in pairs:
        try:
            key, value = pair
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"py-dict takes pairs; {pair!r} is not one"
            ) from exc
        out[key] = value
    return out


def iterate(obj: Any) -> Any:
    """The iterator, so the Prolog side can pull one element at a time.

    Draining is what the engine must not do: a generator asked for its first
    element should run one step, and an infinite one should still work.
    """
    return iter(_unwrap(obj))


def render(obj: Any) -> str:
    """How a Python object displays in MeTTa.

    repr, which is what the language's own tutorials show: `(np-array (py-atom
    "[1, 2, 3]"))` displays `array([1, 2, 3])`, and `(+ (abs -5) 10)` displays
    `np.int64(15)`. An address would say nothing about either.
    """
    return repr(_unwrap(obj))


def sequence_length(obj: Any) -> int:
    """len(obj) when obj pattern-matches AS a sequence, and -1 when it does not.

    PEP 634 settled which Python objects a sequence pattern may take apart, and
    this is that rule verbatim: instances of `collections.abc.Sequence` other
    than `str`, `bytes` and `bytearray`. So a list, a tuple, a range and any
    registered Sequence have a structural reading in MeTTa, a string stays one
    atom rather than becoming its characters, and a dict or a set has none
    because neither is a sequence.

    -1 rather than None because the answer crosses as a number either way, and
    a sequence of length 0 is a real answer that None would be confused with.
    """
    obj = _unwrap(obj)
    if isinstance(obj, (str, bytes, bytearray)):
        return -1
    if isinstance(obj, Sequence):
        return len(obj)
    return -1
