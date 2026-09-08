"""Purpose: proof trees as Python objects. Parses the (derivation ...) atoms
the shim's meta-interpreter produces into a tree of steps, facts and builtin
leaves, records finite-depth truncation without confusing it with no proof,
and renders the result as indented text or notebook HTML.
Guarantees:
  - Derivation.complete is false exactly when a Truncated node occurs
    [tested test_depth_exhaustion_returns_a_partial_proof]
  - parsing, walking, and rendering use explicit work stacks, so proof depth is
    data rather than Python recursion [tested:
    test_deep_proof_consumers_treat_depth_as_data;
    commit=97df27ef8346695707d87fc9bec6a8761cff574e]
  - facts and rules retain first-seen order with expected linear-time hash
    membership [tested: test_fact_and_rule_projection_use_hash_membership;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - post-order construction and pre-order traversal follow established
    iterative tree algorithms [source: extensions/python/metta/_atom_wire.py:
    _from_wire and psf/black pytree.py post_order at upstream commit
    8947c48ef2077c3a301b03c1e814dc2e3f78436e;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - every node class is a projection of one declared row: the parser reads the
    row's field list rather than counting positions by hand, and `_check_rows()`
    holds each class's dataclass fields to that list at import, both ways, so a
    field added to one and not the other refuses on the way in [tested:
    test_a_node_class_and_its_row_declare_the_same_fields; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: why-not trees for derivations that fail.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import html
import string
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, fields
from typing import Any, Final, NamedTuple, TypeGuard

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
        """Parse the (derivation (answer Call Answer) Step...) atom."""
        return Derivation(
            **_parts(tree, _DERIVATION),
            children=_nodes(tree.children[_DERIVATION.arity :]),
        )

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


def _atom(part: Atom) -> Atom:
    """A field carried as the atom it is."""
    return part


def _name(part: Atom) -> str:
    """A field carried as a symbol, read as its name."""
    return part.name if isinstance(part, Symbol) else str(part)


def _text(part: Atom) -> str:
    """A field carried as the engine's own text, grounded or symbolic."""
    value = getattr(part, "value", None) if isinstance(part, Grounded) else None
    return str(value if value is not None else part)


class _Pair(NamedTuple):
    """A nested `(head A B)` row, read as two named fields of its parent.

    `(step (call Call Out) Equation ...)` and
    `(derivation (answer Call Out) ...)` both carry their two subjects one
    level down, which is where the head that names the pair lives.
    """

    head: str
    names: tuple[str, str]


class _Row(NamedTuple):
    """One row of the derivation grammar, and the node it projects to.

    `fields` is the row's own field list, in the order the engine writes them:
    a `(name, reader)` pair for a field carried in place, a `_Pair` for one
    carried as a nested two-part row. `children` says the row ends in a
    variable number of child nodes, which only `step` and `derivation` do.

    The node classes above are these field lists, typed. `_check_rows()`
    holds the two together at import, so a field added to `Step` without a
    field added here -- or the reverse -- is a refusal on the first import
    rather than a node built with a hole in it.
    """

    head: str
    #: `type[Any]` rather than `type`: every node is a dataclass and
    #: `dataclasses.fields` takes one, which a bare `type` does not satisfy.
    node: type[Any]
    fields: tuple[tuple[str, Callable[[Atom], Any]] | _Pair, ...]
    children: bool = False

    @property
    def names(self) -> tuple[str, ...]:
        """Every field name this row carries, nested pairs flattened."""
        found: list[str] = []
        for field_of in self.fields:
            if isinstance(field_of, _Pair):
                found.extend(field_of.names)
            else:
                found.append(field_of[0])
        return tuple(found)

    @property
    def arity(self) -> int:
        """How many children a well-formed row of this shape has, head included."""
        return len(self.fields) + 1

    def spelling(self) -> str:
        """The row as its grammar, for a refusal that names what was expected."""
        parts = [
            f"({field_of.head} {' '.join(name.title() for name in field_of.names)})"
            if isinstance(field_of, _Pair)
            else field_of[0].title()
            for field_of in self.fields
        ]
        tail = " Child..." if self.children else ""
        return f"({self.head} {' '.join(parts)}{tail})"


#: The proof grammar, one row per node the meta-interpreter writes. Every
#: reader below walks THIS rather than a shape of its own, which is the model
#: `metta._projection` uses for the type table: one table, a column per target.
_DERIVATION: Final = _Row(
    "derivation", Derivation, (_Pair("answer", ("call", "answer")),), children=True
)
_STEP: Final = _Row(
    "step",
    Step,
    (_Pair("call", ("call", "answer")), ("equation", _atom)),
    children=True,
)
# closed-set: decides; policy=the proof grammar's leaf rows and the node class each projects to; reads=none, it is the source, and `_check_rows()` holds every class to its row at import
_LEAVES: Final[tuple[_Row, ...]] = (
    _Row("fact", Fact, (("space", _name), ("atom", _atom))),
    _Row("builtin", Builtin, (("text", _text),)),
    _Row("truncated", Truncated, (("text", _text),)),
)


def _check_rows() -> None:
    """Hold every node class to its row, both ways, at import."""
    for row in (_DERIVATION, _STEP, *_LEAVES):
        declared = tuple(
            field_of.name
            for field_of in fields(row.node)
            if field_of.name != "children"
        )
        if declared != row.names:
            msg = (
                f"the {row.head} row declares {row.names} and "
                f"{row.node.__name__} carries {declared}; one grammar, one class"
            )
            raise ValueError(msg)


_check_rows()


def _parts(node: Atom, row: _Row) -> dict[str, Any]:
    """One row read into its declared fields, refusing any other shape."""
    if not (_headed(node, row.head) and len(node) >= row.arity):
        msg = f"malformed {row.head} node {node}: expected {row.spelling()}"
        raise ValueError(msg)
    if not row.children and len(node) != row.arity:
        msg = f"malformed {row.head} node {node}: expected {row.spelling()}"
        raise ValueError(msg)
    read: dict[str, Any] = {}
    for position, field_of in enumerate(row.fields, start=1):
        part = node[position]
        if isinstance(field_of, _Pair):
            if not (_headed(part, field_of.head) and len(part) == 3):
                msg = (
                    f"malformed {field_of.head} node {part}: expected "
                    f"({field_of.head} "
                    f"{' '.join(name.title() for name in field_of.names)})"
                )
                raise ValueError(msg)
            read[field_of.names[0]] = part[1]
            read[field_of.names[1]] = part[2]
        else:
            name, reader = field_of
            read[name] = reader(part)
    return read


def _leaf_node(e: Atom) -> Node:
    """One leaf, built from whichever row of the grammar it is."""
    for row in _LEAVES:
        if _headed(e, row.head):
            return row.node(**_parts(e, row))
    expected = ", ".join(row.head for row in (_STEP, *_LEAVES))
    msg = f"malformed derivation node {e}: expected {expected}"
    raise ValueError(msg)


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
        if _headed(item, _STEP.head):
            read = _parts(item, _STEP)
            child_atoms = item.children[_STEP.arity :]
            stack.append(
                _PendingStep(
                    read["call"], read["answer"], read["equation"], len(child_atoms)
                )
            )
            stack.extend(reversed(child_atoms))
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
            lines.extend(
                (
                    f"{pad}{node.call} = {node.answer}",
                    f"{pad}  by {_pretty(node.equation)}",
                )
            )
            stack.extend((child, level + 1) for child in reversed(node.children))
        else:
            lines.append(node.render(level))
    return lines
