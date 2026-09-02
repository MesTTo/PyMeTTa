"""Purpose: immutable atom values, Python value encoding, and bounded identity caches.
Guarantees:
  - standard callable mentions encode as their symbolic MeTTa heads and all
    four atom rich comparisons follow the engine order used by plain sorted [tested:
    test_callable_mentions_share_operator_and_fourteen_math_names and
    test_atom_comparisons_are_only_ordering; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - atom/plain ordering and comparison-term truthiness refuse with structured
    Python-reference grounds; chained comparisons name the explicit conjunction
    remedy [tested:
    extensions/python/tests/ch10_errors_and_refusals/test_refusal_grounds.py;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - Grounded preserves every non-primitive Python value by identity; only
    exact bool, int, float and str values use native wire terms [tested:
    extensions/python/tests/ch03_atoms_and_expressions/test_identity_wire.py;
    commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - engine rational wire values decode to exact Fraction payloads, while a
    Python-created Fraction follows the non-primitive identity law [tested:
    test_rational_payloads_cross_the_scalar_door and
    test_non_primitive_numbers_keep_their_python_identity; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - pathlib paths encode as symbols rather than opaque host boxes [tested:
    test_path_and_capability_options_cross_as_symbols; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - Ellipsis encodes as the gap symbol, so `...` in a pattern child position is
    the engine's anonymous segment variable [tested:
    test_ellipsis_is_an_anonymous_segment; commit=a3dff3abc83b9d82f3652093246e1d693d526cdb]
  - Grounded carries the engine's two relations, one per operand kind: against a
    raw value it is the == operator's numeric tower, against another atom it
    is unification identity (integer and float atoms distinct, signed zeros
    distinct, NaN self-equal), the same split Java makes between == and
    Double.equals so collections of values stay coherent
    [tested: test_python_equality_is_engine_equality,
    test_atom_equality_is_engine_unification; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - raw tuples are transparent Expression values with symmetric equality and
    identical hashes; explicit Grounded(tuple) remains opaque identity data
    [tested: test_a_tuple_equals_the_expression_it_encodes_to,
    test_an_opaque_grounded_tuple_is_not_its_transparent_expression,
    test_expression_tuple_equality_is_symmetric_and_hash_coherent;
    commit=012413efb73b4dd27c71354c7f654862f349c03f]
  - atom copy and pickle protocols preserve value and identity contracts
    [tested test_atoms_pickle_by_value, test_process_local_grounded_values_refuse_pickle]
  - Expression is a complete immutable Sequence with iterative equality and hashing
    [tested test_expr_sequence_index_and_count, test_expr_identity_equality]
  - Expression collects one generic iterable, snapshots a Space listing, and
    keeps its kind when sliced [tested:
    test_expression_collects_iterables_and_slices_keep_the_expression_kind,
    test_expression_of_a_space_is_an_assembly_order_snapshot; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - unary plus is atom identity and allocates no staged expression [tested:
    test_unary_plus_is_atom_identity; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - Expression virtual Sequence registration uses 4.00% fewer instructions than
    nominal inheritance [measured 2026-08-14: minimum of three instructions:u runs]
  - Expression writes its slots through their descriptors rather than
    object.__setattr__, which costs term-operators 6.55% fewer instructions
    and wire-codec 2.24% fewer [measured 2026-08-19: minimum of three
    instructions:u runs, interleaved against the same tree without it]
  - wire and object identity caches are bounded or weak and synchronized
    [tested test_wire_intern_tables_are_bounded,
    test_atom_identity_caches_are_thread_safe]
  - the wire intern cache evicts in constant time in its bound, so its bound
    is a memory decision rather than a speed one [tested
    test_the_intern_cache_evicts_in_constant_time]
  - _WIRE_SYM_ORDER and _WIRE_VAR_ORDER hold exactly the keys of the cache
    each one bounds, and _wire_intern_clear is the only door that empties
    either [tested test_the_intern_cache_evicts_in_constant_time]
  - object formatters can be removed by their exact registration identity
    [tested test_object_repr_registrations_can_be_removed_exactly]
  - Expression builds its wire form on the first crossing and never on
    construction, 10.1x per call flat and 98.1x nested against rebuilding
    it [measured 2026-08-19: 20,000 crossings, minimum of three
    instructions:u runs with the interpreter floor subtracted; tested
    test_expr_defers_its_wire_form_until_asked]
  - encode answers common types from a table keyed on the exact class and
    falls through to its singledispatch otherwise, 4603 instructions per
    call against 2306 [measured 2026-08-19: 800,000 calls over eight leaf
    types, minimum of three instructions:u runs, empty loop subtracted]
  - _ENCODE_FAST never disagrees with encode.registry: every entry is
    resolved by asking encode.dispatch, and every registration rebuilds it
    [tested test_the_type_fast_path_precedes_encode_and_survives_a_register]
  - __metta__ is discovered on the class, so instance fallback and properties
    cannot run merely because encoding checked for an explicit hook
    [tested: test_dunder_metta_is_read_off_the_class_not_the_instance;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Box publishes its transport value through the reserved
    __metta_wire_value__ protocol, so host bridges can remove the wire layer
    without importing the Python package [tested:
    test_a_python_tuple_answers_the_same_through_both_doors;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Grounded keeps a returned object carrier privately while exposing its
    underlying value, so carrier-owned metadata survives a later engine
    crossing [tested:
    test_a_py_atom_declaration_dies_with_its_grounded_value;
    commit=bbf02dd309d15e178a9c83d03b749eb7170b6a20]
  - Atom operator methods are installed from the immutable 22-entry lowering
    table, including explicit templates and named refusals [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``atom.cast(type_)`` delegates to the ambient ``Space.cast`` door, so
    declarations remain space-relative while the atom owns the concise
    spelling [tested: test_atom_cast_delegates_to_the_ambient_space;
    commit=49c43f86fa17a20ecebf9f9dbb5514de4762297d]
  - Grounded heads preserve keyword arguments for the py-call seam, while a
    signature-free Symbol refuses keywords it cannot position [tested:
    test_unknown_symbol_keywords_refuse_with_the_positional_remedy;
    commit=c2ad5892fbfdd690dd7e9b507e76e87d7d1376d1]
  - symbolic operator rows specialize into direct constructors once at import,
    so term-operators costs 660489697 instructions:u, 27.86% below its
    915593600 baseline [measured: minimum of 660489757, 660489704,
    660489697 on 2026-08-21;
    command=python -m benchmarks.check_instructions term-operators;
    fixture=CPython 3.14 controlled perf lane;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Handle is the common grounded species for executable references, while
    native blobs retain process-local registry identity
    [tested: test_space_handles_are_term_operands_and_round_trip;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - a native blob's public wire value preserves its registry id and display
    text, the two fields its decoder requires [tested:
    test_native_handles_round_trip_through_the_public_wire_codec;
    commit=WORKTREE]
Guarded by:
  - _STATE_LOCK protects box identity, formatter registries, and wire interns
    [tested test_atom_identity_caches_are_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import contextlib
import inspect
import math
import threading
import weakref
from abc import ABCMeta
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from fractions import Fraction
from functools import singledispatch
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Self, cast, overload

from ._call_binding import refuse_unknown_keywords
from ._callable_mentions import callable_mention
from ._operator_lowerings import OPERATOR_LOWERINGS, OperatorLowering
from .errors import (
    _PYTHON_COMPARISON_GROUND,
    _PYTHON_RICH_COMPARISON_GROUND,
    _grounded_type_error,
)


def _encodable(value: str) -> str:
    """Refuse text the boundary cannot carry, naming the reason.

    Python allows an unpaired surrogate in a str; UTF-8 has no encoding for
    one, so janus would fail with a bare SystemError pointing at nothing.
    """
    if value.isascii():
        return value
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        msg = (
            f"this string cannot cross to the engine: it contains an unpaired "
            f"surrogate at position {exc.start}, which has no UTF-8 encoding. "
            f"Repair the text, or carry it whole with metta.ground(text)."
        )
        raise ValueError(
            msg
        ) from None
    return value


def _normalize_grounded(value: Any) -> Any:
    """Retain the exact Python value a grounded atom was constructed with."""
    return value


def _is_primitive(value: Any) -> bool:
    """Whether identity is wholly represented by an exact primitive value."""
    return type(value) in (str, int, float, bool)


def _ground_identical(mine: Any, theirs: Any) -> bool:
    """Identity exactly as the engine reads two crossed values, through EITHER
    of its doors: what unification matches and what the == operator answers are
    now one relation.

    They were two. Until 2026-08-30 == was a numeric tower over crossed values
    -- an integer equal to a float, signed zeros equal, NaN unequal to itself
    -- and this file carried a second helper for it. The tower was ours:
    upstream declares == over two INDEPENDENT type variables and compares
    exactly, so aligning the declaration collapsed the split. Every edge that
    used to separate them now agrees on both sides
    [measured 2026-08-30, ours and PeTTa@ae66fa8 alike, through the text door
    and through Grounded values: `(== 0 0.0)`, `(== 0.0 -0.0)`, `(== True 1)`
    and `(== 1 "a")` are all False, `(== NaN NaN)` is True].

    Booleans are not numbers, an integer never equals a float, 0.0 and -0.0
    are two values, one NaN matches another, and an opaque object is itself
    alone -- a Fraction included, which is why
    `(== (Fraction 1 2) (Fraction 1 2))` over two distinct objects answers
    False. Matching, membership, removal and every dict of atoms follow this,
    so a Counter of atoms counts what the space stores.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    mine = _normalize_grounded(mine)
    theirs = _normalize_grounded(theirs)
    if type(mine) is not type(theirs):
        return False
    if type(mine) is float:
        if math.isnan(mine) or math.isnan(theirs):
            return math.isnan(mine) and math.isnan(theirs)
        return mine == theirs and math.copysign(1.0, mine) == math.copysign(1.0, theirs)
    if _is_primitive(mine):
        return mine == theirs
    return mine is theirs


_STATE_LOCK = threading.RLock()


class Box:
    """Holds one Python value so it crosses the boundary by reference.

    janus rewrites more than containers on the way in: lists, tuples, dicts,
    sets, bytes and None become Prolog terms, and anything speaking the
    sequence protocol, a NumPy array included, explodes into a list of
    element objects. Which types convert is janus's decision, not ours, so
    every opaque value crosses boxed, uniformly, and every consuming surface
    unboxes: from_wire, raw operation arguments and results, and the
    engine's typing through seam:grounded_type_names/2. A caller never sees a
    box; it exists only on the wire and inside the engine.

    Boxes are INTERNED per object identity through boxed(): one live object
    always crosses as the same box, so a stored atom and a later query meet
    in the same reference and unification by identity means identity. The
    intern table holds boxes weakly: a box lives exactly as long as
    something references it (an atom in a space does, through janus), and a
    dropped object costs nothing forever after.
    """

    __slots__ = {
        "__weakref__": "weak-referenceable so caches can hold boxes lightly",
        "value": "the wrapped Python object, exactly as given",
    }

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Box({self.value!r})"

    @property
    def __metta_wire_value__(self) -> Any:
        """The host value hidden by this private transport envelope."""
        return self.value

    def __copy__(self) -> Box:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Box:
        return self

    def __reduce__(self):
        msg = (
            "a metta Box carries process-local object identity and cannot be "
            "pickled; serialize the underlying value explicitly if identity "
            "is not part of its meaning"
        )
        raise TypeError(
            msg
        )


def _unbox_wire_value(value: Any) -> Any:
    """Remove transport envelopes through their reserved value protocol."""
    wire_value = getattr(type(value), "__metta_wire_value__", None)
    if isinstance(wire_value, property):
        if wire_value.fget is None:
            msg = "__metta_wire_value__ must be a readable property"
            raise TypeError(msg)
        return _unbox_wire_value(wire_value.fget(value))
    return value


# WeakKeyDictionary is not suitable here: it follows user equality, while
# arrays and atoms can return non-boolean values from equality. Keying by id
# plus an identity re-check keeps object identity as the unification rule.
# id(value) -> weakref to the box carrying it; see Box's docstring.
_BOXES: dict[int, weakref.ref[Box]] = {}


def boxed(value: Any) -> Box:
    """THE box for this object, stable while any reference to it lives."""
    key = id(value)
    with _STATE_LOCK:
        reference = _BOXES.get(key)
        if reference is not None:
            box = reference()
            if box is not None and box.value is value:
                return box
        box = Box(value)

        def _evict(_: Any, key: int = key) -> None:
            with _STATE_LOCK:
                current = _BOXES.get(key)
                if current is not None and current() is None:
                    del _BOXES[key]

        _BOXES[key] = weakref.ref(box, _evict)
        return box


# type -> callable(value) -> str, consulted by Grounded.__str__ for object values,
# so a stored tensor prints its shape and dtype rather than an address.
_OBJECT_REPRS: dict[type, Callable[[Any], str]] = {}

# Private protocol dispatch supports the short metta.integrate.repr surface.
_PROTOCOL_REPRS: list[tuple[Callable[[Any], bool], Callable[[Any], str]]] = []

def register_object_repr(kind: type, fn: Callable[[Any], str]) -> None:
    """Teach grounded values of one type how to print."""
    with _STATE_LOCK:
        _OBJECT_REPRS[kind] = fn


def unregister_object_repr(kind: type) -> None:
    """Remove the formatter registered for one exact type.

    Raises KeyError when the type has no formatter, so cleanup cannot appear
    to succeed while leaving a different registration live.
    """
    with _STATE_LOCK:
        if kind not in _OBJECT_REPRS:
            msg = f"no object repr is registered for {kind.__qualname__}"
            raise KeyError(msg)
        del _OBJECT_REPRS[kind]


def _register_protocol_repr(
    predicate: Callable[[Any], bool], fn: Callable[[Any], str]
) -> None:
    """Register the implementation behind metta.integrate.register_repr."""
    with _STATE_LOCK:
        _PROTOCOL_REPRS.append((predicate, fn))


def _unregister_protocol_repr(
    predicate: Callable[[Any], bool], fn: Callable[[Any], str]
) -> None:
    """Remove the latest private protocol formatter matching both callables."""
    with _STATE_LOCK:
        for index in range(len(_PROTOCOL_REPRS) - 1, -1, -1):
            registered_predicate, registered_fn = _PROTOCOL_REPRS[index]
            if registered_predicate is predicate and registered_fn is fn:
                _PROTOCOL_REPRS.pop(index)
                return
    msg = "no protocol repr is registered for those exact callables"
    raise KeyError(msg)


def _float_text(value: float) -> str:
    """The engine's float spelling, so one atom has one text in both hosts.

    The digits are repr's, the shortest decimal that reads back to the
    same binary64, which is also what the engine's writer starts from;
    the LAYOUT is the arbiter's law the engine implements [source: LeaTTa
    RyuLean4/Runtime.lean:371-396, Decimal.formatMeTTa]: with D the
    stripped significand and KK the exponent making the value 0.D*10^KK,
    print positionally while KK is in -4..16 and scientifically
    otherwise, exponent KK-1, minus sign only, never a plus, never
    zero-padded. repr differs on exactly the plus sign (1e+16), the
    exponent padding (1e-05), the small-magnitude threshold (1e-05 where
    the law says 0.00001), and nan against the engine's NaN
    [tested: test_gnd_str_spells_numbers_the_engines_way].
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    text = repr(value)
    sign = "-" if text.startswith("-") else ""
    mantissa, _, exponent_text = text.lstrip("-").partition("e")
    int_part, _, frac_part = mantissa.partition(".")
    digits = (int_part + frac_part).lstrip("0")
    if not digits:
        return sign + "0.0"
    tens = (int(exponent_text) if exponent_text else 0) - len(frac_part)
    stripped = digits.rstrip("0")
    tens += len(digits) - len(stripped)
    kk = len(stripped) + tens
    if kk - len(stripped) >= 0 and kk <= 16:
        return f"{sign}{stripped}{'0' * (kk - len(stripped))}.0"
    if 0 < kk <= 16:
        return f"{sign}{stripped[:kk]}.{stripped[kk:]}"
    if -5 < kk <= 0:
        return f"{sign}0.{'0' * -kk}{stripped}"
    if len(stripped) == 1:
        return f"{sign}{stripped}e{kk - 1}"
    return f"{sign}{stripped[0]}.{stripped[1:]}e{kk - 1}"


def _object_str(value: Any) -> str:
    with _STATE_LOCK:
        formatter = next(
            (_OBJECT_REPRS[kind] for kind in type(value).__mro__ if kind in _OBJECT_REPRS),
            None,
        )
        protocols = tuple(_PROTOCOL_REPRS)
    if formatter is not None:
        return formatter(value)
    for predicate, protocol_formatter in protocols:
        try:
            if predicate(value):
                return protocol_formatter(value)
        except Exception as exc:
            msg = f"a registered object repr raised on {type(value).__name__}: {exc}"
            raise RuntimeError(msg) from exc
    return f"<{type(value).__name__}>"


def _leaf_refusal_message(atom: Atom, refusal: str) -> str:
    return f"{atom!r} is a leaf atom and {refusal}"


class Atom:
    """Base class. Atoms are immutable, hashable, and compare structurally."""

    __slots__ = ()

    def __repr__(self) -> str:
        from .atoms import _pretty  # noqa: PLC0415  -- atoms owns layout

        return _pretty(self)

    # Term structure is declared on the base because an engine answer is
    # typed Atom and a checker cannot know which kind arrived. Expression's
    # docstring already promises expr[0] and len(expr), and run, eval and
    # query all return Atom, so without these the documented idiom does not
    # type-check: ten of the 41 diagnostics a downstream user saw over the
    # 16 example programs, across six files [measured 2026-08-17]. Expression
    # overrides all four; a leaf refuses at the same point it always did,
    # so the runtime is unchanged and the static story stops being a lie.
    @property
    def children(self) -> tuple[Atom, ...]:
        raise TypeError(_leaf_refusal_message(self, "has no children"))

    def __len__(self) -> int:
        raise TypeError(_leaf_refusal_message(self, "has no length"))

    # Declaring __len__ above would otherwise route bool() through it and
    # make every leaf atom raise where it used to be truthy. Expression overrides
    # this to keep refusing comparison terms.
    def __bool__(self) -> bool:
        return True

    def __iter__(self) -> Iterator[Atom]:
        raise TypeError(_leaf_refusal_message(self, "is not iterable"))

    def __getitem__(self, i: int | slice) -> Any:
        raise TypeError(_leaf_refusal_message(self, "is not indexable"))

    # Arithmetic operators construct terms on symbolic atoms. Rich
    # comparisons compare atom values in the engine's total order; comparison
    # terms use explicit heads such as S[">="](left, right). Equality stays
    # equality everywhere; its term is x.eq(y).

    def _build(self, op: str, other: Any, flipped: bool = False) -> Expression:  # noqa: FBT001, FBT002  -- the boolean is established API data and positional compatibility is part of the call shape
        left, right = (encode(other), self) if flipped else (self, encode(other))
        return _expression_atoms((Symbol(op), left, right))

    # Runtime implementations are generated after Expression is defined. These
    # signatures keep the dynamic class construction explicit to type
    # checkers without duplicating any lowering decision.
    if TYPE_CHECKING:

        def __add__(self, other: Any) -> Expression: ...
        def __radd__(self, other: Any) -> Expression: ...
        def __sub__(self, other: Any) -> Expression: ...
        def __rsub__(self, other: Any) -> Expression: ...
        def __mul__(self, other: Any) -> Expression: ...
        def __rmul__(self, other: Any) -> Expression: ...
        def __truediv__(self, other: Any) -> Expression: ...
        def __rtruediv__(self, other: Any) -> Expression: ...
        def __floordiv__(self, other: Any) -> Expression: ...
        def __rfloordiv__(self, other: Any) -> Expression: ...
        def __mod__(self, other: Any) -> Expression: ...
        def __rmod__(self, other: Any) -> Expression: ...
        def __pow__(self, other: Any) -> Expression: ...
        def __rpow__(self, other: Any) -> Expression: ...
        def __matmul__(self, other: Any) -> Expression: ...
        def __rmatmul__(self, other: Any) -> Expression: ...
        def __lshift__(self, other: Any) -> Expression: ...
        def __rlshift__(self, other: Any) -> Expression: ...
        def __rshift__(self, other: Any) -> Expression: ...
        def __rrshift__(self, other: Any) -> Expression: ...
        def __and__(self, other: Any) -> Expression: ...
        def __rand__(self, other: Any) -> Expression: ...
        def __or__(self, other: Any) -> Expression: ...
        def __ror__(self, other: Any) -> Expression: ...
        def __xor__(self, other: Any) -> Expression: ...
        def __rxor__(self, other: Any) -> Expression: ...
        def __invert__(self) -> Expression: ...
        def __neg__(self) -> Expression: ...
        def __abs__(self) -> Expression: ...
        def __lt__(self, other: Any) -> bool: ...
        def __le__(self, other: Any) -> bool: ...
        def __gt__(self, other: Any) -> bool: ...
        def __ge__(self, other: Any) -> bool: ...

    def __pos__(self) -> Self:
        """Return this atom unchanged, Python's unary-plus identity law."""
        return self

    def eq(self, other: Any) -> Expression:
        """The equality TERM, (== self other); == itself compares atoms."""
        return self._build("==", other)

    def ne(self, other: Any) -> Expression:
        return _expression_atoms((Symbol("not"), self.eq(other)))

    def alpha(self, other: Any) -> Expression:
        """The alpha-equality TERM, (=alpha self other); alpha_eq answers now.

        The nearest-relative spelling of the head whose `=` marker Python
        cannot carry, exactly as eq() spells ==; compiled bodies write the
        same test as a bare alpha(x, y) call, and fn["=alpha"] stays the
        exact door.
        """
        return self._build("=alpha", other)

    # Ordering, for the same reason eq() exists and by the same construction.
    # The rich-comparison operators cannot carry these: `<` between two atoms
    # is already engine sort order, which is what sorted() needs, so `V.age >=
    # 18` is refused rather than silently meaning one of two things. That
    # refusal is right, but it left ordering as the ONE part of the term
    # vocabulary with no short spelling -- and_/or_/not_/if_/in_ cover the
    # connectives and eq/ne cover equality -- so the documentation reached for
    # the refused operator three times, in the match docstring, the guide, and
    # the guard's own error message [measured 2026-08-31].
    def gt(self, other: Any) -> Expression:
        """The strictly-greater TERM, (> self other)."""
        return self._build(">", other)

    def ge(self, other: Any) -> Expression:
        """The greater-or-equal TERM, (>= self other)."""
        return self._build(">=", other)

    def lt(self, other: Any) -> Expression:
        """The strictly-less TERM, (< self other)."""
        return self._build("<", other)

    def le(self, other: Any) -> Expression:
        """The less-or-equal TERM, (<= self other)."""
        return self._build("<=", other)

    @property
    def vars(self) -> tuple[Variable, ...]:
        """The variables in first-appearance order; none means ground.

        The variables THEMSELVES, not their names, so what this answers is
        what :meth:`subs` and :meth:`unify` accept and a round trip composes:
        ``template.subs(dict(zip(pattern.vars, values)))``. Names were what it
        answered once, and a name cannot say whether it means a variable or a
        symbol on a surface that has both. ``not atom.vars`` still reads
        "ground", because an empty tuple is still empty.
        """
        from .atoms import _variables  # noqa: PLC0415  -- atoms owns tree traversal

        return tuple(Variable(name) for name in _variables(self))

    def map(self, transform: Callable[[Atom], Atom]) -> Atom:
        """Transform every node, children before parents, without recursion."""
        from .atoms import _map_atoms  # noqa: PLC0415  -- atoms owns tree traversal

        return _map_atoms(self, transform)

    def alpha_eq(self, other: Atom) -> bool:
        """Whether two atoms differ only by consistent variable renaming."""
        from .atoms import _alpha_eq  # noqa: PLC0415  -- atoms owns equivalence

        return _alpha_eq(self, other)

    def unify(self, other: Atom, *more: Atom) -> Mapping[Atom, Atom] | None:
        """Unify with the others, returning bindings or ``None``.

        Variadic means SIMULTANEOUS: every operand must agree under ONE
        substitution, folded through one shared binding store, so several
        rule heads unify at once the way two always did. The keys are the
        VARIABLES themselves, which is the currency :meth:`subs` accepts,
        so ``template.subs(pattern.unify(fact))`` is the round trip. They
        were plain names once, and a name cannot say whether it means a
        variable or a symbol in a language that has both.
        """
        from .atoms import unify  # noqa: PLC0415  -- atoms owns unification

        return unify(self, other, *more)

    def subs(self, bindings: Mapping[Atom, Any] | Any) -> Atom:
        """Replace each atom the bindings name, everywhere it occurs.

            pattern = S.job(V.who, V.rank)
            pattern.subs(pattern.unify(S.job(S.ada, 9)))   # (job ada 9)
            S.hired(V.who).subs(space.match(pattern)[0])   # (hired ada)
            S.greet(S.name).subs({S.name: "ada"})          # (greet "ada")

        The KEY says what is being replaced, so a variable hole and a
        placeholder symbol are different substitutions rather than one string
        meaning whichever the door happens to have chosen. ``unify`` produces
        variable keys; a ``bind()`` scope at the evaluation doors accepts either.

        An answer ``Row`` is accepted directly, because its columns ARE the
        query's variable names. It is the library's other producer of
        bindings, and it could not be fed back either.

        Sugar over :meth:`map`, which is the rung below and stays reachable:
        this is ``atom.map(lambda item: bindings.get(item, item))`` with the
        keys and values encoded. Nothing consumed a substitution before this,
        so both producers answered in a currency the library did not accept,
        and two tests had written the recursive walk by hand.
        """
        from .atoms import _to_atom  # noqa: PLC0415  -- atoms owns encoding
        from .results import Row  # noqa: PLC0415  -- results owns the answer row

        if isinstance(bindings, Row):
            bindings = {
                Variable(column): bindings[index]
                for index, column in enumerate(type(bindings)._columns)  # Row's own contract; no public name can hold the columns, because
                # every attribute name on a Row is reserved for a column.
            }
        if not bindings:
            return self
        replacements = {
            _to_atom(key): _to_atom(value) for key, value in bindings.items()
        }
        return self.map(lambda item: replacements.get(item, item))

    @overload
    def cast[CastT](self, type_: type[CastT], /) -> CastT: ...

    @overload
    def cast(self, type_: Atom | str, /) -> Any: ...

    def cast(self, type_: Any, /) -> Any:
        """Cast this atom through the ambient space's type discipline."""
        from . import _ambient_space  # noqa: PLC0415  -- root owns ambient scope

        return _ambient_space().cast(self, type_)

    def __setattr__(self, _name: str, _value: Any, /) -> None:
        msg = "atoms are immutable"
        raise AttributeError(msg)

    def __delattr__(self, _name: str, /) -> None:
        msg = "atoms are immutable"
        raise AttributeError(msg)

    def __copy__(self) -> Atom:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Atom:
        return self

    def to_wire(self) -> list:
        raise NotImplementedError

    @property
    def metatype(self) -> str:
        raise NotImplementedError

    # Casting refusals. Nothing here consults the engine: int(x) reads the
    # datum it was handed and never runs a program. Grounded overrides these for
    # the values that genuinely are numbers.

    def _not_a_message(self, target: str) -> str:
        return (
            f"cannot read {self} as a Python {target}: it is a {self.metatype} "
            f"in MeTTa, and only a grounded number converts. Evaluate it first "
            f"if it is a program: space.eval(atom)."
        )

    def __int__(self) -> int:
        raise TypeError(self._not_a_message("int"))

    def __float__(self) -> float:
        raise TypeError(self._not_a_message("float"))

    def __complex__(self) -> complex:
        raise TypeError(self._not_a_message("complex"))

    def __index__(self) -> int:
        raise TypeError(self._not_a_message("int"))

    def __format__(self, spec: str) -> str:
        return str(self) if not spec else format(str(self), spec)


class Symbol(Atom):
    """A symbol: a name that denotes itself. Coffee, likes, &self.

    A symbol is not a string: Symbol('foo') == 'foo' is False on purpose,
    because 'foo' the text and foo the name are different atoms in MeTTa,
    and folding them together is the ambiguity the wire encoding removes.
    """

    __slots__ = {
        "_wire": "the cached wire form, built on first crossing",
        "name": "the symbol's name, exactly as written in source",
    }
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Atom):
            return NotImplemented
        if isinstance(other, Handle):
            return other == self
        return isinstance(other, Symbol) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("sym", self.name))

    def __reduce__(self):
        return _wire_sym, (self.name,)

    def __str__(self) -> str:
        return self.name

    def to_wire(self) -> list:
        # Atoms are immutable, so the wire form is computed once and kept;
        # the S builder interns symbols, so a head symbol's wire cell is
        # shared by every fact that names it. Wire lists are read-only by
        # contract on both sides of the boundary.
        wire = getattr(self, "_wire", None)
        if wire is None:
            wire = ["s", _encodable(self.name)]
            object.__setattr__(self, "_wire", wire)
        return wire

    @property
    def metatype(self) -> str:
        return "Symbol"

    def __call__(self, *args: Any, **kwargs: Any) -> Expression:
        """A symbol applied is an expression headed by it: S.likes(S.Ada).

        A bare symbol carries no parameter names, so it cannot decide where a
        keyword belongs in MeTTa's positional application and refuses with the
        positional remedy. Bound functions and Defined values carry signatures.
        """
        if kwargs:
            display = f"S.{self.name}"
            raise refuse_unknown_keywords(display, tuple(kwargs))
        return _applied_atoms(self, args, {})


def _applied_atoms(head: Atom, args: tuple, kwargs: dict) -> Expression:
    """Build a head's positional children and optional Python-call keyword tail."""
    children = [head, *(encode(a) for a in args)]
    if kwargs:
        pairs = tuple(
            _expression_atoms((Symbol(name), encode(value)))
            for name, value in kwargs.items()
        )
        children.append(_expression_atoms((Symbol("Kwargs"), *pairs)))
    return _expression_atoms(children)


class Variable(Atom):
    """A variable: a hole a match may fill. $x in source."""

    __slots__ = {
        "_wire": "the cached wire form, built on first crossing",
        "name": "the variable's name without the $ sigil",
    }
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Variable) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("var", self.name))

    def __reduce__(self):
        return _wire_var, (self.name,)

    def __str__(self) -> str:
        return f"${self.name}"

    def to_wire(self) -> list:
        wire = getattr(self, "_wire", None)
        if wire is None:
            wire = ["v", _encodable(self.name)]
            object.__setattr__(self, "_wire", wire)
        return wire

    @property
    def metatype(self) -> str:
        return "Variable"


class Grounded(Atom):
    """A grounded value: a host value carried whole.

    Strings, numbers and booleans have native MeTTa terms. Anything else
    crosses as an object reference, stays the same object on the way back,
    and unifies by identity, which is the equality the engine applies to it.

    Equality carries the engine's own two relations, one per operand kind.
    Against a RAW Python value it is the engine's == operator, ergonomic on
    purpose: a grounded primitive compares equal to its raw value of the
    same term, so run("!(+ 1 2)") answers compare with == 3, while
    Grounded(3.0) == 3 is False exactly as (== 3.0 3) is False, an integer
    and a float being different terms. Against ANOTHER ATOM it is the engine's
    unification: an integer atom never equals a float atom, 0.0 and -0.0 are
    two atoms, one NaN atom equals another, so membership, removal and a
    Counter of atoms agree with what a space actually stores and matches.
    True stays distinct from 1 the way MeTTa keeps Bool and Number apart.
    A symbol never equals a string; that distinction is the point.
    """

    __slots__ = {
        "_wire_value": "the private carrier to reuse on a later crossing",
        "value": "the ground Python value this atom carries",
    }
    __match_args__ = ("value",)
    _wire_value: Any | None
    value: Any

    def __call__(self, *args: Any, **kwargs: Any) -> Expression:
        """A grounded head applied is an expression headed by it, the same
        law a symbol has: `np_arange(4, step=2)` builds
        `(np_arange 4 (Kwargs (step 2)))`, which is what the seam's py-call
        route evaluates. Building is not calling: the term is data until
        something evaluates it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _applied_atoms(self, args, kwargs)

    # Truthiness follows equality, or `if answer:` reads a MeTTa False as
    # true. Without this the library forces the PEP 8 violation it warns
    # against: on a rule answering False, the conformant
    # `any(a for a in answers)` was True and the explicit
    # `any(a == True for a in answers)` was False, so a user tidying away
    # the E712 suppression introduced a silent wrong answer
    # [measured 2026-08-17]. Expression.__bool__ already guards this class of
    # mistake for comparison terms; Grounded had no guard for the same one.
    # Restricted to bool on purpose: a Number 0 is not falsehood in MeTTa,
    # so Grounded(0) and Grounded("") stay truthy.
    def __bool__(self) -> bool:
        value = self.value
        return value if isinstance(value, bool) else True

    def __init__(self, value: Any) -> None:
        object.__setattr__(self, "value", _normalize_grounded(value))
        object.__setattr__(self, "_wire_value", None)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Grounded):
            # Atom against atom is the engine's unification, so identity
            # questions (dict keys, membership, remove) answer as the
            # engine's own storage answers them.
            return _ground_identical(self.value, other.value)
        if isinstance(other, Atom):
            return False
        # A raw tuple is the transparent Expression spelling at every Python
        # value door. Explicit Grounded(tuple) is the opaque spelling; letting
        # it equal the same raw tuple would make that tuple equal both an
        # Expression and an unequal Grounded atom, violating transitivity.
        if isinstance(other, tuple):
            return False
        # Raw Python value on the other side, and the SAME relation: the
        # engine's == over crossed values is its unification now, so a
        # comparison made in Python and one made in an equation cannot
        # disagree.
        return _ground_identical(self.value, other)

    def __hash__(self) -> int:
        # Hash agrees with equality: a primitive hashes as its value, so
        # Grounded(3) and 3 land in the same bucket; an object hashes by identity.
        # NaN atoms are all one atom to unification, and CPython hashes each
        # nan float by object identity, so they need one shared bucket.
        if _is_primitive(self.value):
            if type(self.value) is float and math.isnan(self.value):
                return hash(("gnd", "nan"))
            return hash(self.value)
        return hash(("gnd", id(self.value)))

    def __reduce__(self):
        if self._wire_value is not None or not _is_primitive(self.value):
            msg = (
                "a grounded opaque object has process-local identity and "
                "cannot be pickled; encode a stable value instead"
            )
            raise TypeError(
                msg
            )
        return Grounded, (self.value,)

    # Grounded values are atoms at the operator boundary.  They inherit the
    # base class's term builders, making G(value) the explicit lift from host
    # data into staged syntax.  Their carried Python value remains available
    # through .value and through the numeric conversion methods below.

    # Grounded primitives order like their values, so answers sort and
    # compare with plain numbers: max(rows.age) and Grounded(7) >= 5
    # both mean what they read as. Anything else refuses loudly.

    def _ordered(self, other: Any):
        mine = self.value
        theirs = other.value if isinstance(other, Grounded) else other
        # Booleans do not order: the engine keeps Bool apart from Number
        # and refuses (< True 5), so Python must not answer it either.
        if isinstance(mine, bool) or isinstance(theirs, bool):
            return None
        if (
            _is_primitive(mine)
            and _is_primitive(theirs)
            and (isinstance(mine, str) == isinstance(theirs, str))
        ):
            return mine, theirs
        return None

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            from .atoms import order_key  # noqa: PLC0415  -- atoms owns the order

            return order_key(self) < order_key(other)
        pair = self._ordered(other)
        if pair is None:
            raise _atom_plain_order_error(self, other, "<")
        return pair[0] < pair[1]

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_le(self, other)
        pair = self._ordered(other)
        if pair is None:
            raise _atom_plain_order_error(self, other, "<=")
        return pair[0] <= pair[1]

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_gt(self, other)
        pair = self._ordered(other)
        if pair is None:
            raise _atom_plain_order_error(self, other, ">")
        return pair[0] > pair[1]

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_ge(self, other)
        pair = self._ordered(other)
        if pair is None:
            raise _atom_plain_order_error(self, other, ">=")
        return pair[0] >= pair[1]

    def __str__(self) -> str:
        v = self.value
        if isinstance(v, bool):
            # Source spelling. The parser reads True and False; the engine
            # holds them as the atoms true and false.
            return "True" if v else "False"
        if isinstance(v, str):
            # The same five escapes the engine's swrite emits and its
            # reader decodes, so a printed string stays on one line and
            # both printers agree byte for byte.
            escaped = (
                v.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\t", "\\t")
                .replace("\r", "\\r")
            )
            return '"' + escaped + '"'
        if isinstance(v, float):
            return _float_text(v)
        if isinstance(v, Fraction):
            return f"{v.numerator}r{v.denominator}"
        if isinstance(v, int):
            return repr(v)
        return _object_str(v)

    def _number(self, target: str) -> int | float | Fraction:
        v = self.value
        if isinstance(v, bool) or not isinstance(v, (int, float, Fraction)):
            msg = (
                f"cannot read {self} as a Python {target}: it is not a Number "
                f"in MeTTa. int(atom.value) is how to say parse this text."
            )
            raise TypeError(
                msg
            )
        return v

    def __int__(self) -> int:
        return int(self._number("int"))

    def __float__(self) -> float:
        return float(self._number("float"))

    def __complex__(self) -> complex:
        return complex(self._number("complex"))

    def __index__(self) -> int:
        v = self.value
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(self._not_a_message("int"))
        return v

    def __format__(self, spec: str) -> str:
        if not spec:
            return str(self)
        return format(self.value, spec) if _is_primitive(self.value) else format(str(self), spec)

    def __repr__(self) -> str:
        # Grounded(42) and Grounded('text'), not Grounded('42'): the repr shows the value it
        # carries, so a number never reads like a string.
        if _is_primitive(self.value):
            return f"Grounded({self.value!r})"
        return f"Grounded({_object_str(self.value)})"

    def to_wire(self) -> list:
        v = self.value
        if self._wire_value is not None:
            return ["o", self._wire_value]
        if type(v) is bool:
            return ["b", "true" if v else "false"]
        if type(v) is str:
            return ["g", _encodable(v)]
        if type(v) in (int, float):
            return ["n", v]
        if isinstance(v, Box):
            return ["o", v]
        return ["o", boxed(v)]

    @property
    def metatype(self) -> str:
        return "Grounded"


class Handle(Grounded):
    """A grounded executable reference carried as an atom.

    Space handles and native extension handles are the two concrete species,
    and the canonical glossary's law holds in the class tree: a Handle IS a
    Grounded species, so ``isinstance(handle, Grounded)`` answers True. A
    handle owns behavior and identity outside the term tree while remaining
    usable wherever MeTTa accepts a grounded operand. The ``value`` slot is
    deliberately never filled: a handle carries identity rather than a
    payload, so a ``.value`` read raises AttributeError naming the slot, and
    every Grounded branch that unwraps payloads guards with ``getattr``.
    """

    __slots__ = ()
    # A handle deconstructs to nothing: Grounded's (value,) would send
    # match statements into the unset slot.
    __match_args__ = ()

    # Reason below rather than beside the pragma, which pylint parses as a
    # bare message list: Grounded.__init__ takes the payload a handle has
    # none of, so not chaining is the contract.
    # pylint: disable-next=super-init-not-called
    def __init__(self) -> None:
        """A handle carries identity, not a payload: the value slot stays
        deliberately unset, so construction does nothing, and a concrete
        species calls this instead of Grounded's value-taking form.

        Not chaining is the point rather than an omission: Grounded's
        __init__ stores a value into the slot this species leaves unset, so
        calling it would give every handle a payload the match protocol
        above deliberately removed.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __call__(self, *args: Any, **kwargs: Any) -> Expression:
        del args, kwargs
        msg = (
            f"{type(self).__name__} is not applied: a handle names a live "
            f"engine object, so call its methods, or place it in a built "
            f"term as an operand"
        )
        raise TypeError(msg)

    # A handle is presence: its truth is that it exists, never a payload's.
    def __bool__(self) -> bool:
        return True

    # Raw-value ordering refuses: there is no payload to order by, and
    # atom-vs-atom ordering goes through order_key, which is getattr-safe.
    def _ordered(self, other: Any):
        del other

    @property
    def metatype(self) -> str:
        return "Grounded"


class _NativeHandle(Handle):
    """A native engine value held by reference: the identity carrier for
    anything a C extension hands back as a blob (EXTENDING.md section 3).

    The value itself never crosses; this atom carries a registry id and
    the blob's own printed text. Handing it back to the engine resolves
    the very same blob, so identity, mutation and accessor calls all see
    one object. Unpacking is whatever accessors the owning extension
    registered; the handle is deliberately opaque here, for any blob
    type, with nothing per-type anywhere.

    release() retracts the engine-side registry entry that keeps the
    blob alive; further use of a released handle raises in the engine,
    naming the id. Garbage collection releases as a safety net, but an
    interpreter tearing down cannot promise engine calls, so explicit
    release is the deterministic path.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = {
        "_released": "whether release() already retracted the registry entry",
        "ident": "the engine-side registry id keeping the value alive",
        "text": "the printed form the engine gave this handle",
    }
    __match_args__ = ("ident", "text")
    ident: int
    text: str
    _released: bool

    def __init__(self, ident: int, text: str) -> None:
        super().__init__()
        object.__setattr__(self, "ident", ident)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "_released", False)

    def __str__(self) -> str:
        return self.text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NativeHandle) and other.ident == self.ident

    def __hash__(self) -> int:
        return hash(("handle", self.ident))

    def __reduce__(self):
        msg = (
            "a native handle has process-local identity and cannot be "
            "pickled; read it out through its extension's accessors instead"
        )
        raise TypeError(
            msg
        )

    def to_wire(self) -> list:
        return ["h", self.ident, self.text]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exception: object) -> None:
        self.release()

    def release(self) -> None:
        """Retract the engine-side registry entry keeping the value alive.

        Handles are context managers, so the deterministic spelling is the
        file-object idiom: `with` the handle and it releases on exit.
        """
        if self._released:
            return
        object.__setattr__(self, "_released", True)
        from . import _engine  # noqa: I001,PLC0415 - atoms stay the base layer; the engine is reached only on release

        runtime = _engine.active_runtime()
        if runtime is not None:
            runtime.do("metta_py_handle_release", self.ident)

    def __del__(self) -> None:
        # Interpreter teardown cannot promise engine calls, so collection
        # is a best-effort release and explicit release() the deterministic
        # path.
        with contextlib.suppress(Exception):
            self.release()


class Expression(Atom):
    """An expression: an ordered sequence of atoms. (likes Ada Coffee).

    Sequence-shaped, so Python's own idioms apply: expr[0] is car-atom,
    len(expr) is size-atom, and case [head, *args] destructures it. A single
    iterable supplies the children; a Space supplies its assembly-order
    listing snapshot. None of that costs an engine call after construction.
    """

    __slots__ = {
        "_hash": "the cached structural hash, computed on first use",
        "_wire": "the cached wire form, built on the first crossing",
        "children": "the ordered child atoms, as a tuple",
    }
    __match_args__ = ("children",)
    children: tuple[Atom, ...]
    _hash: int | None

    def __init__(self, *children: Any) -> None:
        """Build from one iterable snapshot or positional Python values."""
        parts: Iterable[Any]
        candidate = children[0] if len(children) == 1 else None
        if (
            isinstance(candidate, Handle)
            and getattr(type(candidate), "_expression_listing_snapshot", False)
            is True
        ) or (
            candidate is not None
            and not isinstance(candidate, (str, bytes, Atom))
            and isinstance(candidate, Iterable)
        ):
            parts = candidate
        else:
            parts = children
        _set_children(
            self,
            tuple(
                child if isinstance(child, Atom) else encode(child)
                for child in parts
            ),
        )
        _set_hash(self, None)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Expression, tuple)):
            return NotImplemented
        # Iterative: nested tuple equality would recurse to the term's
        # depth, and depth is data here. Compare raw tuple leaves directly
        # instead of re-encoding them: an explicit host conversion such as
        # Path -> Symbol need not preserve the host value's equality or hash.
        stack: list[tuple[Expression, Expression | tuple[Any, ...]]] = [(self, other)]
        while stack:
            a, b = stack.pop()
            if a is b:
                continue
            b_children = b.children if isinstance(b, Expression) else b
            if len(a.children) != len(b_children):
                return False
            for x, y in zip(a.children, b_children, strict=True):
                if x is y:
                    continue
                if isinstance(x, Expression) and isinstance(y, (Expression, tuple)):
                    stack.append((x, y))
                elif x != y:
                    return False
        return True

    def __hash__(self) -> int:
        # Cached, and computed bottom-up without recursion on first use.
        cached = self._hash
        if cached is not None:
            return cached
        order: list[Expression] = []
        stack: list[Expression] = [self]
        while stack:
            node = stack.pop()
            if node._hash is None:
                order.append(node)
                stack.extend(c for c in node.children if isinstance(c, Expression) and c._hash is None)
        for node in reversed(order):
            if node._hash is None:
                # Expression is the transparent tuple representation, so its
                # cached structural hash is exactly Python's tuple hash.
                value = hash(node.children)
                _set_hash(node, value)
        return cast(int, self._hash)

    def __reduce__(self):
        return Expression, (self.children,)

    def __rich_repr__(self):
        """rich.pretty expands an expression by its children, so a deep
        term prints as an indented tree instead of one long line. Only
        rich consults this; plain repr() is unchanged.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        yield from self.children

    def __str__(self) -> str:
        # Iterative: deep expressions are ordinary data here, and a printer
        # must not hit Python's recursion ceiling on them.
        parts: list[str] = []
        stack: list[Any] = [self]
        while stack:
            item = stack.pop()
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Expression):
                parts.append("(")
                tail: list[Any] = []
                for i, child in enumerate(item.children):
                    if i:
                        tail.append(" ")
                    tail.append(child)
                tail.append(")")
                stack.extend(reversed(tail))
            else:
                parts.append(str(item))
        return "".join(parts)

    def __len__(self) -> int:
        return len(self.children)

    def __bool__(self) -> bool:
        # A comparison or boolean TERM has no truth value: bool() on one is
        # almost always Python's sort, an if reading (V.a < V.b) as a fact,
        # or `and` chaining terms that wanted &. Refusing here keeps those
        # mistakes loud; every other expression stays truthy like any object.
        head = self.head
        if isinstance(head, Symbol) and head.name in (
            "<",
            "<=",
            ">",
            ">=",
            "==",
            "and",
            "or",
            "not",
            "xor",
        ):
            msg = (
                f"{self} is a comparison TERM, not a truth value. Python "
                "Language Reference section 6.10: a chained comparison uses "
                "truthiness between its terms. Write the conjunction explicitly, "
                "as S.le(1, V.x) & S.le(V.x, 10), or use a named predicate; "
                "then evaluate it with space.eval or pass it as where=."
            )
            raise _grounded_type_error(
                msg,
                ground=_PYTHON_COMPARISON_GROUND,
            )
        return True

    def __getitem__(self, i: int | slice) -> Any:
        selected = self.children[i]
        return _expression_atoms(selected) if isinstance(i, slice) else selected

    def index(self, value: Atom, start: int = 0, stop: int | None = None) -> int:
        if stop is None:
            return self.children.index(value, start)
        return self.children.index(value, start, stop)

    def count(self, value: Atom) -> int:
        return self.children.count(value)

    def __iter__(self) -> Iterator[Atom]:
        return iter(self.children)

    def to_wire(self) -> list:
        # Memoized lazily, exactly as Symbol and Variable are: the slot is written
        # by the first crossing and never on construction, so a term that
        # is built and thrown away pays nothing. Iterative for the same
        # reason __str__ is: depth is data.
        #
        # Only the node that was ASKED caches. A child expression keeps its
        # own slot unwritten, because the parent's cached list already holds
        # that subtree and writing a slot per node would charge every
        # one-shot term for a cache nothing reads [tested
        # test_expr_defers_its_wire_form_until_asked].
        wire = getattr(self, "_wire", None)
        if wire is not None:
            return wire
        out: list = ["e", []]
        stack: list[tuple[Expression, list]] = [(self, out[1])]
        while stack:
            node, sink = stack.pop()
            for child in node.children:
                if isinstance(child, Expression):
                    slot: list = ["e", []]
                    sink.append(slot)
                    stack.append((child, slot[1]))
                else:
                    sink.append(child.to_wire())
        _set_wire(self, out)
        return out

    @property
    def metatype(self) -> str:
        return "Expression"

    @property
    def head(self) -> Atom | None:
        return self.children[0] if self.children else None

    @property
    def args(self) -> tuple[Atom, ...]:
        return self.children[1:]


def _operator_form(form: Any, operands: dict[str, Atom]) -> Atom:
    """Build one immutable lowering template with its operands substituted."""
    if isinstance(form, tuple):
        if not form or not isinstance(form[0], str):
            msg = f"invalid operator template {form!r}"
            raise RuntimeError(msg)
        return _expression_atoms(
            (Symbol(form[0]), *(_operator_form(item, operands) for item in form[1:]))
        )
    if isinstance(form, str):
        return operands.get(form, Symbol(form))
    return encode(form)


def _apply_operator_lowering(
    entry: OperatorLowering,
    atom: Atom,
    other: Any = None,
    *,
    flipped: bool = False,
) -> Expression:
    """Apply one table entry; ``taken`` entries never reach this door."""
    if entry.form is None:
        msg = f"operator lowering {entry.dunder} has no form"
        raise RuntimeError(msg)
    if entry.arity == 1:
        operands = {"$value": atom}
    else:
        encoded = encode(other)
        left, right = (encoded, atom) if flipped else (atom, encoded)
        operands = {"$left": left, "$right": right}
    form: Any = (
        (entry.form, *operands.values())
        # policy-inventory-exempt: mechanism-internal; reason=symbol and provided are the two lowering-table kinds whose form is a MeTTa head to apply to the operands; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
        if entry.kind in {"symbol", "provided"}
        else entry.form
    )
    lowered = _operator_form(form, operands)
    if not isinstance(lowered, Expression):
        msg = f"operator lowering {entry.dunder} did not build an expression"
        raise RuntimeError(msg)  # noqa: TRY004  -- a non-Expression means a corrupt lowering-table row, an internal invariant break, not a caller type error
    return lowered


def _operator_method(
    entry: OperatorLowering, *, reflected: bool = False
) -> Callable[..., Expression]:
    """Specialize one dunder once and retain its table row for inspection."""
    name = entry.reflected if reflected else entry.dunder
    if name is None:
        msg = f"operator lowering {entry.dunder} has no reflected spelling"
        raise RuntimeError(msg)
    # policy-inventory-exempt: mechanism-internal; reason=symbol and provided are the two lowering-table kinds whose form is a MeTTa head to apply to the operands; evidence=extensions/python/metta/_operator_lowerings.py:OperatorLowering
    if entry.kind in {"symbol", "provided"}:
        if not isinstance(entry.form, str):
            msg = f"operator lowering {entry.dunder} has no symbol"
            raise RuntimeError(msg)
        symbol = Symbol(entry.form)
        if entry.arity == 1:

            def unary_symbol(self: Atom, *, _symbol: Symbol = symbol) -> Expression:
                return _expression_atoms((_symbol, self))

            operator: Callable[..., Expression] = unary_symbol
        elif reflected:

            def reflected_symbol(
                self: Atom, other: Any, *, _symbol: Symbol = symbol
            ) -> Expression:
                return _expression_atoms((_symbol, encode(other), self))

            operator = reflected_symbol
        else:

            def binary_symbol(
                self: Atom, other: Any, *, _symbol: Symbol = symbol
            ) -> Expression:
                return _expression_atoms((_symbol, self, encode(other)))

            operator = binary_symbol
    elif entry.arity == 1:

        def unary(self: Atom) -> Expression:
            return _apply_operator_lowering(entry, self)

        operator = unary
    else:

        def binary(self: Atom, other: Any) -> Expression:
            return _apply_operator_lowering(entry, self, other, flipped=reflected)

        operator = binary
    operator.__name__ = name
    operator.__qualname__ = f"Atom.{name}"
    operator.__doc__ = f"Lower {entry.syntax} through the {entry.kind} operator-table entry."
    operator.__dict__["__metta_lowering__"] = entry
    return operator


def _install_operator_lowerings() -> None:
    """Generate every term-building or refusing dunder from the table."""
    for entry in OPERATOR_LOWERINGS:
        if entry.kind == "taken":
            continue
        setattr(Atom, entry.dunder, _operator_method(entry))
        if entry.reflected is not None:
            setattr(Atom, entry.reflected, _operator_method(entry, reflected=True))


_install_operator_lowerings()


#: The term-building method for each comparison operator, so a refusal names
#: the nearest rung rather than the furthest one. The bracket door still works
#: and is still shown, because it is the rung below and the ladder never
#: shrinks; naming only it sent a caller past the method that exists.
_ORDER_METHOD = {"<": "lt", "<=": "le", ">": "gt", ">=": "ge"}


def _atom_plain_order_error(atom: Atom, other: Any, operator: str) -> TypeError:
    """Ground a refused atom/plain comparison in Python's data model."""
    method = _ORDER_METHOD[operator]
    message = (
        f"{operator} is not defined between {type(atom).__name__} and "
        f"{type(other).__name__}. Python Language Reference section 3.3.1 "
        "delegates unsupported rich comparisons. Compare two atoms for engine "
        f"order, unwrap a grounded primitive with .value, or build the MeTTa "
        f"relation with left.{method}(right), whose longhand is "
        f"S[{operator!r}](left, right)."
    )
    return _grounded_type_error(
        message,
        ground=_PYTHON_RICH_COMPARISON_GROUND,
    )


def _standard_order_lt(self: Atom, other: Any) -> bool:
    """Order atoms by the engine's term order; comparisons as terms use S['<']."""
    if not isinstance(other, Atom):
        raise _atom_plain_order_error(self, other, "<")
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) < order_key(other)


def _standard_order_le(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        raise _atom_plain_order_error(self, other, "<=")
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) <= order_key(other)


def _standard_order_gt(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        raise _atom_plain_order_error(self, other, ">")
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) > order_key(other)


def _standard_order_ge(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        raise _atom_plain_order_error(self, other, ">=")
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) >= order_key(other)


# Appendix stamp 6 rules plain sorting over the old ``<`` term-building
# spelling. Compiled Python comparisons lower from the AST, while quoted code
# spells the relation explicitly as ``S["<"](left, right)``.
Atom.__lt__ = _standard_order_lt  # type: ignore[method-assign]
Atom.__le__ = _standard_order_le  # type: ignore[method-assign]
Atom.__gt__ = _standard_order_gt  # type: ignore[method-assign]
Atom.__ge__ = _standard_order_ge  # type: ignore[method-assign]


# Registered so case [head, *args] matches: the Sequence pattern checks the ABC.
cast(ABCMeta, Sequence).register(Expression)

# Atoms refuse assignment, so every slot write goes through a back door.
# object.__setattr__ resolves the attribute NAME against the type on every
# call and costs 951 instructions; the slot's own descriptor is resolved
# already and costs 568 [measured 2026-08-19: minimum of three
# instructions:u runs over 200,000 writes each]. Expression writes two slots per
# construction and from_wire builds one Expression per decoded node, so the name
# lookup was being paid twice for every node of every answer.
_set_children = Expression.__dict__["children"].__set__
_set_hash = Expression.__dict__["_hash"].__set__
_set_wire = Expression.__dict__["_wire"].__set__
_new_expression = Expression.__new__


def _expression_atoms(children: Iterable[Atom]) -> Expression:
    """Build from children that have already crossed the conversion boundary."""
    expression = _new_expression(Expression)
    _set_children(expression, tuple(children))
    _set_hash(expression, None)
    return expression


# --------------------------------------------------------------------- encoding


def explicit_metta_atom(value: Any) -> Atom | None:
    """Invoke an explicit class-owned ``__metta__`` hook, if one exists."""
    cls = type(value)
    descriptor = inspect.getattr_static(cls, "__metta__", None)
    if descriptor is None or isinstance(descriptor, property):
        return None
    getter = getattr(descriptor, "__get__", None)
    hook = getter(value, cls) if getter is not None else descriptor
    if not callable(hook):
        msg = f"__metta__ on {cls.__name__} is not callable"
        raise TypeError(msg)
    result = hook()
    if not isinstance(result, Atom):
        msg = (
            f"__metta__ on {cls.__name__} returned "
            f"{type(result).__name__}, not an Atom"
        )
        raise TypeError(msg)
    return result


@singledispatch
def _encode_value(value: Any) -> Atom:
    """The open dispatch behind encode. See encode for the contract."""
    result = explicit_metta_atom(value)
    if result is not None:
        return result
    return Grounded(value)


@_encode_value.register
def _(value: Atom) -> Atom:
    return value


@_encode_value.register
def _(value: str) -> Atom:
    # A Python str is a grounded string, never a symbol. Symbols come from S.
    return Grounded(value)


@_encode_value.register
def _(value: PurePath) -> Atom:
    """A filesystem path is an engine atom, distinct from text payload."""
    return Symbol(str(value))


@_encode_value.register(bool)
@_encode_value.register(int)
@_encode_value.register(float)
def _(value: Any) -> Atom:
    return Grounded(value)


@_encode_value.register(tuple)
@_encode_value.register(list)
def _(value: Any) -> Atom:
    # A Python sequence reads as an expression, which is what (1 2 3) is.
    # To carry a list whole as one opaque value, wrap it: metta.ground([1, 2, 3]).
    return _expression_atoms(encode(v) for v in value)


@_encode_value.register(type(Ellipsis))
def _(value: Any) -> Atom:
    # Python's own gap glyph IS MeTTa's: `...` in a pattern child position is an
    # ANONYMOUS segment variable standing for a run of zero or more children,
    # and each occurrence is its own variable. The atom is the plain symbol,
    # because whether a marker is a live gap or ordinary data is decided by the
    # SIDE it sits on rather than by its shape: a pattern's `...` is a gap and a
    # stored atom's is data [source: LeaTTa MettaHyperonFull/Core/SeqSyntax.lean,
    # parseSeqAtom against parseConcreteAtom]. Before this it encoded as a
    # grounded ellipsis object, so `space[(S.A, ..., S.D)]` answered nothing.
    del value
    return Symbol("...")


# A table keyed on the value's EXACT class, consulted before the dispatch
# above. singledispatch resolves a class through its own wrapper, a dispatch
# call and a WeakKeyDictionary lookup, and that resolution is most of what
# encode costs: measured 2026-08-19 over 800,000 calls across eight leaf
# types, minimum of three instructions:u runs with the same loop calling
# nothing subtracted, 4,603 instructions per encode against 2,309 with this
# table in front, 1.99x. A dict keyed on __class__ falling through to the
# generic on a miss is what copyreg and pickle do for the same reason.
#
# Every entry is resolved by ASKING _encode_value.dispatch, so the table
# cannot answer differently from the registry it came from, and encode.register
# rebuilds it: a table still answering the old way after someone registers a
# codec would be a correctness bug bought for 2,294 instructions
# [tested test_the_type_fast_path_precedes_encode_and_survives_a_register].
#
# The concrete atom classes are named because the registry holds their BASE,
# Atom, and an exact-class table cannot find them through it. A class that is
# in neither list misses and falls through, which is what subclasses and
# abstract registrations need anyway.
_ENCODE_DIRECT: tuple[type, ...] = (Symbol, Variable, Expression, Grounded, Handle)
_ENCODE_FAST: dict[type, Callable[[Any], Atom]] = {}


def _encode_fast_rebuild() -> None:
    """Resolve every directly reachable class through the registry itself."""
    resolved = {
        cls: _encode_value.dispatch(cls)
        for cls in (*_ENCODE_DIRECT, *_encode_value.registry)
        if isinstance(cls, type)
    }
    _ENCODE_FAST.clear()
    _ENCODE_FAST.update(resolved)


def encode(value: Any) -> Atom:
    """Turn a Python value into an atom.

    Open by design: a class you own implements __metta__; a class you do not
    own is taught through encode.register, which is functools.singledispatch.
    Anything unregistered without __metta__ is carried whole as a grounded
    object, the same rule the engine itself applies to a host value.
    """
    handler = _ENCODE_FAST.get(value.__class__)
    if handler is not None:
        return handler(value)
    mentioned = callable_mention(value)
    if mentioned is not None:
        return Symbol(mentioned)
    return _encode_value(value)


def _encode_register(cls: Any, func: Any = None) -> Any:
    """encode.register, rebuilding the fast table at every registration.

    singledispatch.register has three shapes and all three land here.
    `register(cls, implementation)` and the bare `@register` on an annotated
    function both register at once and answer the implementation; only
    `@register(cls)` defers, and it is told apart by answering something that
    is not the argument it was given, which is the decorator functools built.
    Deferring the rebuild with it keeps the table correct for that shape too.
    """
    outcome = _encode_value.register(cls, func)
    if func is None and outcome is not cls:

        def _deferred(implementation: Any) -> Any:
            registered = outcome(implementation)
            _encode_fast_rebuild()
            return registered

        return _deferred
    _encode_fast_rebuild()
    return outcome


# Attached through __dict__ because the names live on the function OBJECT:
# a plain `encode.register = ...` is what a type checker reads as adding an
# attribute to a Callable, and both checkers here refuse it.
encode.__dict__.update(
    register=_encode_register,
    registry=_encode_value.registry,
    dispatch=_encode_value.dispatch,
)

_encode_fast_rebuild()


def decode(atom: Any) -> Any:
    """Unwrap grounded values to Python, recursively, leaving structure alone.

    A Grounded becomes its value, an Expression becomes an Expression of decoded children
    only when asked (this returns the expression as is), and symbols and
    variables stay atoms. Named for what it does; results already compare
    ergonomically without it, so it is never on a default path.
    """
    # getattr, not .value: a Handle is a Grounded species whose value slot
    # is deliberately unset (identity, not payload), and it decodes to
    # ITSELF, which is what a live reference means host-side.
    return getattr(atom, "value", atom) if isinstance(atom, Grounded) else atom


# Decoded symbols and variables intern per name: their equality and hash are by
# name already, and a query answering thousands of rows repeats a vocabulary.
# Eviction changes only object allocation because equality is by value, while
# bounding names supplied by a remote peer prevents permanent process growth.
#
# ONE tier, read without the lock and mutated under it. It used to be two, a
# 256-entry FIFO in front of a 512-entry LRU, so that a hot name answered
# without taking _STATE_LOCK. That split earned its keep only while the main
# tier was small: once the main tier holds the whole vocabulary, a small tier
# in front of it converts what would have been a lock-free hit into a miss
# plus a locked hit. Measured over ten passes of a 20,000-row query whose
# answers carry 20,001 distinct symbols, minimum of three instructions:u runs
# [2026-08-19]:
#
#   two tiers, 512 LRU behind 256 FIFO, plain-dict eviction   17955972589
#   two tiers, 65,536 LRU behind 256 FIFO                     16786153059
#   two tiers, 65,536 LRU behind 65,536 FIFO                  15884696022
#   one tier,  65,536 FIFO                                    15849235310
#
# The last line is the fastest AND holds half the entries of the line above
# it, which stores every name twice. Dropping the split costs the LRU
# reordering, because reordering on a hit would have to take the lock:
# measured at the old 256, FIFO and LRU are within half a point of each other
# on all three workload shapes [tested:
# extensions/python/tests/ch03_atoms_and_expressions/test_atoms.py::test_the_intern_cache_evicts_in_constant_time], and at
# 65,536 an ordinary vocabulary never reaches an eviction at all.
#
# Eviction has to be O(1) in the bound, and `del cache[next(iter(cache))]` is
# not: a dict's iterator walks the entry array from the front and every
# eviction leaves a tombstone there for the next scan to skip. Measured over
# an evict-and-insert step, minimum of five, 256 to 262,144 entries: that
# spelling goes 170 ns to 2,257 ns, while a deque of keys beside the dict
# holds 118 ns to 182 ns and OrderedDict.popitem(last=False) 136 ns to 225 ns
# [measured 2026-08-19]. The cost is what pinned the bound small.
#
# The deque rather than an OrderedDict, which is one container and therefore
# the tidier answer: OrderedDict pays for its ordering on every LOOKUP, and
# the lookup is the hot path. dict.get against OrderedDict.get, minimum of
# seven over 500,000 calls, is 23.5 ns against 24.8 ns on a three-entry map
# and 20.1 against 22.1 on a 20,000-entry one; end to end that is wire-codec
# +0.289% for the OrderedDict and +0.000% for the deque [measured 2026-08-19].
#
# What makes the deque safe here is the lock that P7.2 requires be kept.
# popleft and del are not one atomic step, but both run inside _STATE_LOCK
# with no other writer able to interleave and no statement between them that
# can raise, and a reader only ever touches `cache`. The pair that CAN drift
# is a caller emptying one and not the other, so emptying has exactly one
# door, _wire_intern_clear, and the two lengths are asserted to agree
# [tested test_the_intern_cache_evicts_in_constant_time].
#
# FIFO rather than LRU: reordering on a hit would have to take the lock, and
# the hit is what has to stay lock-free. Measured at the old 256-entry bound,
# FIFO and LRU are within half a point of each other on all three workload
# shapes [tested:
# extensions/python/tests/ch03_atoms_and_expressions/test_atoms.py::test_the_intern_cache_evicts_in_constant_time], and at 65,536 an ordinary
# vocabulary never reaches an eviction at all.
#
# 65,536 rather than 512: the bound is what a peer can make this process hold,
# so it is a memory decision. Measured 2026-08-19 with tracemalloc over
# 12-character names, a full symbol cache costs 11.8 MB and symbols plus
# variables together 23.7 MB, against 240 KB at 512. CPython's own intern
# table is unbounded and immortal by comparison [cpython issue 113993], so a
# bounded 65,536 is the careful end of this trade, not the loose end.
#
# Measured together over ten passes of a 20,000-row query whose answers carry
# 20,001 distinct symbols, minimum of three instructions:u runs [2026-08-19]:
#
#   two tiers, 512 LRU behind a 256 FIFO, plain-dict eviction   17955972589
#   two tiers, 65,536 LRU behind a 256 FIFO                     16786153059
#   two tiers, 65,536 LRU behind a 65,536 FIFO                  15884696022
#   one cache, 65,536 FIFO                                      15805912567
#
# The last line is the fastest and holds half the entries of the line above
# it, which stores every name twice. The second tier existed so a hot name
# answered without the lock; once the cache itself holds the vocabulary, a
# small tier in front of it turns lock-free hits into misses plus locked hits.
_WIRE_CACHE_MAX = 65_536
_WIRE_SYMS: dict[str, Symbol] = {}
_WIRE_VARS: dict[str, Variable] = {}
_WIRE_SYM_ORDER: deque[str] = deque()
_WIRE_VAR_ORDER: deque[str] = deque()


def _wire_intern[WireAtom: (Symbol, Variable)](
    name: str,
    factory: Callable[[str], WireAtom],
    cache: dict[str, WireAtom],
    order: deque[str],
) -> WireAtom:
    interned = cache.get(name)
    if interned is not None:
        return interned
    with _STATE_LOCK:
        interned = cache.get(name)
        if interned is not None:
            return interned
        interned = factory(name)
        if len(cache) >= _WIRE_CACHE_MAX:
            del cache[order.popleft()]
        cache[name] = interned
        order.append(name)
        return interned


def _wire_intern_clear() -> None:
    """Empty the intern caches, each with the order that bounds it."""
    with _STATE_LOCK:
        for cache, order in (
            (_WIRE_SYMS, _WIRE_SYM_ORDER),
            (_WIRE_VARS, _WIRE_VAR_ORDER),
        ):
            cache.clear()
            order.clear()


def _wire_sym(name: str) -> Symbol:
    return _wire_intern(name, Symbol, _WIRE_SYMS, _WIRE_SYM_ORDER)


def _wire_var(name: str) -> Variable:
    return _wire_intern(name, Variable, _WIRE_VARS, _WIRE_VAR_ORDER)
