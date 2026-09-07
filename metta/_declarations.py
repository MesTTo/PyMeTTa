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
  - inferred() answers one row per (head, arity) the space mentions and does
    not declare, from the same catalogue split declarations() reads, so a
    head is never both declared and proposed [tested:
    test_a_declared_head_is_skipped, test_a_catalogue_row_is_not_data_about_a_head,
    test_a_position_takes_the_narrowest_kind_covering_its_children,
    shim_type_inference; commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
  - a head's declared types stay in the space's order, so an overload family
    reaches a renderer the way it was written [tested:
    test_declarations_carry_arrows_arities_and_documentation; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - reading is one `atoms()` call and no evaluation, so a projection cannot
    run the program it describes [tested: test_stubs_read_the_space_without_evaluating_it;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - the projection is over ATOMS, so a space's store and a file's own forms
    reach the same rows and a module can report what its FILE declares rather
    than what the space it loaded into holds [tested:
    test_a_metta_file_imports_as_a_module_of_its_own_heads; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - a subject that knows where its atoms were written answers the same rows
    with an `origin` and a `documentation_origin` on each, and a head it
    publishes through one of the language's registration forms is a row like
    any other; a Space answers `atoms()` and its rows carry none of the three,
    which is the same pass and the same cost it always had [tested:
    test_a_card_lists_the_heads_a_registration_form_publishes,
    test_rows_are_the_query_the_reference_page_renders,
    test_a_registered_head_is_counted_in_the_reference; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NamedTuple, TypeGuard

from .atoms import Atom, Expression, Symbol, _atom_from_wire

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from ._source_forms import Origin
    from ._space import Space

DECLARE = Symbol(":")
EQUATION = Symbol("=")
DOCUMENTATION = Symbol("@doc")
TYPE = Symbol("Type")
ARROW = Symbol("->")

#: What an inferred arrow says about itself wherever one is shown -- a
#: signature, a docstring, a stub -- so a reader can tell a proposal from a
#: promise without asking a second door. `Space.infer_types(declare=True)` is
#: the only thing that turns one into a declaration.
INFERRED_NOTE = "(inferred from stored atoms, not declared)"


def is_arrow(atom: Atom) -> TypeGuard[Expression]:
    """Whether a type atom is a function type, `(-> ...)`."""
    return (
        isinstance(atom, Expression)
        and bool(atom.children)
        and atom.children[0] == ARROW
    )


class Written(NamedTuple):
    """One atom as a SOURCE holds it, which is more than a space can say.

    A space answers atoms; a source also knows where each one was written and
    which heads a form of it registers, and both are things a description of
    the source has to carry. `registers` is empty for everything but a
    registration form, and the names in it are the engine's answer rather than
    this side's reading of the form
    [source: engine/metta/interop.pl, metta_string_registrations/2].
    """

    atom: Atom
    origin: Origin | None = None
    registers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Declaration:
    """Everything one space says about one head.

    `types` carries every `(: name ...)` row in the space's order, whether it
    is an arrow, the symbol `Type`, or a plain type; `arities` carries the
    MeTTa arities its equations answer at, ascending; `documentation` is the
    space's own `(@doc name ...)` atom, which formats to the text `help()`
    prints.

    `origin` is where the subject FIRST mentions the head and
    `documentation_origin` is where its `(@doc ...)` row sits, which is a
    different line whenever a head is documented away from its definition;
    `registered` says the subject publishes it through one of the language's
    registration forms. All three are answered by a source and are None,
    None and False for a space, which holds atoms and knows nothing about
    where they were written.
    """

    name: str
    types: tuple[Atom, ...] = ()
    arities: tuple[int, ...] = ()
    documentation: Expression | None = None
    origin: Origin | None = None
    documentation_origin: Origin | None = None
    registered: bool = False

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

    @property
    def carried(self) -> bool:
        """Whether the subject gives this head meaning rather than only prose.

        A head with a type, an equation or a registration is one the subject
        PUBLISHES; a head with nothing but an `(@doc ...)` row is documentation
        about a name that lives elsewhere, which is why the generated library
        reference counts the two differently.
        """
        return bool(self.types) or self.defined or self.registered


@dataclass
class _Rows:
    """One head's rows while the single pass is still collecting them."""

    types: list[Atom] = field(default_factory=list)
    arities: set[int] = field(default_factory=set)
    documentation: Expression | None = None
    origin: Origin | None = None
    documentation_origin: Origin | None = None
    registered: bool = False


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


def written(subject: Space | Any) -> Iterator[Written]:
    """Every atom of a subject, with what it knows about where each came from.

    A source view answers `written()` itself; anything else answers `atoms()`,
    which is the whole `Space` surface this reader has ever needed, and its
    rows carry no position because a stored atom has none.
    """
    source = getattr(subject, "written", None)
    if source is None:
        return (Written(atom) for atom in subject.atoms())
    rows: Iterable[Written] = source()
    return iter(rows)


def declarations(subject: Space | Any) -> tuple[Declaration, ...]:
    """Read one subject's heads: what each is declared as, defined at, documented as.

        for row in declarations(m.self):
            print(row.name, row.arrows, row.arities)

    The pass is over `atoms()` rather than three `match` calls because the
    three row shapes are one read of one store, and because a projection that
    matched would evaluate nothing but would still cost a query per shape.
    A subject that also knows where its atoms were written, which a library's
    own source does, answers the same rows with an `origin` on each.
    """
    return declarations_in(written(subject))


def declarations_in(items: Iterable[Atom | Written]) -> tuple[Declaration, ...]:
    """The same rows over any atoms, whatever holds them.

    A space's store is one source of them, and `declarations(space)` is that
    reading. A FILE's own forms are another: the import hook's module reports
    the heads its file declares, which is a different set from the heads the
    space it loaded into can call, and both are this one projection. An item
    may be a bare atom, which knows no position, or a `Written` entry, which
    also says where it was written and which heads its form registers.
    """
    collected: dict[str, _Rows] = {}

    def rows_for(name: str, origin: Origin | None) -> _Rows:
        """This head's collector, remembering where it was first mentioned."""
        rows = collected.setdefault(name, _Rows())
        if rows.origin is None:
            rows.origin = origin
        return rows

    for item in items:
        entry = item if isinstance(item, Written) else Written(item)
        atom = entry.atom
        for name in entry.registers:
            rows_for(name, entry.origin).registered = True
        if not isinstance(atom, Expression) or len(atom.children) < 2:
            continue
        head, *rest = atom.children
        if head == DECLARE and len(rest) == 2 and isinstance(rest[0], Symbol):
            rows_for(str(rest[0]), entry.origin).types.append(rest[1])
        elif head == EQUATION:
            defined = _head_of(atom)
            if defined is not None:
                name, arity = defined
                rows_for(name, entry.origin).arities.add(arity)
        elif head == DOCUMENTATION and isinstance(rest[0], Symbol):
            rows = rows_for(str(rest[0]), entry.origin)
            if rows.documentation is None:
                rows.documentation = atom
                rows.documentation_origin = entry.origin
    return tuple(
        Declaration(
            name=name,
            types=tuple(rows.types),
            arities=tuple(sorted(rows.arities)),
            documentation=rows.documentation,
            origin=rows.origin,
            documentation_origin=rows.documentation_origin,
            registered=rows.registered,
        )
        for name, rows in collected.items()
    )


@dataclass(frozen=True)
class Inference:
    """The arrow one head's stored atoms justify, for a head nothing declares.

    `arguments` is one type per position and `result` is what the head
    answers, both as atoms rather than names so a declared result that is
    itself an expression, `(List Number)`, arrives whole. A head observed at
    two arities is two rows, because two arities are two signatures.
    """

    name: str
    arguments: tuple[Atom, ...]
    result: Atom

    @property
    def arity(self) -> int:
        """How many arguments this row saw the head take."""
        return len(self.arguments)

    @property
    def arrow(self) -> Expression:
        """The proposed function type, `(-> T1 .. Tn R)`."""
        return Expression([ARROW, *self.arguments, self.result])

    @property
    def declaration(self) -> Expression:
        """The proposal as the atom `declare=True` would add, `(: name arrow)`."""
        return Expression([DECLARE, Symbol(self.name), self.arrow])


def inferred(space: Space | Any) -> tuple[Inference, ...]:
    """Propose an arrow for every head this space mentions and never declares.

        for row in inferred(m.self):
            print(row.declaration)

    The walk is the engine's `metta_py_infer_types/2`, because naming the
    narrowest kind covering a position needs the language's own answer for a
    nested call's head, and this side turns its wire rows into atoms.
    ``Space.infer_types()`` is the public door and makes the enumerate
    capability check first; a caller here has already read the space, the way
    ``head_origins`` assumes of the space it is handed.
    """
    rows = space._rt.apply_must("metta_py_infer_types", space._space)
    return tuple(
        Inference(
            name=str(name),
            arguments=tuple(_atom_from_wire(kind) for kind in kinds),
            result=_atom_from_wire(result),
        )
        for name, _arity, kinds, result in rows
    )
