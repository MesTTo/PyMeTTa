"""Purpose: read a space's declaration rows as the one projection every surface renders.

A space holds its own catalog: `(: name type)` says what a head is, `(= (head
...) body)` says how it answers, `(@doc name ...)` says what it means. Every
face this library grows over that -- the `.pyi` a checker reads, a card, an
OpenAPI document, the `llms.txt` roster -- is the same query rendered
differently, so the query is written once here and the renderers take rows
rather than reaching into a space each in their own way.

Assumes:
  - the subject answers `atoms()` with the atoms IT holds; an inherited
    space's rows belong to that space's own projection, not to this one
  - `atoms()` answers in the order the space stored them, which for a loaded
    file is source order [measured 2026-09-07: three runs of one four-atom
    program returned identical order]
Guarantees:
  - one row per head the space declares, defines or documents, in the order
    the space first mentions each [tested:
    test_declarations_carry_arrows_arities_and_documentation; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - a head's declared types stay in the space's order, so an overload family
    reaches a renderer the way it was written [tested:
    test_declarations_carry_arrows_arities_and_documentation; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - reading is one `atoms()` call and no evaluation, so a projection cannot
    run the program it describes [tested: test_stubs_read_the_space_without_evaluating_it;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeGuard

from .atoms import Atom, Expression, Symbol

if TYPE_CHECKING:
    from ._space import Space

DECLARE = Symbol(":")
EQUATION = Symbol("=")
DOCUMENTATION = Symbol("@doc")
TYPE = Symbol("Type")
ARROW = Symbol("->")


def is_arrow(atom: Atom) -> TypeGuard[Expression]:
    """Whether a type atom is a function type, `(-> ...)`."""
    return (
        isinstance(atom, Expression)
        and bool(atom.children)
        and atom.children[0] == ARROW
    )


@dataclass(frozen=True)
class Declaration:
    """Everything one space says about one head.

    `types` carries every `(: name ...)` row in the space's order, whether it
    is an arrow, the symbol `Type`, or a plain type; `arities` carries the
    MeTTa arities its equations answer at, ascending; `documentation` is the
    space's own `(@doc name ...)` atom, which formats to the text `help()`
    prints.
    """

    name: str
    types: tuple[Atom, ...] = ()
    arities: tuple[int, ...] = ()
    documentation: Expression | None = None

    @property
    def arrows(self) -> tuple[Expression, ...]:
        """The declared function types, which are the callable signatures."""
        return tuple(atom for atom in self.types if is_arrow(atom))

    @property
    def is_type(self) -> bool:
        """Whether the space declares this name as a type of its own."""
        return TYPE in self.types

    @property
    def defined(self) -> bool:
        """Whether the space holds equations for this head."""
        return bool(self.arities)


@dataclass
class _Rows:
    """One head's rows while the single pass is still collecting them."""

    types: list[Atom] = field(default_factory=list)
    arities: set[int] = field(default_factory=set)
    documentation: Expression | None = None


def _head_of(equation: Expression) -> tuple[str, int] | None:
    """The name and MeTTa arity an `(= head body)` row defines, if any."""
    if len(equation.children) < 2:
        return None
    head = equation.children[1]
    if isinstance(head, Symbol):
        return str(head), 0
    if isinstance(head, Expression) and head.children:
        first = head.children[0]
        if isinstance(first, Symbol):
            return str(first), len(head.children) - 1
    return None


def declarations(space: Space | Any) -> tuple[Declaration, ...]:
    """Read one space's heads: what each is declared as, defined at, documented as.

        for row in declarations(m.self):
            print(row.name, row.arrows, row.arities)

    The pass is over `atoms()` rather than three `match` calls because the
    three row shapes are one read of one store, and because a projection that
    matched would evaluate nothing but would still cost a query per shape.
    """
    collected: dict[str, _Rows] = {}
    for atom in space.atoms():
        if not isinstance(atom, Expression) or len(atom.children) < 2:
            continue
        head, *rest = atom.children
        if head == DECLARE and len(rest) == 2 and isinstance(rest[0], Symbol):
            collected.setdefault(str(rest[0]), _Rows()).types.append(rest[1])
        elif head == EQUATION:
            defined = _head_of(atom)
            if defined is not None:
                name, arity = defined
                collected.setdefault(name, _Rows()).arities.add(arity)
        elif head == DOCUMENTATION and isinstance(rest[0], Symbol):
            rows = collected.setdefault(str(rest[0]), _Rows())
            if rows.documentation is None:
                rows.documentation = atom
    return tuple(
        Declaration(
            name=name,
            types=tuple(rows.types),
            arities=tuple(sorted(rows.arities)),
            documentation=rows.documentation,
        )
        for name, rows in collected.items()
    )
