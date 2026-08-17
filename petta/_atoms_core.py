"""Purpose: immutable atom values, Python value encoding, and bounded identity caches.
Guarantees:
  - Gnd normalizes the numeric tower to engine-native values [tested
    test_numpy_scalars_are_engine_numbers]
  - atom copy and pickle protocols preserve value and identity contracts
    [tested test_atoms_pickle_by_value, test_process_local_grounded_values_refuse_pickle]
  - Expr is a complete immutable Sequence with iterative equality and hashing
    [tested test_expr_sequence_index_and_count, test_expr_identity_equality]
  - Expr virtual Sequence registration uses 4.00% fewer instructions than
    nominal inheritance [measured 2026-08-14: minimum of three instructions:u runs]
  - wire and object identity caches are bounded or weak and synchronized
    [tested test_wire_intern_tables_are_bounded,
    test_atom_identity_caches_are_thread_safe]
  - object formatters can be removed by their exact registration identity
    [tested test_object_repr_registrations_can_be_removed_exactly]
Guarded by:
  - _STATE_LOCK protects box identity, formatter registries, and wire interns
    [tested test_atom_identity_caches_are_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import contextlib
import math
import numbers as _numbers
import re
import threading
import weakref
from abc import ABCMeta
from collections.abc import Callable, Iterator, Sequence
from functools import singledispatch
from typing import Any, Self, TypeVar, cast

# A symbol prints bare only when PeTTa's tokeniser would read it back whole:
# token//1 stops at whitespace, parentheses and quotes.
_BARE = re.compile(r'^[^\s()"]+$')


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
        raise ValueError(
            f"this string cannot cross to the engine: it contains an unpaired "
            f"surrogate at position {exc.start}, which has no UTF-8 encoding. "
            f"Repair the text, or carry it whole with petta.val(text)."
        ) from None
    return value


def _normalize_grounded(value: Any) -> Any:
    """Convert the numeric tower to the exact host types the engine carries."""
    if type(value) in (bool, int, float, str):
        return value
    if isinstance(value, _numbers.Integral):
        return int(value)
    if isinstance(value, _numbers.Real):
        return float(value)
    return value


def _is_primitive(value: Any) -> bool:
    """Whether PeTTa has a native term for this value: string, number, boolean."""
    return type(value) in (str, int, float, bool)


def _ground_equal(mine: Any, theirs: Any) -> bool:
    """Equality exactly as the engine's == reads it, so a comparison made in
    Python and one made in an equation never disagree: booleans are not
    integers, an integer is not a float ((== 1 1.0) is false), floats
    compare by IEEE identity (-0.0 is not 0.0, and a NaN IS itself), and an
    opaque object is itself alone."""
    mine = _normalize_grounded(mine)
    theirs = _normalize_grounded(theirs)
    if type(mine) is not type(theirs):
        return False
    if isinstance(mine, float):
        return _float_equal(mine, theirs)
    if _is_primitive(mine):
        return mine == theirs
    return mine is theirs


def _float_equal(mine: float, theirs: float) -> bool:
    """Engine equality for same-type floats, including NaN and signed zero."""
    if math.isnan(mine) or math.isnan(theirs):
        return math.isnan(mine) and math.isnan(theirs)
    if mine == theirs == 0.0:
        return math.copysign(1.0, mine) == math.copysign(1.0, theirs)
    return mine == theirs


_STATE_LOCK = threading.RLock()


class Box:
    """Holds one Python value so it crosses the boundary by reference.

    janus rewrites more than containers on the way in: lists, tuples, dicts,
    sets, bytes and None become Prolog terms, and anything speaking the
    sequence protocol, a NumPy array included, explodes into a list of
    element objects. Which types convert is janus's decision, not ours, so
    every opaque value crosses boxed, uniformly, and every consuming surface
    unboxes: from_wire, raw operation arguments and results, and the
    engine's typing through py_object_type_names/2. A caller never sees a
    box; it exists only on the wire and inside the engine.

    Boxes are INTERNED per object identity through boxed(): one live object
    always crosses as the same box, so a stored atom and a later query meet
    in the same reference and unification by identity means identity. The
    intern table holds boxes weakly: a box lives exactly as long as
    something references it (an atom in a space does, through janus), and a
    dropped object costs nothing forever after.
    """

    __slots__ = ("__weakref__", "value")

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Box({self.value!r})"

    def __copy__(self) -> Box:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Box:
        return self

    def __reduce__(self):
        raise TypeError(
            "a petta Box carries process-local object identity and cannot be "
            "pickled; serialize the underlying value explicitly if identity "
            "is not part of its meaning"
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


# type -> callable(value) -> str, consulted by Gnd.__str__ for object values,
# so a stored tensor prints its shape and dtype rather than an address.
_OBJECT_REPRS: dict[type, Callable[[Any], str]] = {}

# (predicate, formatter) pairs for protocols rather than classes, so one
# registration covers every library speaking a protocol such as DLPack.
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
            raise KeyError(f"no object repr is registered for {kind.__qualname__}")
        del _OBJECT_REPRS[kind]


def register_object_repr_protocol(
    predicate: Callable[[Any], bool], fn: Callable[[Any], str]
) -> None:
    """Teach grounded values satisfying a predicate how to print."""
    with _STATE_LOCK:
        _PROTOCOL_REPRS.append((predicate, fn))


def unregister_object_repr_protocol(
    predicate: Callable[[Any], bool], fn: Callable[[Any], str]
) -> None:
    """Remove the latest protocol formatter matching both callables."""
    with _STATE_LOCK:
        for index in range(len(_PROTOCOL_REPRS) - 1, -1, -1):
            registered_predicate, registered_fn = _PROTOCOL_REPRS[index]
            if registered_predicate is predicate and registered_fn is fn:
                _PROTOCOL_REPRS.pop(index)
                return
    raise KeyError("no protocol repr is registered for those exact callables")


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
            raise RuntimeError(
                f"a registered object repr raised on {type(value).__name__}: {exc}"
            ) from exc
    return f"<{type(value).__name__}>"


class Atom:
    """Base class. Atoms are immutable, hashable, and compare structurally."""

    __slots__ = ()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self)!r})"

    # Term structure is declared on the base because an engine answer is
    # typed Atom and a checker cannot know which kind arrived. Expr's
    # docstring already promises expr[0] and len(expr), and run, eval and
    # query all return Atom, so without these the documented idiom does not
    # type-check: ten of the 41 diagnostics a downstream user saw over the
    # 16 example programs, across six files [measured 2026-08-17]. Expr
    # overrides all four; a leaf refuses at the same point it always did,
    # so the runtime is unchanged and the static story stops being a lie.
    @property
    def children(self) -> tuple[Atom, ...]:
        raise TypeError(f"{self!r} is a leaf atom and has no children")

    def __len__(self) -> int:
        raise TypeError(f"{self!r} is a leaf atom and has no length")

    # Declaring __len__ above would otherwise route bool() through it and
    # make every leaf atom raise where it used to be truthy. Expr overrides
    # this to keep refusing comparison terms.
    def __bool__(self) -> bool:
        return True

    def __iter__(self) -> Iterator[Atom]:
        raise TypeError(f"{self!r} is a leaf atom and is not iterable")

    def __getitem__(self, i: int | slice) -> Any:
        raise TypeError(f"{self!r} is a leaf atom and is not indexable")

    # Term-building operators, the query-builder lesson: arithmetic and
    # order comparisons on symbols, variables and expressions CONSTRUCT the
    # corresponding term, so V.age >= 18 is (>= $age 18) and V.x + 1 is
    # (+ $x 1), guards and bodies written as the Python they look like.
    # Gnd overrides both families with VALUE semantics (its comparisons
    # answer booleans, engine-exactly), so a grounded number never quietly
    # becomes a program. Equality stays equality everywhere; the term is
    # spelled x.eq(y), since overloading == would cost structural equality.

    def _build(self, op: str, other: Any, flipped: bool = False) -> Expr:
        left, right = (encode(other), self) if flipped else (self, encode(other))
        return Expr([Sym(op), left, right])

    def __add__(self, other: Any) -> Expr:
        return self._build("+", other)

    def __radd__(self, other: Any) -> Expr:
        return self._build("+", other, flipped=True)

    def __sub__(self, other: Any) -> Expr:
        return self._build("-", other)

    def __rsub__(self, other: Any) -> Expr:
        return self._build("-", other, flipped=True)

    def __mul__(self, other: Any) -> Expr:
        return self._build("*", other)

    def __rmul__(self, other: Any) -> Expr:
        return self._build("*", other, flipped=True)

    def __truediv__(self, other: Any) -> Expr:
        return self._build("/", other)

    def __rtruediv__(self, other: Any) -> Expr:
        return self._build("/", other, flipped=True)

    def __mod__(self, other: Any) -> Expr:
        return self._build("%", other)

    def __rmod__(self, other: Any) -> Expr:
        return self._build("%", other, flipped=True)

    def __pow__(self, other: Any) -> Expr:
        return self._build("pow-math", other)

    def __rpow__(self, other: Any) -> Expr:
        return self._build("pow-math", other, flipped=True)

    def __matmul__(self, other: Any) -> Expr:
        return self._build("matmul", other)

    def __rmatmul__(self, other: Any) -> Expr:
        return self._build("matmul", other, flipped=True)

    # &, | and ~ build the boolean terms, the query-composition idiom:
    # (V.age >= 18) & (V.age <= 40) is (and (>= $age 18) (<= $age 40)),
    # so guards compose the way the engine reads them. Python's own and,
    # or and not are not overloadable; they hit __bool__, which refuses
    # loudly on comparison terms.

    def __and__(self, other: Any) -> Expr:
        return self._build("and", other)

    def __rand__(self, other: Any) -> Expr:
        return self._build("and", other, flipped=True)

    def __or__(self, other: Any) -> Expr:
        return self._build("or", other)

    def __ror__(self, other: Any) -> Expr:
        return self._build("or", other, flipped=True)

    def __xor__(self, other: Any) -> Expr:
        return self._build("xor", other)

    def __rxor__(self, other: Any) -> Expr:
        return self._build("xor", other, flipped=True)

    def __invert__(self) -> Expr:
        return Expr([Sym("not"), self])

    def __lt__(self, other: Any) -> Expr | bool:
        return self._build("<", other)

    def __le__(self, other: Any) -> Expr | bool:
        return self._build("<=", other)

    def __gt__(self, other: Any) -> Expr | bool:
        return self._build(">", other)

    def __ge__(self, other: Any) -> Expr | bool:
        return self._build(">=", other)

    def eq(self, other: Any) -> Expr:
        """The equality TERM, (== self other); == itself compares atoms."""
        return self._build("==", other)

    def ne(self, other: Any) -> Expr:
        return Expr([Sym("not"), self.eq(other)])

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("atoms are immutable")

    def __delattr__(self, *_: Any) -> None:
        raise AttributeError("atoms are immutable")

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
    # datum it was handed and never runs a program. Gnd overrides these for
    # the values that genuinely are numbers.

    def _not_a(self, target: str) -> TypeError:
        return TypeError(
            f"cannot read {self} as a Python {target}: it is a {self.metatype} "
            f"in MeTTa, and only a grounded number converts. Evaluate it first "
            f"if it is a program: space.eval(atom)."
        )

    def __int__(self) -> int:
        raise self._not_a("int")

    def __float__(self) -> float:
        raise self._not_a("float")

    def __complex__(self) -> complex:
        raise self._not_a("complex")

    def __index__(self) -> int:
        raise self._not_a("int")

    def __format__(self, spec: str) -> str:
        return str(self) if not spec else format(str(self), spec)


class Sym(Atom):
    """A symbol: a name that denotes itself. Coffee, likes, &self.

    A symbol is not a string: Sym('foo') == 'foo' is False on purpose,
    because 'foo' the text and foo the name are different atoms in MeTTa,
    and folding them together is the ambiguity the wire encoding removes.
    """

    __slots__ = ("_wire", "name")
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Sym) and other.name == self.name

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

    def __call__(self, *args: Any) -> Expr:
        """A symbol applied is an expression headed by it: S.likes(S.Ada)."""
        return Expr([self, *(encode(a) for a in args)])


class Var(Atom):
    """A variable: a hole a match may fill. $x in source."""

    __slots__ = ("_wire", "name")
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Var) and other.name == self.name

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
    """

    __slots__ = ("_released", "ident", "text")
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
        return isinstance(other, Handle) and other.ident == self.ident

    def __hash__(self) -> int:
        return hash(("handle", self.ident))

    def __reduce__(self):
        raise TypeError(
            "a native handle has process-local identity and cannot be "
            "pickled; read it out through its extension's accessors instead"
        )

    def to_wire(self) -> list:
        return ["h", self.ident]

    @property
    def metatype(self) -> str:
        return "Grounded"

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


class Gnd(Atom):
    """A grounded value: a host value carried whole.

    Strings, numbers and booleans have native PeTTa terms. Anything else
    crosses as an object reference, stays the same object on the way back,
    and unifies by identity, which is the equality the engine applies to it.

    Equality is ergonomic on purpose: a grounded primitive compares equal to
    its raw Python value, so run("!(+ 1 2)") answers compare with == 3.
    True stays distinct from 1 the way MeTTa keeps Bool and Number apart.
    A symbol never equals a string; that distinction is the point.
    """

    __slots__ = ("value",)
    __match_args__ = ("value",)
    value: Any

    # Truthiness follows equality, or `if answer:` reads a MeTTa False as
    # true. Without this the library forces the PEP 8 violation it warns
    # against: on a rule answering False, the conformant
    # `any(a for a in answers)` was True and the explicit
    # `any(a == True for a in answers)` was False, so a user tidying away
    # the `# noqa: E712` introduced a silent wrong answer
    # [measured 2026-08-17]. Expr.__bool__ already guards this class of
    # mistake for comparison terms; Gnd had no guard for the same one.
    # Restricted to bool on purpose: a Number 0 is not falsehood in MeTTa,
    # so Gnd(0) and Gnd("") stay truthy.
    def __bool__(self) -> bool:
        value = self.value
        return value if isinstance(value, bool) else True

    def __init__(self, value: Any) -> None:
        object.__setattr__(self, "value", _normalize_grounded(value))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Gnd):
            return _ground_equal(self.value, other.value)
        if isinstance(other, Atom):
            return False
        # Raw Python value on the other side, the ergonomic comparison:
        # the same engine identity the Gnd-to-Gnd case applies.
        return _ground_equal(self.value, other)

    def __hash__(self) -> int:
        # Hash agrees with equality: a primitive hashes as its value, so
        # Gnd(3) and 3 land in the same bucket; an object hashes by identity.
        if _is_primitive(self.value):
            return hash(self.value)
        return hash(("gnd", id(self.value)))

    def __reduce__(self):
        if not _is_primitive(self.value):
            raise TypeError(
                "a grounded opaque object has process-local identity and "
                "cannot be pickled; encode a stable value instead"
            )
        return Gnd, (self.value,)

    # Grounded values are VALUES throughout: comparisons answer booleans
    # (engine-exactly) and arithmetic computes, so an answer post-processes
    # like the number it is; term building belongs to symbols, variables
    # and expressions.

    def _value_of(self, other: Any) -> Any:
        return other.value if isinstance(other, Gnd) else other

    def __add__(self, other: Any) -> Any:
        return self.value + self._value_of(other)

    def __radd__(self, other: Any) -> Any:
        return self._value_of(other) + self.value

    def __sub__(self, other: Any) -> Any:
        return self.value - self._value_of(other)

    def __rsub__(self, other: Any) -> Any:
        return self._value_of(other) - self.value

    def __mul__(self, other: Any) -> Any:
        return self.value * self._value_of(other)

    def __rmul__(self, other: Any) -> Any:
        return self._value_of(other) * self.value

    def __truediv__(self, other: Any) -> Any:
        return self.value / self._value_of(other)

    def __rtruediv__(self, other: Any) -> Any:
        return self._value_of(other) / self.value

    def __mod__(self, other: Any) -> Any:
        return self.value % self._value_of(other)

    def __rmod__(self, other: Any) -> Any:
        return self._value_of(other) % self.value

    def __pow__(self, other: Any) -> Any:
        return self.value ** self._value_of(other)

    def __rpow__(self, other: Any) -> Any:
        return self._value_of(other) ** self.value

    def __matmul__(self, other: Any) -> Any:
        return self.value @ self._value_of(other)

    def __rmatmul__(self, other: Any) -> Any:
        return self._value_of(other) @ self.value

    def __and__(self, other: Any) -> Any:
        return self.value & self._value_of(other)

    def __rand__(self, other: Any) -> Any:
        return self._value_of(other) & self.value

    def __or__(self, other: Any) -> Any:
        return self.value | self._value_of(other)

    def __ror__(self, other: Any) -> Any:
        return self._value_of(other) | self.value

    def __xor__(self, other: Any) -> Any:
        return self.value ^ self._value_of(other)

    def __rxor__(self, other: Any) -> Any:
        return self._value_of(other) ^ self.value

    def __invert__(self) -> Any:
        return ~self.value

    # Grounded primitives order like their values, so answers sort and
    # compare with plain numbers: max(rows["age"]) and Gnd(7) >= 5
    # both mean what they read as. Anything else refuses loudly.

    def _ordered(self, other: Any):
        mine = self.value
        theirs = other.value if isinstance(other, Gnd) else other
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
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
        return pair[0] < pair[1]

    def __le__(self, other: Any) -> bool:
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
        return pair[0] <= pair[1]

    def __gt__(self, other: Any) -> bool:
        pair = self._ordered(other)
        if pair is None:
            return NotImplemented
        return pair[0] > pair[1]

    def __ge__(self, other: Any) -> bool:
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
        if isinstance(v, (int, float)):
            return repr(v)
        return _object_str(v)

    def _number(self, target: str) -> int | float:
        v = self.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TypeError(
                f"cannot read {self} as a Python {target}: it is not a Number "
                f"in MeTTa. int(atom.value) is how to say parse this text."
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
            raise self._not_a("int")
        return v

    def __format__(self, spec: str) -> str:
        if not spec:
            return str(self)
        return format(self.value, spec) if _is_primitive(self.value) else format(str(self), spec)

    def __repr__(self) -> str:
        # Gnd(42) and Gnd('text'), not Gnd('42'): the repr shows the value it
        # carries, so a number never reads like a string.
        if _is_primitive(self.value):
            return f"Gnd({self.value!r})"
        return f"Gnd({_object_str(self.value)})"

    def to_wire(self) -> list:
        v = self.value
        if isinstance(v, bool):
            return ["b", "true" if v else "false"]
        if isinstance(v, str):
            return ["g", _encodable(v)]
        if isinstance(v, (int, float)):
            return ["n", v]
        if isinstance(v, Box):
            return ["o", v]
        return ["o", boxed(v)]

    @property
    def metatype(self) -> str:
        return "Grounded"


class Expr(Atom):
    """An expression: an ordered sequence of atoms. (likes Ada Coffee).

    Sequence-shaped, so Python's own idioms apply: expr[0] is car-atom,
    len(expr) is size-atom, and case [head, *args] destructures it. None of
    that costs an engine call.
    """

    __slots__ = ("_hash", "children")
    __match_args__ = ("children",)
    children: tuple[Atom, ...]
    _hash: int | None

    def __init__(self, children: Sequence[Atom]) -> None:
        object.__setattr__(self, "children", tuple(children))
        object.__setattr__(self, "_hash", None)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Expr):
            return NotImplemented
        # Iterative: nested tuple equality would recurse to the term's
        # depth, and depth is data here.
        stack: list[tuple[Expr, Expr]] = [(self, other)]
        while stack:
            a, b = stack.pop()
            if a is b:
                continue
            if len(a.children) != len(b.children):
                return False
            for x, y in zip(a.children, b.children, strict=True):
                if x is y:
                    continue
                if isinstance(x, Expr) and isinstance(y, Expr):
                    stack.append((x, y))
                elif x != y:
                    return False
        return True

    def __hash__(self) -> int:
        # Cached, and computed bottom-up without recursion on first use.
        cached = self._hash
        if cached is not None:
            return cached
        order: list[Expr] = []
        stack: list[Expr] = [self]
        while stack:
            node = stack.pop()
            if node._hash is None:
                order.append(node)
                stack.extend(c for c in node.children if isinstance(c, Expr) and c._hash is None)
        for node in reversed(order):
            if node._hash is None:
                value = hash(("expr", tuple(hash(child) for child in node.children)))
                object.__setattr__(node, "_hash", value)
        return cast(int, self._hash)

    def __reduce__(self):
        return Expr, (self.children,)

    def __rich_repr__(self):
        """rich.pretty expands an expression by its children, so a deep
        term prints as an indented tree instead of one long line. Only
        rich consults this; plain repr() is unchanged."""
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
            elif isinstance(item, Expr):
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
        if isinstance(head, Sym) and head.name in (
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
            raise TypeError(
                f"{self} is a comparison TERM, not a truth value; evaluate "
                f"it (space.eval) or use it as a guard (where=...)"
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
        # Iterative for the same reason __str__ is: depth is data. Leaf
        # symbols and variables answer their cached wire cells; the
        # expression skeleton itself is one-shot in the hot paths (a fact
        # is added once), so it builds fresh, measured cheaper than
        # memoizing it.
        out: list = ["e", []]
        stack: list[tuple[Expr, list]] = [(self, out[1])]
        while stack:
            node, sink = stack.pop()
            for child in node.children:
                if isinstance(child, Expr):
                    slot: list = ["e", []]
                    sink.append(slot)
                    stack.append((child, slot[1]))
                else:
                    sink.append(child.to_wire())
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


# Registered so case [head, *args] matches: the Sequence pattern checks the ABC.
cast(ABCMeta, Sequence).register(Expr)


# --------------------------------------------------------------------- encoding


@singledispatch
def encode(value: Any) -> Atom:
    """Turn a Python value into an atom.

    Open by design: a class you own implements __metta__; a class you do not
    own is taught through encode.register, which is functools.singledispatch.
    Anything unregistered without __metta__ is carried whole as a grounded
    object, the same rule the engine itself applies to a host value.
    """
    hook = getattr(value, "__metta__", None)
    if hook is not None:
        result = hook()
        if not isinstance(result, Atom):
            raise TypeError(
                f"__metta__ on {type(value).__name__} returned {type(result).__name__}, not an Atom"
            )
        return result
    return Gnd(value)


@encode.register
def _(value: Atom) -> Atom:
    return value


@encode.register
def _(value: str) -> Atom:
    # A Python str is a grounded string, never a symbol. Symbols come from S.
    return Gnd(value)


@encode.register(bool)
@encode.register(int)
@encode.register(float)
def _(value: Any) -> Atom:
    return Gnd(value)


@encode.register(tuple)
@encode.register(list)
def _(value: Any) -> Atom:
    # A Python sequence reads as an expression, which is what (1 2 3) is.
    # To carry a list whole as one opaque value, wrap it: petta.val([1, 2, 3]).
    return Expr([encode(v) for v in value])


def decode(atom: Any) -> Any:
    """Unwrap grounded values to Python, recursively, leaving structure alone.

    A Gnd becomes its value, an Expr becomes an Expr of decoded children
    only when asked (this returns the expression as is), and symbols and
    variables stay atoms. Named for what it does; results already compare
    ergonomically without it, so it is never on a default path.
    """
    return atom.value if isinstance(atom, Gnd) else atom


# Decoded symbols and variables intern per name: their equality and hash are by
# name already, and a query answering thousands of rows repeats a small
# vocabulary. The two tiers follow CPython's re cache: check a small FIFO first
# without reordering, then maintain a larger LRU. Eviction changes only object
# allocation because equality is by value, while bounding names supplied by a
# remote peer prevents permanent process growth.
_WIRE_CACHE_MAX = 512
_WIRE_CACHE_FAST_MAX = 256
_WIRE_SYMS: dict[str, Sym] = {}
_WIRE_SYMS_FAST: dict[str, Sym] = {}
_WIRE_VARS: dict[str, Var] = {}
_WIRE_VARS_FAST: dict[str, Var] = {}
_WireAtom = TypeVar("_WireAtom", Sym, Var)


def _wire_intern(
    name: str,
    factory: Callable[[str], _WireAtom],
    cache: dict[str, _WireAtom],
    fast: dict[str, _WireAtom],
) -> _WireAtom:
    interned = fast.get(name)
    if interned is not None:
        return interned
    with _STATE_LOCK:
        interned = fast.get(name)
        if interned is not None:
            return interned
        interned = cache.pop(name, None)
        if interned is None:
            interned = factory(name)
            if len(cache) >= _WIRE_CACHE_MAX:
                del cache[next(iter(cache))]
        cache[name] = interned
        if len(fast) >= _WIRE_CACHE_FAST_MAX:
            del fast[next(iter(fast))]
        fast[name] = interned
        return interned


def _wire_sym(name: str) -> Sym:
    return _wire_intern(name, Sym, _WIRE_SYMS, _WIRE_SYMS_FAST)


def _wire_var(name: str) -> Var:
    return _wire_intern(name, Var, _WIRE_VARS, _WIRE_VARS_FAST)
