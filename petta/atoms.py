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
import re
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


# Types janus would convert on the way in rather than keep as a reference.
# A dict becomes a Prolog dict, a tuple a compound, bytes a code list, None a
# janus @none, so an opaque container has to be boxed to stay one object.
_CONVERTED_BY_JANUS = (list, tuple, dict, set, frozenset, bytes, bytearray, type(None))


class Box:
    """Holds one Python value so it crosses the boundary by reference.

    janus rewrites lists, tuples, dicts, sets, bytes and None into Prolog
    terms, which unmakes an opaque value on the way in. A class instance
    always crosses as an object reference, so wrapping the value in one is
    what keeps it whole. Unboxing happens on decode, so a caller never sees
    the box unless the value surfaces inside the engine itself.
    """

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Box({self.value!r})"


# type -> callable(value) -> str, consulted by Gnd.__str__ for object values.
# pettorch registers a tensor formatter here so a stored tensor prints its
# shape and dtype rather than an address.
_OBJECT_REPRS: dict[type, Callable[[Any], str]] = {}


def register_object_repr(kind: type, fn: Callable[[Any], str]) -> None:
    """Teach grounded values of one type how to print."""
    _OBJECT_REPRS[kind] = fn


def _object_str(value: Any) -> str:
    for kind in type(value).__mro__:
        fn = _OBJECT_REPRS.get(kind)
        if fn is not None:
            return fn(value)
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
            if isinstance(self.value, bool) != isinstance(other.value, bool):
                return False
            if _is_primitive(self.value) and _is_primitive(other.value):
                return self.value == other.value
            return self.value is other.value
        if isinstance(other, Atom):
            return False
        # Raw Python value on the other side: compare by value for primitives,
        # by identity for carried objects, keeping bool apart from int.
        if _is_primitive(self.value) and _is_primitive(other):
            if isinstance(self.value, bool) != isinstance(other, bool):
                return False
            return self.value == other
        return self.value is other

    def __hash__(self) -> int:
        # Hash agrees with equality: a primitive hashes as its value, so
        # Gnd(3) and 3 land in the same bucket; an object hashes by identity.
        if _is_primitive(self.value):
            return hash(self.value)
        return hash(("gnd", id(self.value)))

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
        if isinstance(v, _CONVERTED_BY_JANUS):
            # janus would rewrite these into Prolog terms; boxing keeps the
            # value one opaque object with its identity.
            return ["o", Box(v)]
        return ["o", v]

    @property
    def metatype(self) -> str:
        return "Grounded"


class Expr(Atom):
    """An expression: an ordered sequence of atoms. (likes Ada Coffee).

    Sequence-shaped, so Python's own idioms apply: expr[0] is car-atom,
    len(expr) is size-atom, and case [head, *args] destructures it. None of
    that costs an engine call.
    """

    __slots__ = ("children",)
    children: tuple[Atom, ...]

    def __init__(self, children: Sequence[Atom]) -> None:
        object.__setattr__(self, "children", tuple(children))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return NotImplemented
        return isinstance(other, Expr) and other.children == self.children

    def __hash__(self) -> int:
        return hash(("expr", self.children))

    def __str__(self) -> str:
        return "(" + " ".join(str(c) for c in self.children) + ")"

    def __len__(self) -> int:
        return len(self.children)

    def __getitem__(self, i: int | slice) -> Any:
        return self.children[i]

    def __iter__(self) -> Iterator[Atom]:
        return iter(self.children)

    def to_wire(self) -> list:
        return ["e", [c.to_wire() for c in self.children]]

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


def from_wire(wire: Any) -> Atom:
    """Rebuild an atom from the tagged wire form janus delivered."""
    if not isinstance(wire, (list, tuple)) or len(wire) != 2:
        raise ValueError(f"malformed wire term: {wire!r}")
    tag, payload = wire
    if tag == "s":
        return Sym(payload)
    if tag == "g":
        return Gnd(payload)
    if tag == "n":
        return Gnd(payload)
    if tag == "b":
        return Gnd(payload if isinstance(payload, bool) else payload == "true")
    if tag == "v":
        return Var(payload)
    if tag == "e":
        return Expr([from_wire(c) for c in payload])
    if tag == "o":
        if isinstance(payload, Box):
            payload = payload.value
        return Gnd(payload)
    raise ValueError(f"unknown wire tag {tag!r}")


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
    """Variable names in an atom, in first-appearance order."""
    out: list[str] = []

    def walk(a: Atom) -> None:
        if isinstance(a, Var):
            if a.name not in out:
                out.append(a.name)
        elif isinstance(a, Expr):
            for c in a.children:
                walk(c)

    walk(atom)
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
    if isinstance(a, Var) and isinstance(b, Var):
        if ab.setdefault(a.name, b.name) != b.name:
            return False
        return ba.setdefault(b.name, a.name) == a.name
    if isinstance(a, Expr) and isinstance(b, Expr):
        if len(a.children) != len(b.children):
            return False
        return all(_alpha(x, y, ab, ba) for x, y in zip(a.children, b.children, strict=True))
    return a == b


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
    if isinstance(p, Var):
        seen = b.get(p.name)
        if seen is None:
            b[p.name] = a
            return True
        return seen == a
    if isinstance(p, Expr) and isinstance(a, Expr):
        if len(p.children) != len(a.children):
            return False
        return all(_unify(x, y, b) for x, y in zip(p.children, a.children, strict=True))
    return p == a
