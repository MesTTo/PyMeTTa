"""Purpose: proof trees as Python objects. Parses the (derivation ...) atoms
the shim's meta-interpreter produces into a tree of steps, facts and builtin
leaves, records finite-depth truncation without confusing it with no proof,
and renders the result as indented text or notebook HTML.
Guarantees:
  - Derivation.complete is false exactly when a Truncated node occurs
    [tested test_depth_exhaustion_returns_a_partial_proof]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: why-not trees for derivations that fail.
"""

from __future__ import annotations

import html
import string
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeGuard

from .atoms import Atom, Expr, Gnd, Sym, Var, map_atoms

__all__ = ["Builtin", "Derivation", "Fact", "Step", "Truncated"]


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
class Truncated:
    """A finite proof budget ended before this engine goal was explained."""

    text: str

    def render(self, indent: int) -> str:
        return f"{'  ' * indent}truncated {self.text}"


@dataclass(frozen=True)
class Step:
    """One equation firing: the call it answered and the equation used."""

    call: Atom
    answer: Atom
    equation: Atom
    children: tuple[Node, ...] = field(default_factory=tuple)

    def render(self, indent: int) -> str:
        pad = "  " * indent
        lines = [
            f"{pad}{self.call} = {self.answer}",
            f"{pad}  by {_pretty(self.equation)}",
        ]
        lines.extend(c.render(indent + 1) for c in self.children)
        return "\n".join(lines)


Node = Step | Fact | Builtin | Truncated


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
    def from_atom(tree: Atom) -> Derivation:
        """Parse the (derivation (answer Call Out) Steps...) atom."""
        if not (
            isinstance(tree, Expr)
            and _headed(tree, "derivation")
            and len(tree) >= 2
        ):
            msg = (
                f"malformed derivation node {tree}: expected "
                f"(derivation (answer Call Out) Step...)"
            )
            raise ValueError(
                msg
            )
        answer_expr = tree[1]
        if not (_headed(answer_expr, "answer") and len(answer_expr) == 3):
            msg = f"malformed answer node {answer_expr}: expected (answer Call Out)"
            raise ValueError(
                msg
            )
        call, out = answer_expr[1], answer_expr[2]
        children = tuple(_node(c) for c in tree.children[2:])
        return Derivation(call=call, answer=out, children=children)

    @property
    def facts(self) -> list[Fact]:
        seen: list[Fact] = []
        for node in _walk(self.children):
            if isinstance(node, Fact) and node not in seen:
                seen.append(node)
        return seen

    @property
    def rules(self) -> list[Atom]:
        seen: list[Atom] = []
        for n in _walk(self.children):
            if isinstance(n, Step) and n.equation not in seen:
                seen.append(n.equation)
        return seen

    @property
    def truncations(self) -> list[Truncated]:
        """Every point where a finite depth stopped this proof walk."""
        return [n for n in _walk(self.children) if isinstance(n, Truncated)]

    @property
    def complete(self) -> bool:
        """Whether the tree explains the proof without a depth cutoff."""
        return not self.truncations

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
    names = string.ascii_lowercase
    mapping: dict[str, str] = {}

    def rename(a: Atom) -> Atom:
        if isinstance(a, Var):
            # Only machine names are renamed; a name the author wrote stays.
            if not a.name.startswith("_"):
                return a
            if a.name not in mapping:
                index = len(mapping)
                fresh = names[index] if index < len(names) else f"v{index}"
                mapping[a.name] = fresh
            return Var(mapping[a.name])
        return a

    return map_atoms(atom, rename)


def _headed(e: Atom, name: str) -> TypeGuard[Expr]:
    return (
        isinstance(e, Expr)
        and len(e) > 0
        and isinstance(e.head, Sym)
        and e.head.name == name
    )


def _step_node(node: Expr) -> Step:
    if len(node) < 3:
        msg = (
            f"malformed step node {node}: expected "
            f"(step (call Call Out) Equation Child...)"
        )
        raise ValueError(
            msg
        )
    call_expr = node[1]
    if not (_headed(call_expr, "call") and len(call_expr) == 3):
        msg = f"malformed call node {call_expr}: expected (call Call Out)"
        raise ValueError(msg)
    call, out = call_expr[1], call_expr[2]
    children = tuple(_node(child) for child in node.children[3:])
    return Step(call=call, answer=out, equation=node[2], children=children)


def _fact_node(node: Expr) -> Fact:
    if len(node) != 3:
        msg = f"malformed fact node {node}: expected (fact Space Atom)"
        raise ValueError(msg)
    space = node[1]
    name = space.name if isinstance(space, Sym) else str(space)
    return Fact(space=name, atom=node[2])


def _text_node(
    node: Expr,
    name: str,
    constructor: Callable[[str], Node],
) -> Node:
    if len(node) != 2:
        msg = f"malformed {name} node {node}: expected ({name} Text)"
        raise ValueError(msg)
    payload = node[1]
    text = payload.value if isinstance(payload, Gnd) else str(payload)
    return constructor(str(text))


def _node(e: Atom) -> Node:
    if _headed(e, "step"):
        return _step_node(e)
    if _headed(e, "fact"):
        return _fact_node(e)
    if _headed(e, "builtin"):
        return _text_node(e, "builtin", Builtin)
    if _headed(e, "truncated"):
        return _text_node(e, "truncated", Truncated)
    msg = f"malformed derivation node {e}: expected step, fact, builtin, or truncated"
    raise ValueError(
        msg
    )


def _walk(nodes: tuple[Node, ...]):
    for n in nodes:
        yield n
        if isinstance(n, Step):
            yield from _walk(n.children)
