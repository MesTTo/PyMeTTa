"""Purpose: the Python half of MeTTa's Python surface, so that resolving a
    name, reading an attribute, building a container and calling a callable are
    each ONE crossing instead of a conversation.
Assumes:
  - janus is importing this module by name after extensions/python/bridge.pl adds this directory to
    sys.path with py_add_lib_dir/1, so it must not import anything from the
    `metta` package: the engine runs with janus alone and the package need not
    be installed [tested: examples/ch11-python-as-a-notation/04-py_surface.metta under run.sh]
Guarantees:
  - resolve() imports the longest importable prefix of a dotted path and
    getattrs the rest, so a path of any depth works [tested: B26 in
    tests/prolog/suites/host/python_surface.plt]
  - prefix fallback handles only a missing candidate module; import failures
    raised by an importable candidate propagate unchanged [tested:
    test_resolution_preserves_internal_failure_from_an_importable_prefix;
    commit=e8b8cbc6734e73199f0f4105b6f0d4168516521a]
  - successful resolve() calls reuse a bounded weak prefix plan, retain live
    final attributes, and refresh when the chosen module or its next longer
    prefix changes in sys.modules [tested:
    test_repeated_resolution_reuses_the_import_plan,
    test_resolution_reuses_the_prefix_and_reads_the_current_attribute,
    test_resolution_refreshes_after_module_replacement,
    test_resolution_refreshes_when_a_longer_module_is_loaded,
    test_a_failed_final_read_does_not_poison_a_later_lookup;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - over 1,000 hot paths of depth 4/16/64, prefix imports fall from
    4,000/16,000/64,000 to zero and minimum time falls from
    15.575/250.514/4293.293 to 0.259/0.556/2.008 microseconds per resolution
    [measured: minimum of three rounds; command=cd extensions/python &&
    PYTHONPATH=. /home/user/Dev/.venv-pypetta/bin/python -m
    benchmarks.resolve_prefix_cache 4 16 64 --repetitions 1000 --rounds 3;
    fixture=one synthetic module with live nested attributes;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - resolve_grounded() and evaluate_grounded() retain an exact Python tuple
    behind a Python object reference, despite Janus translating base tuples
    eagerly [tested: test_a_python_tuple_answers_the_same_through_both_doors;
    commit=89374a7ed8eec75e26ea595f2c6e55665f80d6fc]
  - every function here returns the OBJECT, never a converted copy, so the
    caller decides what crosses; extensions/python/bridge.pl asks janus for py_object(true)
  - a py-atom type declaration follows a weak-referenceable Python object
    without owning it; values that cannot be weakly referenced carry their
    declaration in a weakly interned transparent envelope [tested:
    test_a_py_atom_declaration_dies_with_its_grounded_value;
    commit=bbf02dd309d15e178a9c83d03b749eb7170b6a20]
  - numeric_operation() uses Python's operator protocol and an object's array
    namespace for math functions, retaining reflected dispatch and library
    result types [tested: test_numpy_numeric_family_keeps_python_result_types
    and test_user_numeric_subclass_uses_its_own_operator; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
Fails when:
  - a name does not resolve. It raises rather than answering None, because a
    typo in a module path is not a value.
Owns resources:
  - one weak registry entry per live weak-referenceable declaration, and one
    weak cache entry per live non-weak-referenceable declaration carrier.
  - at most RESOLVE_CACHE_MAX weak prefix plans; plans never own their modules
    [tested: test_resolution_plans_do_not_own_temporary_modules,
    test_resolution_plan_cache_is_bounded;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
Guarded by:
  - _DECLARATION_LOCK protects declaration records and carrier identity.
  - functools.lru_cache protects the bounded _resolve_plan cache during
    concurrent updates [source: Python 3.14.7 functools.lru_cache
    documentation; https://docs.python.org/3.14/library/functools.html#functools.lru_cache;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205, D415 -- the contract is one continuous invariant

from __future__ import annotations

import builtins
import importlib
import math
import numbers
import operator
import sys
import threading
import weakref
from collections.abc import Sequence
from functools import lru_cache
from types import ModuleType
from typing import Any, Final, NamedTuple, Self


class _GroundedTuple(tuple):
    """A tuple subclass Janus carries as an object reference.

    Janus always translates an exact ``tuple`` to ``-/N``, even under
    ``py_object(true)``, but applies that rule to no tuple subclass. Keeping
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


class _DeclaredValue:
    """A transparent declaration owner for values weakref cannot observe."""

    __slots__ = ("__weakref__", "_declared_type_texts", "value")

    def __init__(self, value: Any) -> None:
        self.value = value
        self._declared_type_texts: list[str] = []

    @property
    def __metta_wire_value__(self) -> Any:
        """The exact value represented by this private carrier."""
        return self.value

    def declare(self, type_text: str) -> None:
        """Record one type once, preserving declaration order."""
        with _DECLARATION_LOCK:
            if type_text not in self._declared_type_texts:
                self._declared_type_texts.append(type_text)

    def declarations(self) -> list[str]:
        """Snapshot the declarations while the carrier is live."""
        with _DECLARATION_LOCK:
            return list(self._declared_type_texts)

    def __copy__(self) -> _DeclaredValue:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> _DeclaredValue:
        return self


_DECLARATION_LOCK = threading.RLock()
_DECLARATIONS: dict[int, tuple[weakref.ReferenceType[Any], list[str]]] = {}
_DECLARED_CARRIERS: dict[int, weakref.ReferenceType[_DeclaredValue]] = {}


def _declared_carrier(value: Any) -> _DeclaredValue:
    """Return the stable metadata carrier for a non-weak-referenceable value."""
    if isinstance(value, _DeclaredValue):
        return value
    key = id(value)
    with _DECLARATION_LOCK:
        reference = _DECLARED_CARRIERS.get(key)
        if reference is not None:
            carrier = reference()
            if carrier is not None and carrier.value is value:
                return carrier
        carrier = _DeclaredValue(value)

        def _evict(_: Any, key: int = key) -> None:
            with _DECLARATION_LOCK:
                current = _DECLARED_CARRIERS.get(key)
                if current is not None and current() is None:
                    del _DECLARED_CARRIERS[key]

        _DECLARED_CARRIERS[key] = weakref.ref(carrier, _evict)
        return carrier


def declare_type(value: Any, type_text: str) -> Any:
    """Attach one serialized MeTTa type without strongly owning the value."""
    if not isinstance(type_text, str):
        msg = f"a declared type encoding must be str, not {type(type_text).__name__}"
        raise TypeError(msg)
    if isinstance(value, _DeclaredValue):
        value.declare(type_text)
        return value
    unwrapped = _unwrap(value)
    try:
        key = id(unwrapped)

        def _evict(reference: weakref.ReferenceType[Any], key: int = key) -> None:
            with _DECLARATION_LOCK:
                current = _DECLARATIONS.get(key)
                if current is not None and current[0] is reference:
                    del _DECLARATIONS[key]

        reference = weakref.ref(unwrapped, _evict)
    except TypeError:
        carrier = _declared_carrier(unwrapped)
        carrier.declare(type_text)
        return carrier
    with _DECLARATION_LOCK:
        current = _DECLARATIONS.get(key)
        if current is None or current[0]() is not unwrapped:
            texts: list[str] = []
            _DECLARATIONS[key] = (reference, texts)
        else:
            texts = current[1]
        if type_text not in texts:
            texts.append(type_text)
    return value


def declared_type_texts(value: Any) -> list[str]:
    """Return live declarations without extending the value's lifetime."""
    if isinstance(value, _DeclaredValue):
        return value.declarations()
    unwrapped = _unwrap(value)
    key = id(unwrapped)
    with _DECLARATION_LOCK:
        current = _DECLARATIONS.get(key)
        if current is None or current[0]() is not unwrapped:
            return []
        return list(current[1])


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


RESOLVE_CACHE_MAX: Final[int] = 512


class _ResolvePlan(NamedTuple):
    """An import prefix and the live attribute path below it."""

    module_name: str | None
    module: weakref.ReferenceType[ModuleType]
    attrs: tuple[str, ...]
    next_module_name: str | None
    next_module: weakref.ReferenceType[ModuleType] | None


def _find_resolve_root(path: str) -> tuple[ModuleType, str | None, tuple[str, ...]]:
    """Import the longest prefix and return its remaining attribute path."""
    parts = path.split(".")
    if not all(parts):
        msg = f"{path!r} is not a dotted Python name"
        raise ValueError(msg)
    for cut in range(len(parts), 0, -1):
        module_name = ".".join(parts[:cut])
        try:
            found = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            # ImportError.name records the module being imported. A missing
            # intermediate package also rules out this longer candidate; any
            # name outside the candidate's prefix chain is a dependency the
            # candidate failed to import and must remain the reported failure.
            # [source: https://docs.python.org/3/library/exceptions.html#ImportError; commit=e8b8cbc6734e73199f0f4105b6f0d4168516521a]
            missing = error.name
            if not isinstance(missing, str) or not (
                module_name == missing or module_name.startswith(f"{missing}.")
            ):
                raise
            continue
        return found, module_name, tuple(parts[cut:])
    return builtins, None, tuple(parts)


# A bounded LRU retains recent plans and supplies a coherent cache under
# concurrent calls. Its explicit clear operation is the invalidation primitive.
# [source: Python 3.14.7 functools.lru_cache documentation,
# https://docs.python.org/3.14/library/functools.html#functools.lru_cache;
# commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
@lru_cache(maxsize=RESOLVE_CACHE_MAX)
def _resolve_plan(path: str) -> _ResolvePlan:
    root, module_name, attrs = _find_resolve_root(path)
    next_name = None
    if attrs:
        next_name = attrs[0] if module_name is None else f"{module_name}.{attrs[0]}"
    next_module = sys.modules.get(next_name) if next_name is not None else None
    next_reference = (
        weakref.ref(next_module) if isinstance(next_module, ModuleType) else None
    )
    return _ResolvePlan(
        module_name,
        weakref.ref(root),
        attrs,
        next_name,
        next_reference,
    )


def _current_plan_root(plan: _ResolvePlan) -> ModuleType | None:
    """Return the planned root only while its import bindings are unchanged."""
    root = plan.module()
    if root is None:
        return None
    if plan.module_name is not None and sys.modules.get(plan.module_name) is not root:
        return None
    if plan.next_module_name is None:
        return root
    expected = plan.next_module() if plan.next_module is not None else None
    if sys.modules.get(plan.next_module_name) is not expected:
        return None
    return root


def clear_resolve_cache() -> None:
    """Forget imported-prefix plans after an external import-registry change."""
    _resolve_plan.cache_clear()


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
    plan = _resolve_plan(path)
    root = _current_plan_root(plan)
    if root is None:
        clear_resolve_cache()
        plan = _resolve_plan(path)
        root = _current_plan_root(plan)
        if root is None:
            root, _, attrs = _find_resolve_root(path)
            return _walk(root, attrs, path)
    try:
        return _walk(root, plan.attrs, path)
    except AttributeError:
        # A failed final read is not a durable plan: a later import or
        # attribute assignment must be able to make the same name valid.
        clear_resolve_cache()
        raise


def resolve_grounded(path: str) -> Any:
    """Resolve while retaining an exact tuple behind an object reference."""
    return _grounded(resolve(path))


def _walk(root: Any, attrs: Sequence[str], path: str) -> Any:
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
