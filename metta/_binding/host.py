"""Purpose: the Python half of MeTTa's Python surface, so that resolving a
    name, reading an attribute, building a container and calling a callable are
    each ONE crossing instead of a conversation.
Assumes:
  - janus is importing this module by name after extensions/python/metta/_binding/surface.pl adds this directory to
    sys.path with py_add_lib_dir/1, so it must not import anything from the
    `metta` package: the engine runs with janus alone and the package need not
    be installed [tested:
    test_a_python_tuple_answers_the_same_through_both_doors, which runs
    examples/ch11-python-as-a-notation/04-py_surface.metta through the engine
    seat where janus is all there is]
Guarantees:
  - sized_length reads __len__ once and never enumerates elements; a value
    without that protocol answers -1, and a failing __len__ propagates
    [tested: test_host_length_refinements_do_not_read_elements,
    test_a_host_length_failure_preserves_its_exception; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - resolve() imports the longest importable prefix of a dotted path and
    getattrs the rest, so a path of any depth works [tested:
    a_dotted_path_of_any_depth_resolves in
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
    [measured 2026-09-02: minimum of three rounds; command=cd extensions/python &&
    PYTHONPATH=. python -m
    benchmarks.resolve_prefix_cache 4 16 64 --repetitions 1000 --rounds 3;
    fixture=one synthetic module with live nested attributes;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - resolve_grounded() and evaluate_grounded() retain an exact Python tuple
    behind a Python object reference, despite Janus translating base tuples
    eagerly [tested: test_a_python_tuple_answers_the_same_through_both_doors;
    commit=89374a7ed8eec75e26ea595f2c6e55665f80d6fc]
  - the host helpers return Python results; the caller selects Janus
    object-reference transport [source:
    extensions/python/metta/_binding/surface.pl:metta_py_opts/1; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
  - container construction unwraps carried elements after their final crossing,
    preserving borrowed values inside call frames [tested:
    test_host_call_frames_preserve_borrowed_value_identity; commit=fb170a48db042c9a002e06f6cb47389af7fd66fc]
  - a py-atom type declaration follows a weak-referenceable Python object
    without owning it; values that cannot be weakly referenced carry their
    declaration in a weakly interned transparent envelope [tested:
    test_a_py_atom_declaration_dies_with_its_grounded_value;
    commit=bbf02dd309d15e178a9c83d03b749eb7170b6a20]
  - numeric_operation() uses Python's operator protocol and an object's array
    namespace for math functions, retaining reflected dispatch and library
    result types [tested: test_numpy_numeric_family_keeps_python_result_types
    and test_user_numeric_subclass_uses_its_own_operator; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - a scalar comparison over a host numeric answers Python's bool, so it
    crosses as the MeTTa boolean `if` and `==` read, while an array comparison
    keeps its array [tested: test_a_numpy_scalar_comparison_answers_the_metta_boolean;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - grounded_apply() is the engine's grounded call's one crossing: the
    callable and its arguments arrive as atoms on the wire and reach the
    callable through ``pythonic``, keyword pairs the translator read from a
    written ``(Kwargs ...)`` become keywords, and the result returns through
    ``returned``, so a generator it answers stays the unstarted object and a
    tuple is the expression it spells [tested:
    test_grounded_applications_use_the_seam_codec,
    test_grounded_applications_read_keywords_only_where_written; commit=fd0af38f748cedb593dd4e12c4dc19e8c283323a]
  - iterator objects crossing through resolve(), evaluate(), dot(), apply(), or
    a grounded transport envelope acquire one lazy shared cache; iterate()
    returns an independent cursor at index zero, while iterate_once() exposes
    Python's consumptive protocol for compiled for statements [tested:
    test_nested_py_iter_reads_form_the_cartesian_product,
    test_compiled_for_keeps_one_shot_python_iteration; commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
  - no iterator handed to janus's py_iter/2 raises: a pull that fails ends the
    enumeration with the reserved (stream_tag(), exception) pair, which
    extensions/python/metta/_binding/surface.pl turns back into the exception at the pull that
    raised, and a replayable source remembers the failure so every later cursor
    reports it at the same index instead of reading a truncated prefix
    [tested: test_a_raising_iterator_is_attributed_to_the_py_iter_that_pulled_it,
    test_a_failed_replay_source_reports_the_same_failure_to_every_cursor;
    commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44]
  - algebra_equal() compares tensor shape and exact elements, including unequal
    NaNs [tested: test_finite_tensor_semiring_checks_every_law,
    test_finite_tensor_nan_does_not_become_equal_by_identity; commit=074dc0a88b1605c54824de677d586b6f60998bcf].
  - the expression form of py-atom raises sys.audit("metta.host", "py-atom",
    source) before it evaluates, so an audit hook sees the source and can
    refuse it [tested: test_the_py_atom_expression_door_raises_its_event;
    commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
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
  - one cache of every value pulled from a live one-shot iterator; the carrier
    or grounded transport envelope owns it, and its death releases the source
    and cache [tested: test_a_grounded_iterator_cache_dies_with_its_box;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
Guarded by:
  - _DECLARATION_LOCK protects declaration records and carrier identity.
  - functools.lru_cache protects the bounded _resolve_plan cache during
    concurrent updates [source: Python 3.14.7 functools.lru_cache
    documentation; https://docs.python.org/3.14/library/functools.html#functools.lru_cache;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - _REPLAY_LOCK protects transport-envelope carrier identity, and each
    _ReplayableIterator lock serializes source pulls and cache publication
    [tested: test_two_threads_replay_one_iterator_without_duplicate_pulls;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
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
from collections.abc import Callable, Iterator, Sequence, Sized
from functools import lru_cache
from types import ModuleType
from typing import Any, Final, NamedTuple, Self

from metta._atoms.factories import Symbol, _atom_from_wire
from metta._catalog.call_values import pythonic, returned


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


class _StreamFailureTag:
    """The head of the reserved terminal-failure pair, and nothing else.

    A private class rather than a bare ``object()`` so the blob names itself
    wherever janus prints one, and a private instance rather than a value any
    caller could spell: the Prolog side tells the frame from an ordinary item
    by this object's IDENTITY, so an iterator's own data cannot forge one.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<metta_py terminal failure>"


#: The one tag object of this process. extensions/python/metta/_binding/surface.pl fetches it
#: once through stream_tag() and compares every pulled item against the blob it
#: got back, which is a pointer comparison and costs no crossing.
_STREAM_FAILURE: Final = _StreamFailureTag()


def stream_tag() -> _StreamFailureTag:
    """The tag that opens a terminal-failure pair, for the Prolog side to hold.

    Longhand for what surface.pl's ``py_iter_tag/1`` caches; nothing else
    calls it.
    """
    return _STREAM_FAILURE


def stream_reraise(error: BaseException) -> None:
    """Raise what a stream carried out, back on the Python side of the crossing.

    Called from Prolog with the object ``_stream_failure`` put in the pair, so
    the exception is raised inside an ordinary ``py_call``: janus maps
    ``KeyboardInterrupt`` and ``SystemExit`` onto their unwind forms and every
    other class onto ``error(python_error(Class, Object), context(...))``,
    which surface.pl's ``metta_py_guard/2`` already knows how to attribute. The
    shim's ``metta._errors.errors.stream_reraise`` is the same function for the
    operation and provider doors; this file may not import it, because the
    engine runs with janus alone.
    """
    raise error


def _stream_failure(error: BaseException) -> tuple[_StreamFailureTag, BaseException]:
    """Carry a terminal stream failure as data until Prolog can raise it.

    Janus pulls a Python iterator with ``PyIter_Next`` inside ``py_iter/2`` and
    never consults the error indicator afterwards, so an iterator that RAISES
    is indistinguishable there from one that is exhausted: the Prolog goal
    carries on over a silently truncated stream and the still-set Python
    exception surfaces at whatever crossing runs next [source: janus 1.5.3
    janus.c:py_iter3, the two ``state->next = PyIter_Next(state->iterator)``
    calls, neither followed by ``check_error``;
    commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe]. So no iterator this file
    hands to ``py_iter`` may raise; each ends a failure with this pair instead.

    A PAIR, where ``metta._errors.errors.stream_failure`` uses the four-element list
    ``["x", "raise", Class, Exception]``. The shape is forced by the options
    each seat crosses under: surface.pl asks for ``py_object(true)``, under
    which a Python list arrives as an opaque blob that Prolog cannot take
    apart without a second crossing, while an exact tuple arrives as ``-/2``
    with both elements in hand [measured 2026-09-07 with a janus probe:
    ``['x','raise',...]`` crossed as ``<py>(0x..,list)`` and ``(tag, exc)`` as
    ``<py>(0x..,object)-<py>(0x..,'ValueError')``].
    """
    return (_STREAM_FAILURE, error)


def _failed_during_generator_close(error: BaseException) -> bool:
    """Tell a release failure from an ordinary mid-iteration failure.

    ``yield from`` delegates ``close()`` to the source while handling
    ``GeneratorExit``, so a source whose ``finally`` raises carries that
    control signal as its direct context and must propagate rather than yield:
    yielding while closing raises ``RuntimeError: generator ignored
    GeneratorExit`` and hides the resource failure [tested:
    test_a_release_failure_while_closing_a_guarded_stream_propagates;
    commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44].
    """
    return isinstance(error.__context__, GeneratorExit)


def _guarded(source: Iterator[Any]) -> Iterator[Any]:
    """One iterator, made total: it yields items and never raises into py_iter.

    For the sources that keep no cache. ``_ReplayableIterator.replay`` carries
    the same rule itself, because there the failure also has to be remembered.
    """
    try:
        yield from source
    except GeneratorExit:
        raise
    # Every class, because every class poisons the crossing equally: a narrower
    # `except Exception` is what let KeyboardInterrupt through to py_iter on
    # the operation doors.
    except BaseException as error:
        if _failed_during_generator_close(error):
            raise
        yield _stream_failure(error)


class _ReplayableIterator:
    """One lazy source cache with a fresh index for every enumeration."""

    __slots__ = ("_cache", "_done", "_lock", "_source")

    def __init__(self, source: Iterator[Any]) -> None:
        self._source = source
        self._cache: list[Any] = []
        self._done = False
        self._lock = threading.RLock()

    @property
    def __metta_wire_value__(self) -> Iterator[Any]:
        """The original consumptive value represented by this carrier."""
        return self._source

    def replay(self) -> Iterator[Any]:
        """Read from index zero, extending the shared cache only on demand.

        A failure of the source is CACHED, as its last entry, so every cursor
        replays the same items and then the same failure at the same index. The
        source is spent once it has raised, so the alternative is not "try
        again": it is a second enumeration reading a silently truncated prefix
        as a complete answer, which is the defect the frame exists to close.
        This is RxJava's rule for a shared sequence -- ``Single.cache()``
        "caches its success or error event and replays it to all the downstream
        subscribers" -- rather than ``itertools.tee``'s, whose ``_tee.__next__``
        calls ``next(self.iterator)`` with no handler, so the failure reaches
        whichever tee pulled it and the others read the prefix
        [source: https://javadoc.io/doc/io.reactivex/rxjava/latest/rx/Single.html,
        cache(); CPython 3.14 itertools documentation, the tee() equivalent].
        """
        index = 0
        while True:
            with self._lock:
                if index < len(self._cache):
                    value = self._cache[index]
                elif self._done:
                    return
                else:
                    try:
                        value = _transported(next(self._source))
                    except StopIteration:
                        self._done = True
                        return
                    # Every class, for the reason _guarded gives.
                    except BaseException as error:  # noqa: BLE001
                        self._done = True
                        value = _stream_failure(error)
                    self._cache.append(value)
            index += 1
            yield value


def _transported(value: Any) -> Any:
    if isinstance(value, _ReplayableIterator):
        return value
    if isinstance(value, Iterator):
        return _ReplayableIterator(value)
    return value


def _grounded(value: Any) -> Any:
    return _GroundedTuple(value) if type(value) is tuple else _transported(value)


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
_REPLAY_LOCK = threading.RLock()
_REPLAY_CARRIERS: dict[
    int,
    tuple[weakref.ReferenceType[Any], _ReplayableIterator],
] = {}


def _transport_replay(envelope: Any, source: Iterator[Any]) -> _ReplayableIterator:
    """The replay cache owned by one weak-referenceable transport envelope."""
    key = id(envelope)
    with _REPLAY_LOCK:
        current = _REPLAY_CARRIERS.get(key)
        if current is not None and current[0]() is envelope:
            return current[1]

        def _evict(reference: weakref.ReferenceType[Any], key: int = key) -> None:
            with _REPLAY_LOCK:
                found = _REPLAY_CARRIERS.get(key)
                if found is not None and found[0] is reference:
                    del _REPLAY_CARRIERS[key]

        reference = weakref.ref(envelope, _evict)
        carrier = _ReplayableIterator(source)
        _REPLAY_CARRIERS[key] = (reference, carrier)
        return carrier


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
    # Keep replay ownership between a declaration envelope and the original.
    unwrapped = value if isinstance(value, _ReplayableIterator) else _unwrap(value)
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
        return True, wire_value.__get__(value, type(value))  # pylint: disable=unnecessary-dunder-call # invoke the discovered descriptor on its original receiver
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
        msg = (
            "a cyclic Python container containing a grounded transport value "
            "cannot cross the Python call boundary"
        )
        raise ValueError(msg)
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


# closed-set: decides; policy=Python numeric operator targets; reads=none
_BINARY_NUMERIC_OPERATORS: dict[str, Callable[..., Any]] = {
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

#: The comparisons whose scalar answer is a MeTTa boolean rather than a host value.
_COMPARISON_OPERATIONS = frozenset({"<", "<=", ">", ">="})

# closed-set: decides; policy=array namespace numeric targets; reads=none
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

# closed-set: decides; policy=Python scalar math targets; reads=none
_UNARY_NUMERIC_OPERATORS: dict[str, Callable[..., Any]] = {
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


# Exact shape plus all-elements equality follows numpy.array_equal, including
# unequal NaNs. Backend operations retain device arrays instead of copying them.
# [source: https://github.com/numpy/numpy/blob/v2.5.0/numpy/_core/numeric.py;
# commit=074dc0a88b1605c54824de677d586b6f60998bcf].
def algebra_equal(left: Any, right: Any) -> bool:
    """Compare finite algebra carrier values without transport identity."""
    left, right = _unwrap(left), _unwrap(right)
    left_shape = getattr(left, "shape", None)
    right_shape = getattr(right, "shape", None)
    if left_shape is not None or right_shape is not None:
        if left_shape is None or right_shape is None or left_shape != right_shape:
            return False
        compared = operator.eq(left, right)
        namespace = _array_namespace((compared,))
        if namespace is not None:
            return bool(namespace.all(compared))
        return bool(compared.all())
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        return (
            type(left) is type(right)
            and len(left) == len(right)
            and all(algebra_equal(a, b) for a, b in zip(left, right, strict=True))
        )
    return bool(operator.eq(left, right))


def numeric_operation(name: str, args: Sequence[Any]) -> Any:
    """Apply one MeTTa numeric operation through Python's own protocols."""
    values = tuple(_unwrap(arg) for arg in args)
    binary = _BINARY_NUMERIC_OPERATORS.get(name)
    if binary is not None:
        if name in ("min", "max"):
            return binary(values)
        result = binary(*values)
        # A scalar comparison answers Python's own bool. numpy's `int64(5) < 6`
        # is `np.True_`, a zero-dimensional object janus carries whole rather
        # than as the MeTTa boolean, so `(if (< x 6) yes no)` answered `no`
        # and `(== (< x 6) True)` answered False for every numpy scalar. An
        # array comparison keeps its array, whose truth is element-wise.
        if name in _COMPARISON_OPERATIONS and getattr(result, "ndim", 0) == 0:
            return bool(result)
        return result

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
            return _transported(_walk(root, attrs, path))
    try:
        return _transported(_walk(root, plan.attrs, path))
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
            msg = f"{path!r} does not resolve: {reached} has no attribute {attr!r}"
            raise AttributeError(msg) from exc
    return found


def evaluate(source: str) -> Any:
    """A Python expression, evaluated. `(py-atom "[1, 2, 3]")` in MeTTa.

    Separate from resolve() because the two answer different questions and a
    string that happens to parse as a name should still be evaluated: `"len"`
    is the builtin and `"len(x)"` is a call.

    The event is raised BEFORE the expression runs, which is PEP 578's whole
    shape: a hook may refuse by raising, and one that only watches sees the
    source rather than the code object `exec` would hand it. The name form
    needs none of its own, because importing raises `import` already.
    """
    sys.audit("metta.host", "py-atom", source)
    return _transported(eval(source, {"__builtins__": builtins}))  # noqa: S307  # nosec B307  # pylint: disable=eval-used # py-atom evaluates Python expressions after the metta.host audit event


def evaluate_grounded(source: str) -> Any:
    """Evaluate while retaining an exact tuple behind an object reference."""
    return _grounded(evaluate(source))


def dot(obj: Any, attr: str) -> Any:
    """An attribute, READ rather than called.

    `py-call`'s `.name` spelling always applies, so reading a property or
    getting a bound method as a value needed `getattr` by hand.
    """
    return _transported(getattr(_unwrap(obj), attr))


def apply(fn: Any, args: list, kwargs: dict | None = None) -> Any:
    """Call a resolved Python object with separate argument frames.

    The callee a compiled keyword or expanded call applies: the frames were
    assembled at run time, so their keywords cannot be written at a call site
    for the translator to read, and this callable takes them as the mapping
    they are. It is itself applied through grounded_apply(), so its frames
    arrive as the twin's values.
    """
    return _transported(
        _unwrap(fn)(
            *(_unwrap(arg) for arg in args),
            **{name: _unwrap(value) for name, value in (kwargs or {}).items()},
        )
    )


def grounded_apply(payload: Any, pairs: Any) -> Any:
    """Apply a grounded Python callable through the seam's codec.

    `payload` is the wire of `(callable argument ...)` and `pairs` the wire of
    the `((name value) ...)` a `(Kwargs ...)` written at the call site named,
    `()` when none was. Every argument reaches the callable through
    `pythonic`, the codec the seam's value calls and the prelude operators
    share (an expression is a tuple, a symbol stays a Symbol, a grounded
    value is itself), and the result crosses back through `returned`, held
    rather than reduced. This is seam:grounded_apply/4's one crossing, so a
    Python callable applied from MeTTa and one applied from a compiled body
    see the same values. It lives in the engine audience's module because the
    engine applies a grounded callable with or without the host runtime loaded.
    """
    application = _atom_from_wire(payload)
    callable_atom, *arguments = application.children
    named = {}
    for pair in _atom_from_wire(pairs).children:
        name, value = pair.children
        # A written keyword name is a symbol; a string spells the same name.
        named[name.name if isinstance(name, Symbol) else str(pythonic(name))] = pythonic(value)
    target = _unwrap(pythonic(callable_atom))
    return returned(target(*(pythonic(argument) for argument in arguments), **named)).to_wire()


def is_callable(obj: Any) -> bool:
    return callable(_unwrap(obj))


def unboxed(value: Any) -> Any:
    """The transport envelope removed, for the goal-term call route.

    surface.pl's py-call builds a Python goal term whose arguments janus
    converts directly, so a metta Box reference reached the callee AS the
    Box; setattr on a crossed object raised 'Box' object has no attribute
    [measured 2026-08-25, integration/python.py's three-statement chain].
    apply() unwraps its own arguments; this hands the same _unwrap to the
    engine-side normalizer so both call routes see one law.
    """
    return _unwrap(value)


def build_list(items: list) -> list:
    return list(_unwrap(items))


def build_tuple(items: list) -> tuple:
    return tuple(_unwrap(items))


def build_dict(pairs: list) -> dict:
    """Build a mapping from pairs, as in `(py-dict (("a" 1) ("b" 2)))`."""
    out = {}
    for pair in _unwrap(pairs):
        try:
            key, value = pair
        except (TypeError, ValueError) as exc:
            msg = f"py-dict takes pairs; {pair!r} is not one"
            raise ValueError(msg) from exc
        out[key] = value
    return out


def iterate(obj: Any) -> Any:
    """The iterator, so the Prolog side can pull one element at a time.

    Draining is what the engine must not do: a generator asked for its first
    element runs one step, an infinite one still works, and a later read starts
    at index zero without pulling an already cached value from the source.

    The shared-cache/fresh-index model follows itertools.tee, while the lock
    also permits concurrent readers, which tee explicitly does not guarantee.
    [source: Python 3.14 itertools.tee documentation;
    https://docs.python.org/3.14/library/itertools.html#itertools.tee;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]

    A pull that RAISES ends the enumeration with ``_stream_failure``'s pair
    rather than raising into ``py_iter``; the three cached paths carry that
    themselves, in ``replay``, because there the failure must also be
    remembered for the next cursor.
    """
    if isinstance(obj, _ReplayableIterator):
        return obj.replay()
    if isinstance(obj, _DeclaredValue) and isinstance(obj.value, _ReplayableIterator):
        return obj.value.replay()
    wrapped, source = _wire_value(obj)
    if wrapped and isinstance(source, Iterator):
        return _transport_replay(obj, source).replay()
    return _guarded(iter(_unwrap(obj)))


def iterate_once(obj: Any) -> Iterator[Any]:
    """Python's original consumptive iterator protocol for compiled loops.

    Guarded like every other stream this file hands to ``py_iter`` and cached
    like none of them: a source that has raised is spent, which is Python's own
    consumptive rule, so a second ``py-iter-once`` over it reads the empty
    remainder rather than the failure. ``py-iter`` is the replayable reading
    and remembers.
    """
    return _guarded(iter(_unwrap(obj)))


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


def sized_length(obj: Any) -> int:
    """Return a value's length, or -1 when it has no length protocol."""
    # Length constraints use len(), independently of sequence patterns:
    # https://github.com/annotated-types/annotated-types/blob/v0.7.0/annotated_types/__init__.py
    obj = _unwrap(obj)
    return len(obj) if isinstance(obj, Sized) else -1
