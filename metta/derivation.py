"""Purpose: proof trees as Python objects. Parses the (derivation ...) atoms
the shim's meta-interpreter produces into a tree of steps, facts and builtin
leaves, records finite-depth truncation without confusing it with no proof,
and renders the result as indented text or notebook HTML.
Guarantees:
  - Derivation.complete is false exactly when a Truncated node occurs
    [tested test_depth_exhaustion_returns_a_partial_proof]
  - parsing, walking, and rendering use explicit work stacks, so proof depth is
    data rather than Python recursion [tested:
    test_deep_proof_consumers_treat_depth_as_data; commit=WORKTREE]
  - facts and rules retain first-seen order with expected linear-time hash
    membership [tested: test_fact_and_rule_projection_use_hash_membership;
    commit=WORKTREE]
  - post-order construction and pre-order traversal follow established
    iterative tree algorithms [source: extensions/python/metta/_atom_wire.py:
    _from_wire and psf/black pytree.py post_order at upstream commit
    8947c48ef2077c3a301b03c1e814dc2e3f78436e; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: why-not trees for derivations that fail.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import html
import string
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TypeGuard

from .atoms import Atom, Expression, Grounded, Symbol, Variable, _map_atoms

__all__ = ["Builtin", "Derivation", "Fact", "Step", "Truncated"]


@dataclass(frozen=True)
class Fact:
    """A stored atom the proof rests on, and the space holding it."""

    space: str
    atom: Atom

    def render(self, indent: int) -> str:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return f"{'  ' * indent}fact {self.atom}   [{self.space}]"


@dataclass(frozen=True)
class Builtin:
    """An engine-level goal the proof used, kept as the engine wrote it."""

    text: str

    def render(self, indent: int) -> str:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return f"{'  ' * indent}builtin {self.text}"


@dataclass(frozen=True)
class Truncated:
    """A finite proof budget ended before this engine goal was explained."""

    text: str

    def render(self, indent: int) -> str:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return f"{'  ' * indent}truncated {self.text}"


@dataclass(frozen=True)
class Step:
    """One equation firing: the call it answered and the equation used."""

    call: Atom
    answer: Atom
    equation: Atom
    children: tuple[Node, ...] = field(default_factory=tuple)

    def render(self, indent: int) -> str:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return "\n".join(_render_nodes((self,), indent))


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
            isinstance(tree, Expression)
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
        children = _nodes(tree.children[2:])
        return Derivation(call=call, answer=out, children=children)

    @property
    def facts(self) -> list[Fact]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return list(dict.fromkeys(node for node in _walk(self.children) if isinstance(node, Fact)))

    @property
    def rules(self) -> list[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return list(
            dict.fromkeys(node.equation for node in _walk(self.children) if isinstance(node, Step))
        )

    @property
    def truncations(self) -> list[Truncated]:
        """Every point where a finite depth stopped this proof walk."""
        return [n for n in _walk(self.children) if isinstance(n, Truncated)]

    @property
    def complete(self) -> bool:
        """Whether the tree explains the proof without a depth cutoff."""
        return not self.truncations

    def __str__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        lines = [f"{self.call} = {self.answer}"]
        lines.extend(_render_nodes(self.children, 1))
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
        if isinstance(a, Variable):
            # Only machine names are renamed; a name the author wrote stays.
            if not a.name.startswith("_"):
                return a
            if a.name not in mapping:
                index = len(mapping)
                fresh = names[index] if index < len(names) else f"v{index}"
                mapping[a.name] = fresh
            return Variable(mapping[a.name])
        return a

    return _map_atoms(atom, rename)


def _headed(e: Atom, name: str) -> TypeGuard[Expression]:
    return (
        isinstance(e, Expression)
        and len(e) > 0
        and isinstance(e.head, Symbol)
        and e.head.name == name
    )


def _step_parts(
    node: Expression,
) -> tuple[Atom, Atom, Atom, tuple[Atom, ...]]:
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
    return call, out, node[2], node.children[3:]


def _fact_node(node: Expression) -> Fact:
    if len(node) != 3:
        msg = f"malformed fact node {node}: expected (fact Space Atom)"
        raise ValueError(msg)
    space = node[1]
    name = space.name if isinstance(space, Symbol) else str(space)
    return Fact(space=name, atom=node[2])


def _text_node(
    node: Expression,
    name: str,
    constructor: Callable[[str], Node],
) -> Node:
    if len(node) != 2:
        msg = f"malformed {name} node {node}: expected ({name} Text)"
        raise ValueError(msg)
    payload = node[1]
    value = getattr(payload, "value", None) if isinstance(payload, Grounded) else None
    text = value if value is not None else str(payload)
    return constructor(str(text))


def _leaf_node(e: Atom) -> Node:
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


@dataclass(frozen=True, slots=True)
class _PendingStep:
    call: Atom
    answer: Atom
    equation: Atom
    width: int


def _nodes(nodes: tuple[Atom, ...]) -> tuple[Node, ...]:
    """Parse proof nodes post-order with depth held in an explicit stack."""
    # Black's post_order uses the same enter/finish work-stack pattern so a
    # nested tree does not retain one delegating generator per level.
    # https://github.com/psf/black/blob/8947c48ef2077c3a301b03c1e814dc2e3f78436e/src/blib2to3/pytree.py#L313-L326
    stack: list[Atom | _PendingStep] = list(reversed(nodes))
    built: list[Node] = []
    while stack:
        item = stack.pop()
        if isinstance(item, _PendingStep):
            children = tuple(built[-item.width :]) if item.width else ()
            if item.width:
                del built[-item.width :]
            built.append(Step(item.call, item.answer, item.equation, children))
            continue
        if _headed(item, "step"):
            call, answer, equation, children = _step_parts(item)
            stack.append(_PendingStep(call, answer, equation, len(children)))
            stack.extend(reversed(children))
            continue
        built.append(_leaf_node(item))
    return tuple(built)


def _node(e: Atom) -> Node:
    return _nodes((e,))[0]


def _walk(nodes: tuple[Node, ...]) -> Iterator[Node]:
    """Yield proof nodes pre-order with depth held in an explicit stack."""
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, Step):
            stack.extend(reversed(node.children))


def _render_nodes(nodes: tuple[Node, ...], indent: int) -> list[str]:
    """Render proof nodes in pre-order without recursive string assembly."""
    lines: list[str] = []
    stack = [(node, indent) for node in reversed(nodes)]
    while stack:
        node, level = stack.pop()
        if isinstance(node, Step):
            pad = "  " * level
            lines.append(f"{pad}{node.call} = {node.answer}")
            lines.append(f"{pad}  by {_pretty(node.equation)}")
            stack.extend((child, level + 1) for child in reversed(node.children))
        else:
            lines.append(node.render(level))
    return lines
