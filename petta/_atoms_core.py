"""Purpose: immutable atom values, Python value encoding, and bounded identity caches.
Guarantees:
  - standard callable mentions encode as their symbolic MeTTa heads and all
    four atom rich comparisons follow the engine order used by plain sorted [tested:
    test_callable_mentions_share_operator_and_fourteen_math_names and
    test_atom_comparisons_are_only_ordering; commit=WORKTREE]
  - Grounded normalizes the numeric tower to engine-native values [tested
    test_numpy_scalars_are_engine_numbers]
  - exact rational values retain their Fraction payload through the n wire
    tag [tested: test_rational_payloads_cross_the_scalar_door;
    commit=WORKTREE]
  - pathlib paths encode as symbols rather than opaque host boxes [tested:
    test_path_and_capability_options_cross_as_symbols; commit=WORKTREE]
  - Grounded carries the engine's two relations, one per operand kind: against a
    raw value it is the == operator's numeric tower, against another atom it
    is unification identity (integer and float atoms distinct, signed zeros
    distinct, NaN self-equal), the same split Java makes between == and
    Double.equals so collections of values stay coherent
    [tested: test_python_equality_is_engine_equality,
    test_atom_equality_is_engine_unification; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - atom copy and pickle protocols preserve value and identity contracts
    [tested test_atoms_pickle_by_value, test_process_local_grounded_values_refuse_pickle]
  - Expression is a complete immutable Sequence with iterative equality and hashing
    [tested test_expr_sequence_index_and_count, test_expr_identity_equality]
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
    __petta_wire_value__ protocol, so host bridges can remove the wire layer
    without importing the Python package [tested:
    test_a_python_tuple_answers_the_same_through_both_doors;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Atom operator methods are installed from the immutable 22-entry lowering
    table, including explicit templates and named refusals [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
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
import numbers as _numbers
import threading
import weakref
from abc import ABCMeta
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from fractions import Fraction
from functools import singledispatch
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Self, cast

from ._callable_mentions import callable_mention
from ._operator_lowerings import OPERATOR_LOWERINGS, OperatorLowering


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
            f"Repair the text, or carry it whole with petta.ground(text)."
        )
        raise ValueError(
            msg
        ) from None
    return value


def _normalize_grounded(value: Any) -> Any:
    """Convert the numeric tower to the exact host types the engine carries."""
    if type(value) in (bool, int, float, Fraction, str):
        return value
    if isinstance(value, _numbers.Integral):
        return int(value)
    if isinstance(value, _numbers.Real):
        return float(value)
    return value


def _is_primitive(value: Any) -> bool:
    """Whether PeTTa has a native term for this value: string, number, boolean."""
    return type(value) in (str, int, float, Fraction, bool)


def _ground_equal(mine: Any, theirs: Any) -> bool:
    """Comparison exactly as the engine's == OPERATOR reads a crossed value,
    so a comparison made in Python and one made in an equation never
    disagree: booleans are not numbers, integer and float values share the
    numeric tower, floats use arithmetic equality (-0.0 equals 0.0, NaN is
    unequal to itself), and an opaque object is itself alone. NaN is the one
    value the engine's own doors split on: == over crossed values answers
    False as IEEE does, while the text reader's `!(== NaN NaN)` answers True
    through term identity [measured 2026-08-21, recorded in the ledger as an
    engine seam]; this relation follows the crossed-value door, which is the
    door a Grounded travels. Two atoms compare by _ground_identical, the engine's
    unification, which splits the tower and matches NaN atoms.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    mine = _normalize_grounded(mine)
    theirs = _normalize_grounded(theirs)
    if isinstance(mine, bool) or isinstance(theirs, bool):
        return type(mine) is type(theirs) is bool and mine == theirs
    if isinstance(mine, (int, float, Fraction)) and isinstance(
        theirs, (int, float, Fraction)
    ):
        return mine == theirs
    if type(mine) is not type(theirs):
        return False
    if _is_primitive(mine):
        return mine == theirs
    return mine is theirs


def _ground_identical(mine: Any, theirs: Any) -> bool:
    """Identity exactly as the engine UNIFIES two crossed values, which is a
    different relation from its == operator on three measured edges: an
    integer atom never matches a float atom where (== 0 0.0) answers True,
    0.0 and -0.0 are two float values where == answers one, and one NaN
    matches another where == answers False [measured 2026-08-21: space.query
    over the live engine for each pair; commit=f88aa8be03cb64cb59d3307515ded8701f418321]. Matching,
    membership, removal and every dict of atoms follow this relation, so a
    Counter of atoms counts what the space stores.
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
    def __petta_wire_value__(self) -> Any:
        """The host value hidden by this private transport envelope."""
        return self.value

    def __copy__(self) -> Box:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Box:
        return self

    def __reduce__(self):
        msg = (
            "a petta Box carries process-local object identity and cannot be "
            "pickled; serialize the underlying value explicitly if identity "
            "is not part of its meaning"
        )
        raise TypeError(
            msg
        )


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

# Private protocol dispatch supports the short petta.integrate.repr surface.
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
    """Register the implementation behind petta.integrate.register_repr."""
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

    def eq(self, other: Any) -> Expression:
        """The equality TERM, (== self other); == itself compares atoms."""
        return self._build("==", other)

    def ne(self, other: Any) -> Expression:
        return _expression_atoms((Symbol("not"), self.eq(other)))

    @property
    def vars(self) -> tuple[str, ...]:
        """Variable names in first-appearance order; no names means ground."""
        from .atoms import _variables  # noqa: PLC0415  -- atoms owns tree traversal

        return tuple(_variables(self))

    def map(self, transform: Callable[[Atom], Atom]) -> Atom:
        """Transform every node, children before parents, without recursion."""
        from .atoms import _map_atoms  # noqa: PLC0415  -- atoms owns tree traversal

        return _map_atoms(self, transform)

    def alpha_eq(self, other: Atom) -> bool:
        """Whether two atoms differ only by consistent variable renaming."""
        from .atoms import _alpha_eq  # noqa: PLC0415  -- atoms owns equivalence

        return _alpha_eq(self, other)

    def unify(self, other: Atom) -> Mapping[str, Atom] | None:
        """Unify with another atom, returning bindings or ``None``."""
        from .atoms import unify  # noqa: PLC0415  -- atoms owns unification

        return unify(self, other)

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

    def __call__(self, *args: Any) -> Expression:
        """A symbol applied is an expression headed by it: S.likes(S.Ada)."""
        return _expression_atoms((self, *(encode(a) for a in args)))


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


class Handle(Atom):
    """A grounded executable reference carried as an atom.

    Space handles and native extension handles are the two concrete species.
    A handle owns behavior and identity outside the term tree while remaining
    usable wherever MeTTa accepts a grounded operand.
    """

    __slots__ = ()

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
        return ["h", self.ident]

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
            runtime.do("petta_py_handle_release", self.ident)

    def __del__(self) -> None:
        # Interpreter teardown cannot promise engine calls, so collection
        # is a best-effort release and explicit release() the deterministic
        # path.
        with contextlib.suppress(Exception):
            self.release()


class Grounded(Atom):
    """A grounded value: a host value carried whole.

    Strings, numbers and booleans have native PeTTa terms. Anything else
    crosses as an object reference, stays the same object on the way back,
    and unifies by identity, which is the equality the engine applies to it.

    Equality carries the engine's own two relations, one per operand kind.
    Against a RAW Python value it is the engine's == operator, ergonomic on
    purpose: a grounded primitive compares equal to its raw value, so
    run("!(+ 1 2)") answers compare with == 3 and Grounded(3.0) == 3 the way
    (== 3.0 3) answers True. Against ANOTHER ATOM it is the engine's
    unification: an integer atom never equals a float atom, 0.0 and -0.0 are
    two atoms, one NaN atom equals another, so membership, removal and a
    Counter of atoms agree with what a space actually stores and matches.
    True stays distinct from 1 the way MeTTa keeps Bool and Number apart.
    A symbol never equals a string; that distinction is the point.
    """

    __slots__ = {"value": "the ground Python value this atom carries"}
    __match_args__ = ("value",)
    value: Any

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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Grounded):
            # Atom against atom is the engine's unification, so identity
            # questions (dict keys, membership, remove) answer as the
            # engine's own storage answers them.
            return _ground_identical(self.value, other.value)
        if isinstance(other, Atom):
            return False
        # Raw Python value on the other side, the ergonomic comparison:
        # the engine's == operator, numeric tower included.
        return _ground_equal(self.value, other)

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
        if not _is_primitive(self.value):
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
            return NotImplemented
        return pair[0] < pair[1]

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_le(self, other)
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
        return pair[0] <= pair[1]

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_gt(self, other)
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
        return pair[0] > pair[1]

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Atom):
            return _standard_order_ge(self, other)
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
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
        if isinstance(v, bool):
            return ["b", "true" if v else "false"]
        if isinstance(v, str):
            return ["g", _encodable(v)]
        if isinstance(v, (int, float, Fraction)):
            return ["n", v]
        if isinstance(v, Box):
            return ["o", v]
        return ["o", boxed(v)]

    @property
    def metatype(self) -> str:
        return "Grounded"


class Expression(Atom):
    """An expression: an ordered sequence of atoms. (likes Ada Coffee).

    Sequence-shaped, so Python's own idioms apply: expr[0] is car-atom,
    len(expr) is size-atom, and case [head, *args] destructures it. None of
    that costs an engine call.
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
        """Build an expression from one sequence or positional Python values."""
        parts: Sequence[Any]
        if len(children) == 1 and (
            type(children[0]) in (list, tuple)
            or (
                not isinstance(children[0], (str, bytes, Atom))
                and isinstance(children[0], Sequence)
            )
        ):
            parts = children[0]
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
        if not isinstance(other, Expression):
            return NotImplemented
        # Iterative: nested tuple equality would recurse to the term's
        # depth, and depth is data here.
        stack: list[tuple[Expression, Expression]] = [(self, other)]
        while stack:
            a, b = stack.pop()
            if a is b:
                continue
            if len(a.children) != len(b.children):
                return False
            for x, y in zip(a.children, b.children, strict=True):
                if x is y:
                    continue
                if isinstance(x, Expression) and isinstance(y, Expression):
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
                value = hash(("expr", tuple(hash(child) for child in node.children)))
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
                f"{self} is a comparison TERM, not a truth value; evaluate "
                f"it (space.eval) or use it as a guard (where=...)"
            )
            raise TypeError(
                msg
            )
        return True

    def __getitem__(self, i: int | slice) -> Any:
        return self.children[i]

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
    if entry.kind == "absent":
        msg = (
            f"{entry.syntax} has no MeTTa lowering: {entry.reason}. "
            "Operate on grounded Python values or define a named MeTTa function instead."
        )
        raise TypeError(msg)
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
        # policy-inventory-exempt: mechanism-internal; reason=symbol and provided are the two lowering-table kinds whose form is a MeTTa head to apply to the operands; evidence=bindings/python/petta/_operator_lowerings.py:OperatorLowering
        if entry.kind in {"symbol", "provided"}
        else entry.form
    )
    lowered = _operator_form(form, operands)
    if not isinstance(lowered, Expression):
        msg = f"operator lowering {entry.dunder} did not build an expression"
        raise RuntimeError(msg)  # noqa: TRY004  -- a non-Expression means a corrupt lowering-table row, an internal invariant break, not a caller type error
    return lowered


def _operator_method(  # noqa: C901  -- _operator_method keeps every specialization shape together so its branches share one table row
    entry: OperatorLowering, *, reflected: bool = False
) -> Callable[..., Expression]:
    """Specialize one dunder once and retain its table row for inspection."""
    name = entry.reflected if reflected else entry.dunder
    if name is None:
        msg = f"operator lowering {entry.dunder} has no reflected spelling"
        raise RuntimeError(msg)
    # policy-inventory-exempt: mechanism-internal; reason=symbol and provided are the two lowering-table kinds whose form is a MeTTa head to apply to the operands; evidence=bindings/python/petta/_operator_lowerings.py:OperatorLowering
    if entry.kind in {"symbol", "provided"}:
        if not isinstance(entry.form, str):
            msg = f"operator lowering {entry.dunder} has no symbol"
            raise RuntimeError(msg)
        symbol = Symbol(entry.form)
        if entry.arity == 1:

            def unary_symbol(self: Atom, _symbol: Symbol = symbol) -> Expression:
                return _expression_atoms((_symbol, self))

            operator: Callable[..., Expression] = unary_symbol
        elif reflected:

            def reflected_symbol(
                self: Atom, other: Any, _symbol: Symbol = symbol
            ) -> Expression:
                return _expression_atoms((_symbol, encode(other), self))

            operator = reflected_symbol
        else:

            def binary_symbol(
                self: Atom, other: Any, _symbol: Symbol = symbol
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
    operator.__dict__["__petta_lowering__"] = entry
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


def _standard_order_lt(self: Atom, other: Any) -> bool:
    """Order atoms by the engine's term order; comparisons as terms use S['<']."""
    if not isinstance(other, Atom):
        return NotImplemented
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) < order_key(other)


def _standard_order_le(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        return NotImplemented
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) <= order_key(other)


def _standard_order_gt(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        return NotImplemented
    from .atoms import order_key  # noqa: PLC0415  -- atoms owns the public order

    return order_key(self) > order_key(other)


def _standard_order_ge(self: Atom, other: Any) -> bool:
    """Compare atoms by the engine order, refusing non-atoms."""
    if not isinstance(other, Atom):
        return NotImplemented
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
    # To carry a list whole as one opaque value, wrap it: petta.ground([1, 2, 3]).
    return _expression_atoms(encode(v) for v in value)


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
    return atom.value if isinstance(atom, Grounded) else atom


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
# on all three workload shapes [ai-code-organisation-and-fixes.md BA3], and at
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
# shapes [ai-code-organisation-and-fixes.md BA3], and at 65,536 an ordinary
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
