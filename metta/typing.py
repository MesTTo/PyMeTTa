"""Purpose: declare what SHAPE a head's result has, as rows over registrable
rule kinds, so the engine derives the type instead of a Python table assembling
the equations.

A shape rule is an algebra over an indexed carrier. `preserve` keeps the
operand's shape, `broadcast` is NumPy's rule for two of them, `reduce-all`
answers a scalar, `concatenate-axis` sums one axis. None of that is about
arrays: a dataframe is rows by columns, an image is height by width by
channels, a series is a length, and every one of those wants the same rules.
So a rule KIND is a row on the seam's `typing` point, carrying its equations as
TEMPLATE atoms, and a HEAD declares which kind it follows as an ordinary
`(typing <space> <head> <kind> <arg>...)` row in the space. The space is the
row's own first field because that is what retires it: a released space takes
its declarations with it, and without the field a row survived the space that
declared it and could not be withdrawn.

    seam.typing.register(
        "broadcast",
        doc="the two operands' shapes, broadcast",
        equations=(template,),
    )
    undo = typing.declare(space, "t+", "broadcast")

A template carries `$head` where the head goes and `$arg1`, `$arg2`, ... where
the row's own arguments go; instantiating one substitutes them and adds the
result to the space, which is the same equation a hand-written builder produced
and is now data a program can read, store and rewrite.

Assumes:
  - the engine evaluates a `(= (get-type (<head> ...)) ...)` equation exactly
    as it evaluates one a program wrote, which is what makes a template the
    whole of a rule [source: engine/metta/terms.pl, metta_types_match/2]
  - nothing puts `extensions/python/metta/` itself on `sys.path`. This module
    is named for the point it serves and shares that name with the standard
    library's, which Python 3's absolute imports keep apart: `from typing
    import ...` anywhere in this package reaches the stdlib because the
    package DIRECTORY is not a search path. Adding it makes this file shadow
    the stdlib for the package's own imports, which no consumer does and no
    runner here does -- pytest inserts `extensions/python`, where conftest.py
    is
Guarantees:
  - a head's declaration is a row in the space's own catalog, marked
    `(owned-by-space typing)` so it dies with the space, and the equations it
    added are withdrawn by the inverse `declare` answers [tested:
    test_the_declaration_is_a_row,
    test_the_inverse_withdraws_the_row_and_its_equations; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
  - a kind nobody registered refuses by name, listing the kinds that are
    registered [tested: test_an_unregistered_kind_refuses_by_name;
    commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
  - a row whose argument count does not fill the template's holes refuses
    naming both counts [tested: test_a_row_that_does_not_fill_the_template_refuses;
    commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
  - a stranger's rule kind reaches the point exactly as the shipped ones do
    [tested: extensions/python/tests/ch20_extending_the_engine/test_typing_point.py;
    commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final

from . import seam as _seam
from ._api_types import SpaceLike
from .atoms import Atom, Expression, S, V, Variable, _expr, _map_atoms, parse, seg
from .errors import MettaError

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["ROW_HEAD", "declare", "rules", "template", "withdraw"]

#: The head of a head's own declaration row:
#: `(typing <space> <head> <kind> <arg>...)`. The SPACE is the first field
#: because that is where the declaration happened: two spaces on two libraries
#: declare their own rules and answer their own rows, and the row dies with the
#: space because the head is marked `(owned-by-space typing)` in the same
#: catalog. The array layer's roster carries its space for the same reason
#: [source: extensions/python/ext/metta-arrays/metta_arrays.py, _ROSTER_HEAD].
ROW_HEAD: Final[str] = "typing"

#: The template hole that carries the head a rule is declared for.
HEAD_HOLE: Final[str] = "head"

#: The template holes that carry the row's own arguments, `$arg1` upward.
_ARGUMENT_HOLE = re.compile(r"^arg([1-9][0-9]*)$")

_CATALOG: Final[str] = "&metta"


def template(source: str | Atom) -> Atom:
    """One rule kind's equation template, from source text or an atom.

    Text is the escape hatch a registrant writes a whole form in, and it is
    parsed once here; an atom built with `S` and `V` is the ordinary spelling
    and passes straight through.
    """
    return parse(source) if isinstance(source, str) else source


def _holes(atom: Atom) -> int:
    """How many `$argN` holes a template carries, by its highest N.

    By the highest rather than by the count, because a template may use one
    hole twice and skipping one is a mistake this refuses at the row rather
    than leaving an unbound variable in an equation.
    """
    highest = 0
    found: set[int] = set()
    for part in _variables(atom):
        match = _ARGUMENT_HOLE.match(part)
        if match is not None:
            index = int(match.group(1))
            highest = max(highest, index)
            found.add(index)
    missing = sorted(set(range(1, highest + 1)) - found)
    if missing:
        holes = ", ".join(f"$arg{index}" for index in missing)
        msg = (
            f"a rule template numbers its argument holes from $arg1 without "
            f"gaps; this one reaches $arg{highest} and never uses {holes}"
        )
        raise MettaError(msg)
    return highest


def _variables(atom: Atom) -> set[str]:
    """Every variable NAME in one template."""
    names: set[str] = set()

    def visit(part: Atom) -> Atom:
        if isinstance(part, Variable):
            names.add(part.name)
        return part

    _map_atoms(atom, visit)
    return names


def _instantiate(atom: Atom, head: Atom, arguments: tuple[Atom, ...]) -> Atom:
    """One template with its head and argument holes filled."""
    filled = {HEAD_HOLE: head}
    filled.update({f"arg{index}": value for index, value in enumerate(arguments, start=1)})

    def substitute(part: Atom) -> Atom:
        if isinstance(part, Variable):
            return filled.get(part.name, part)
        return part

    return _map_atoms(atom, substitute)


def _row(kind: str) -> Any:
    """One registered rule kind, or a refusal listing the ones there are."""
    table = _seam.typing.table()
    found = table.get(kind)
    if found is None:
        registered = ", ".join(sorted(table)) or "nothing"
        msg = (
            f"no typing rule kind named {kind!r}; registered: {registered}. A "
            f"library registers one with "
            f"metta.seam.typing.register(<kind>, equations=..., doc=...)"
        )
        raise MettaError(msg)
    return found


def rules(m: SpaceLike) -> tuple[Expression, ...]:
    """Every `(typing <space> <head> <kind> <arg>...)` row a space carries.

        for row in metta.typing.rules(m):
            print(row.args[0], row.args[1])

    Ordinary catalog data, so a program writes one itself and reads back what
    a library declared, which is the whole point of the row being a row.
    """
    space = m.self
    catalog = _seam.at("catalog").call()(space)
    # A sequence variable, because a rule takes any number of arguments and
    # most take none: `(typing $space $head $kind $rest)` would miss every one
    # of those.
    return tuple(
        catalog.match(
            _expr(S[ROW_HEAD], S[str(space.name)], V.head, V.kind, seg(V.rest))
        )
    )


def declare(
    m: SpaceLike, head: str | Atom, kind: str, *arguments: Any
) -> Callable[[], None]:
    """Declare that `head`'s result shape follows `kind`; answer the inverse.

        undo = metta.typing.declare(space, "t+", "broadcast")

    Writes the `(typing <space> <head> <kind> <arg>...)` row and adds the kind's
    equations with their holes filled, both into the space this is given. The
    answer withdraws both, so an installer that fails part way puts back what
    it put in.

    Its longhand is the two writes: `space.add(S.typing(...))` and
    `space.add(<the instantiated equation>)`. What the door buys is the
    instantiation and the refusals: a kind nobody registered, and a row that
    does not fill the template's holes.

    Cost: one catalog write per row plus one per equation the kind carries,
    which for a rule the runtime observes is none.
    """
    space = m.self
    row = _row(kind)
    head_atom = S[head] if isinstance(head, str) else head
    supplied = tuple(_encode(argument) for argument in arguments)
    catalog = _seam.at("catalog").call()(space)
    _declare_kind(catalog)

    equations = []
    for source in row.equations:
        shape = template(source)
        wanted = _holes(shape)
        if wanted != len(supplied):
            given = "".join(f" {argument}" for argument in supplied)
            msg = (
                f"the {kind!r} rule takes {wanted} argument(s) and "
                f"({ROW_HEAD} {space.name} {head_atom} {kind}{given}) "
                f"gives {len(supplied)}"
            )
            raise MettaError(msg)
        equations.append(_instantiate(shape, head_atom, supplied))

    declaration = _expr(
        S[ROW_HEAD], S[str(space.name)], head_atom, S[kind], *supplied
    )
    if declaration in catalog:
        # The row IS the record that this declaration happened, so a second
        # install of the same library adds nothing and withdraws nothing.
        return _nothing
    catalog.add(declaration)
    for equation in equations:
        space.add(equation)

    def undo() -> None:
        """Withdraw the row and every equation this declaration added."""
        for equation in equations:
            space.remove(equation)
        catalog.remove(declaration)

    return undo


def _nothing() -> None:
    """The inverse of a declaration that was already standing."""


def withdraw(m: SpaceLike, head: str | Atom) -> tuple[str, ...]:
    """Retire every typing declaration a head carries; answer the kinds retired.

        metta.typing.withdraw(space, "t+")

    The inverse `declare` answers is the cheap path when the caller still holds
    it; this is the one an UNINSTALL takes, which has only the space and the
    head. Both remove the same two things, because both derive the equations
    from the row and the kind's own templates rather than from a list kept
    somewhere.
    """
    space = m.self
    catalog = _seam.at("catalog").call()(space)
    head_atom = S[head] if isinstance(head, str) else head
    retired: list[str] = []
    named = S[str(space.name)]
    for row in catalog.match(
        _expr(S[ROW_HEAD], named, head_atom, V.kind, seg(V.rest))
    ):
        kind = str(row.kind)
        arguments = tuple(row.rest)
        for source in _row(kind).equations:
            space.remove(_instantiate(template(source), head_atom, arguments))
        catalog.remove(_expr(S[ROW_HEAD], named, head_atom, S[kind], *arguments))
        retired.append(kind)
    return tuple(retired)


def _encode(value: Any) -> Atom:
    """One row argument as the atom it is stored as."""
    from .atoms import _encode as encode  # noqa: PLC0415  -- the atom encoder

    return value if isinstance(value, Atom) else encode(value)


def _declare_kind(catalog: Any) -> None:
    """Declare the row's shape and its space ownership, once per catalog.

    The kind row makes the engine's own declaration checker refuse a malformed
    row at the write, and `(owned-by-space typing)` puts the head in the
    retirement walk every space-owned declaration already leaves through, so
    dropping a space takes its typing rows with it [source:
    engine/spaces/catalog.pl, metta_retire_space_catalog/1].
    """
    for declaration in (
        _expr(S.kind, S[ROW_HEAD], S.symbol, S.symbol, S.symbol, _expr(S.rest, S.term)),
        _expr(S["owned-by-space"], S[ROW_HEAD]),
    ):
        if declaration not in catalog:
            catalog.add(declaration)
