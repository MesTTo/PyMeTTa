"""Purpose: proof trees as Python objects. Parses the (derivation ...) atoms
the shim's meta-interpreter produces into a tree of steps, facts and builtin
leaves, and renders it as indented text or notebook HTML.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: why-not trees for derivations that fail.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Union

from .atoms import Atom, Expr, Gnd, Sym

__all__ = ["Derivation", "Step", "Fact", "Builtin"]


@dataclass(frozen=True)
class Fact:
    """A stored atom the proof rests on, and the space holding it."""

    space: str
    atom: Atom

    def render(self, indent: int) -> str:
        return f"{'  ' * indent}fact {self.atom}   [{self.space}]"


@dataclass(frozen=True)
class Builtin:
    """An engine-level goal the proof used, kept as the engine wrote it."""

    text: str

    def render(self, indent: int) -> str:
        return f"{'  ' * indent}builtin {self.text}"


@dataclass(frozen=True)
class Step:
    """One equation firing: the call it answered and the equation used."""

    call: Atom
    answer: Atom
    equation: Atom
    children: tuple["Node", ...] = field(default_factory=tuple)

    def render(self, indent: int) -> str:
        pad = "  " * indent
        lines = [
            f"{pad}{self.call} = {self.answer}",
            f"{pad}  by {_pretty(self.equation)}",
        ]
        lines.extend(c.render(indent + 1) for c in self.children)
        return "\n".join(lines)


Node = Union[Step, Fact, Builtin]


@dataclass(frozen=True)
class Derivation:
    """One complete proof of an answer.

    steps are the equations that fired in order; facts and rules list the
    leaves and equations involved, deduplicated, which is usually the part a
    reader wants first.
    """

    call: Atom
    answer: Atom
    children: tuple[Node, ...]

    @staticmethod
    def from_atom(tree: Atom) -> "Derivation":
        """Parse the (derivation (answer Call Out) Steps...) atom."""
        if not (isinstance(tree, Expr) and _headed(tree, "derivation")):
            raise ValueError(f"not a derivation atom: {tree}")
        answer_expr = tree[1]
        call, out = answer_expr[1], answer_expr[2]
        children = tuple(_node(c) for c in tree.children[2:])
        return Derivation(call=call, answer=out, children=children)

    @property
    def facts(self) -> list[Fact]:
        return [n for n in _walk(self.children) if isinstance(n, Fact)]

    @property
    def rules(self) -> list[Atom]:
        seen: list[Atom] = []
        for n in _walk(self.children):
            if isinstance(n, Step) and n.equation not in seen:
                seen.append(n.equation)
        return seen

    def __str__(self) -> str:
        lines = [f"{self.call} = {self.answer}"]
        lines.extend(c.render(1) for c in self.children)
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        return f"<pre>{html.escape(str(self))}</pre>"


def _pretty(atom: Atom) -> Atom:
    """The same equation with readable variable names, for display only.

    Compiled equations carry machine names such as $_121118; rendering maps
    them to $a, $b, ... in appearance order. The stored tree keeps the
    originals, so nothing downstream loses the real identity.
    """
    from .atoms import Expr as E, Var as Vr

    names = "abcdefghijklmnopqrstuvwxyz"
    mapping: dict[str, str] = {}

    def walk(a: Atom) -> Atom:
        if isinstance(a, Vr):
            # Only machine names are renamed; a name the author wrote stays.
            if not a.name.startswith("_"):
                return a
            if a.name not in mapping:
                index = len(mapping)
                fresh = names[index] if index < len(names) else f"v{index}"
                mapping[a.name] = fresh
            return Vr(mapping[a.name])
        if isinstance(a, E):
            return E([walk(c) for c in a.children])
        return a

    return walk(atom)


def _headed(e: Atom, name: str) -> bool:
    return (
        isinstance(e, Expr)
        and len(e) > 0
        and isinstance(e.head, Sym)
        and e.head.name == name
    )


def _node(e: Atom) -> Node:
    if _headed(e, "step"):
        call_expr = e[1]  # (call (f args...) Out)
        call, out = call_expr[1], call_expr[2]
        equation = e[2]
        children = tuple(_node(c) for c in e.children[3:])
        return Step(call=call, answer=out, equation=equation, children=children)
    if _headed(e, "fact"):
        space = e[1]
        name = space.name if isinstance(space, Sym) else str(space)
        return Fact(space=name, atom=e[2])
    if _headed(e, "builtin"):
        payload = e[1]
        text = payload.value if isinstance(payload, Gnd) else str(payload)
        return Builtin(text=str(text))
    raise ValueError(f"unknown derivation node: {e}")


def _walk(nodes: tuple[Node, ...]):
    for n in nodes:
        yield n
        if isinstance(n, Step):
            yield from _walk(n.children)
