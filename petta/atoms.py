"""Purpose: atoms as Python values, and the tagged wire encoding that carries
them across janus without losing their metatype. A symbol and a grounded
string both reach Python as str under janus's own conversion, booleans arrive
as text, and containers are rewritten term-shaped, so every value crossing the
boundary travels tagged instead: s symbol, g string, n number, b boolean,
v variable, e expression, o object reference.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import collections.abc as _abc
import math
import re
import weakref
from collections.abc import Iterator, Mapping, Sequence
from functools import singledispatch
from typing import Any, Callable

__all__ = [
    "Atom",
    "Sym",
    "Var",
    "Gnd",
    "Expr",
    "S",
    "V",
    "sym",
    "var",
    "val",
    "expr",
    "encode",
    "decode",
    "from_wire",
    "parse",
    "alpha_eq",
    "unify",
    "variables",
    "is_ground",
    "register_object_repr",
    "register_object_repr_protocol",
]

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


def _is_primitive(value: Any) -> bool:
    """Whether PeTTa has a native term for this value: string, number, boolean."""
    return isinstance(value, (str, int, float, bool))


def _ground_equal(mine: Any, theirs: Any) -> bool:
    """Equality exactly as the engine's == reads it, so a comparison made in
    Python and one made in an equation never disagree: booleans are not
    integers, an integer is not a float ((== 1 1.0) is false), floats
    compare by IEEE identity (-0.0 is not 0.0, and a NaN IS itself), and an
    opaque object is itself alone."""
    if isinstance(mine, bool) or isinstance(theirs, bool):
        return type(mine) is type(theirs) and mine == theirs
    if isinstance(mine, float) and isinstance(theirs, float):
        if math.isnan(mine) or math.isnan(theirs):
            return math.isnan(mine) and math.isnan(theirs)
        if mine == theirs == 0.0:
            return math.copysign(1.0, mine) == math.copysign(1.0, theirs)
        return mine == theirs
    if isinstance(mine, (int, float)) and isinstance(theirs, (int, float)):
        return type(mine) is type(theirs) and mine == theirs
    if _is_primitive(mine) and _is_primitive(theirs):
        return type(mine) is type(theirs) and mine == theirs
    return mine is theirs


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

    __slots__ = ("value", "__weakref__")

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Box({self.value!r})"


# id(value) -> weakref to the box carrying it; see Box's docstring.
_BOXES: dict[int, "weakref.ref[Box]"] = {}


def boxed(value: Any) -> Box:
    """THE box for this object, minted on first crossing, stable while any
    reference to it lives anywhere, engine included."""
    key = id(value)
    reference = _BOXES.get(key)
    if reference is not None:
        box = reference()
        if box is not None and box.value is value:
            return box
    box = Box(value)

    def _evict(_: Any, key: int = key) -> None:
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
    _OBJECT_REPRS[kind] = fn


def register_object_repr_protocol(
    predicate: Callable[[Any], bool], fn: Callable[[Any], str]
) -> None:
    """Teach grounded values satisfying a predicate how to print."""
    _PROTOCOL_REPRS.append((predicate, fn))


def _object_str(value: Any) -> str:
    for kind in type(value).__mro__:
        fn = _OBJECT_REPRS.get(kind)
        if fn is not None:
            return fn(value)
    for predicate, fn in _PROTOCOL_REPRS:
        try:
            if predicate(value):
                return fn(value)
        except Exception:
            # Printing must never take a session down with it.
            continue
    return f"<{type(value).__name__}>"


class Atom:
    """Base class. Atoms are immutable, hashable, and compare structurally."""

    __slots__ = ()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self)!r})"

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("atoms are immutable")

    def __delattr__(self, *_: Any) -> None:
        raise AttributeError("atoms are immutable")

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

    __slots__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Sym) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("sym", self.name))

    def __str__(self) -> str:
        return self.name

    def to_wire(self) -> list:
        return ["s", _encodable(self.name)]

    @property
    def metatype(self) -> str:
        return "Symbol"

    def __call__(self, *args: Any) -> Expr:
        """A symbol applied is an expression headed by it: S.likes(S.Ada)."""
        return Expr([self, *(encode(a) for a in args)])


class Var(Atom):
    """A variable: a hole a match may fill. $x in source."""

    __slots__ = ("name",)
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Var) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("var", self.name))

    def __str__(self) -> str:
        return f"${self.name}"

    def to_wire(self) -> list:
        return ["v", _encodable(self.name)]

    @property
    def metatype(self) -> str:
        return "Variable"


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
    value: Any

    def __init__(self, value: Any) -> None:
        object.__setattr__(self, "value", value)

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

    # Grounded primitives order like their values, so answers sort and
    # compare with plain numbers: max(rows.column("age")) and Gnd(7) >= 5
    # both mean what they read as. Anything else refuses loudly.

    def _ordered(self, other: Any):
        mine = self.value
        theirs = other.value if isinstance(other, Gnd) else other
        if _is_primitive(mine) and _is_primitive(theirs) and not (
            isinstance(mine, str) != isinstance(theirs, str)
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
            return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
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

    __slots__ = ("children", "_hash")
    children: tuple[Atom, ...]

    def __init__(self, children: Sequence[Atom]) -> None:
        object.__setattr__(self, "children", tuple(children))
        object.__setattr__(self, "_hash", None)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        if not isinstance(other, Expr):
            return False
        # Iterative: nested tuple equality would recurse to the term's
        # depth, and depth is data here.
        stack: list[tuple[Expr, Expr]] = [(self, other)]
        while stack:
            a, b = stack.pop()
            if len(a.children) != len(b.children):
                return False
            for x, y in zip(a.children, b.children, strict=True):
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
                stack.extend(
                    c for c in node.children
                    if isinstance(c, Expr) and c._hash is None
                )
        for node in reversed(order):
            if node._hash is None:
                value = hash(("expr", tuple(hash(c) for c in node.children)))
                object.__setattr__(node, "_hash", value)
        return self._hash

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

    def __getitem__(self, i: int | slice) -> Any:
        return self.children[i]

    def __iter__(self) -> Iterator[Atom]:
        return iter(self.children)

    def to_wire(self) -> list:
        # Iterative for the same reason __str__ is: depth is data.
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
_abc.Sequence.register(Expr)


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
                f"__metta__ on {type(value).__name__} returned "
                f"{type(result).__name__}, not an Atom"
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


class _PendingExpr:
    """A wire expression mid-build; its items become an Expr once every
    nested expression below it has become one."""

    __slots__ = ("items", "built")

    def __init__(self) -> None:
        self.items: list = []
        self.built: Expr | None = None


def _leaf_from_wire(tag: Any, payload: Any) -> Atom:
    """One non-expression wire term, its payload validated exactly: a wrong
    payload is a boundary bug and must say so, never coerce."""
    if tag == "s":
        if not isinstance(payload, str):
            raise ValueError(f"wire symbol payload must be text, got {payload!r}")
        return Sym(payload)
    if tag == "g":
        if not isinstance(payload, str):
            raise ValueError(f"wire string payload must be text, got {payload!r}")
        return Gnd(payload)
    if tag == "n":
        if isinstance(payload, bool) or not isinstance(payload, (int, float)):
            raise ValueError(f"wire number payload must be numeric, got {payload!r}")
        return Gnd(payload)
    if tag == "b":
        if isinstance(payload, bool):
            return Gnd(payload)
        if payload in ("true", "false"):
            return Gnd(payload == "true")
        raise ValueError(f"wire boolean payload must be true or false, got {payload!r}")
    if tag == "v":
        if not isinstance(payload, str):
            raise ValueError(f"wire variable payload must be text, got {payload!r}")
        return Var(payload)
    if tag == "o":
        if isinstance(payload, Box):
            payload = payload.value
        return Gnd(payload)
    raise ValueError(f"unknown wire tag {tag!r}")


def from_wire(wire: Any) -> Atom:
    """Rebuild an atom from the tagged wire form janus delivered.

    Iterative, because expression depth is data and must not meet Python's
    recursion ceiling; strict, because a malformed payload is a boundary
    bug that must surface rather than coerce.
    """
    if not isinstance(wire, (list, tuple)) or len(wire) != 2:
        raise ValueError(f"malformed wire term: {wire!r}")
    if wire[0] != "e":
        return _leaf_from_wire(wire[0], wire[1])

    root = _PendingExpr()
    pendings: list[_PendingExpr] = [root]
    stack: list[tuple[Any, _PendingExpr]] = [(wire[1], root)]
    while stack:
        children, pending = stack.pop()
        if not isinstance(children, (list, tuple)):
            raise ValueError(f"wire expression payload must be a list, got {children!r}")
        for child in children:
            if not isinstance(child, (list, tuple)) or len(child) != 2:
                raise ValueError(f"malformed wire term: {child!r}")
            tag, payload = child
            if tag == "e":
                nested = _PendingExpr()
                pendings.append(nested)
                pending.items.append(nested)
                stack.append((payload, nested))
            else:
                pending.items.append(_leaf_from_wire(tag, payload))
    # Children are discovered after their parents, so building in reverse
    # discovery order builds every nested expression before its holder.
    for pending in reversed(pendings):
        pending.built = Expr(
            [
                item.built if isinstance(item, _PendingExpr) else item
                for item in pending.items
            ]
        )
    if root.built is None:
        raise RuntimeError("wire decoding built no root expression")
    return root.built


# ----------------------------------------------------------------- constructors

def sym(name: str) -> Sym:
    """A symbol by name, for names that are not Python identifiers."""
    return Sym(name)


def var(name: str) -> Var:
    """A variable by name."""
    return Var(name)


def val(value: Any) -> Gnd:
    """Carry a Python value whole, whatever it is.

    MeTTa has no list type: encode([1, 2, 3]) is the expression (1 2 3), so
    petta.val([1, 2, 3]) is how to say this particular list is one grounded
    value. It crosses by reference, comes back as the same object, and
    unifies by identity.
    """
    return Gnd(value)


def expr(*children: Any) -> Expr:
    """An expression from parts, each encoded."""
    return Expr([encode(c) for c in children])


class _Namespace:
    """Mint atoms by attribute access: S.likes is the symbol likes, V.x is $x.

    The Python binding is the name itself, so nothing is spelled twice.
    S["car-atom"] reaches names that are not identifiers.
    """

    __slots__ = ("_kind", "_cache")

    def __init__(self, kind: type) -> None:
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        cache = object.__getattribute__(self, "_cache")
        hit = cache.get(name)
        if hit is None:
            hit = cache[name] = object.__getattribute__(self, "_kind")(name)
        return hit

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __call__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("namespaces are read-only")

    def _known(self) -> list[str]:
        names = set(object.__getattribute__(self, "_cache"))
        if object.__getattribute__(self, "_kind") is Sym:
            from . import _engine

            if _engine.started():
                try:
                    names.update(_engine.runtime().builtins())
                except Exception:
                    # Completion must never break a session.
                    pass
        return sorted(names)

    def __dir__(self):
        return [n for n in self._known() if n.isidentifier()]

    def _ipython_key_completions_(self):
        # Most engine names carry a hyphen, so S["<TAB>"] is where they live.
        return self._known()


S = _Namespace(Sym)
V = _Namespace(Var)


# -------------------------------------------------------------------- reading

def parse(source: str) -> Atom:
    """Read one form of MeTTa source into an atom, evaluating nothing.

    Backed by the engine's own reader, with one improvement over sread/2: the
    variable names the DCG collects are kept, so parse("(Parent $x Bob)")
    contains Var('x') rather than a machine name, and the same pattern built
    with V.x compares equal.
    """
    from ._engine import runtime

    row = runtime().once("petta_py_parse(Src, W)", Src=source)
    return from_wire(row["W"])


# ------------------------------------------------------------------ inspection

def variables(atom: Atom) -> list[str]:
    """Variable names in an atom, in first-appearance order. Iterative:
    depth is data."""
    out: list[str] = []
    stack: list[Atom] = [atom]
    while stack:
        a = stack.pop()
        if isinstance(a, Var):
            if a.name not in out:
                out.append(a.name)
        elif isinstance(a, Expr):
            stack.extend(reversed(a.children))
    return out


def is_ground(atom: Atom) -> bool:
    """True when the atom carries no variables."""
    return not variables(atom)


# ----------------------------------------------------------------- equivalence

def alpha_eq(a: Atom, b: Atom) -> bool:
    """Equality up to consistent renaming of variables, PeTTa's =alpha.

    A named function rather than ==, because two atoms must not compare
    differently depending on which variable names they happen to carry.
    """
    return _alpha(encode(a), encode(b), {}, {})


def _alpha(a: Atom, b: Atom, ab: dict, ba: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(a, b)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Var) and isinstance(y, Var):
            if ab.setdefault(x.name, y.name) != y.name:
                return False
            if ba.setdefault(y.name, x.name) != x.name:
                return False
        elif isinstance(x, Expr) and isinstance(y, Expr):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True


def unify(pattern: Any, atom: Any) -> Mapping[str, Atom] | None:
    """Match a pattern against an atom, returning bindings or None.

    One-way: variables on the pattern side bind; a variable on the atom side
    matches only the same variable. No occurs check, matching SWI's default
    and therefore the engine's.
    """
    bindings: dict[str, Atom] = {}
    if _unify(encode(pattern), encode(atom), bindings):
        return bindings
    return None


def _unify(p: Atom, a: Atom, b: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(p, a)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Var):
            # `_` is anonymous: it matches anything, binds nothing, and two
            # occurrences never constrain each other, the reader's own rule.
            if x.name == "_":
                continue
            seen = b.get(x.name)
            if seen is None:
                b[x.name] = y
            elif seen != y:
                return False
        elif isinstance(x, Expr) and isinstance(y, Expr):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True
