"""Purpose: generate atoms and programs from their declared domains.

Guarantees: the public testing contracts survive the package partition
[tested: test_from_pattern_generates_ground_instances_without_losing_aliases; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import functools
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import metta._catalog.types as _projection
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _encode,
)
from metta._errors.errors import Ground, MettaError, Remedy, refusing
from metta._lazy import optional as require_module

#: programs() draws only from heads the ARBITER reduces, so the census it
#: refuses without is upstream PeTTa's own answer set rather than this
#: engine's: the corpus under tests/conformance/petta/ is where that answer
#: lives [source: tests/conformance/petta/MANIFEST.json; commit=3fc5479961fd591b1884af118528c9a64a1afbb7].
_CENSUS_GROUND = Ground(
    "arbiter",
    "upstream PeTTa at the parity pin: tests/conformance/petta/ is the "
    "captured answer set programs() draws its reducing heads from",
)


def _st():
    hypothesis = require_module(
        "hypothesis",
        "metta.testing generates atoms with hypothesis, which is not installed; "
        "install pymetta[test]",
    )
    return hypothesis.strategies


def names():
    """Symbol and variable names MeTTa's tokeniser reads back whole: no
    whitespace, parens or quotes, none of the characters that mean
    something else at the front, and never the boolean spellings (the
    engine holds its booleans as those very atoms, so True and true are
    one term there and a round trip canonicalizes) or the anonymous `_`
    (fresh at every occurrence by contract, so it never shares).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_?<>=+*"),
        min_size=1,
        max_size=12,
    ).filter(
        lambda s: (
            s[0] not in "$&-<>=+*?0123456789" and s not in ("True", "False", "true", "false", "_")
        )
    )


def symbols():
    """Symbol atoms with engine-readable names."""
    return names().map(Symbol)


def variables():
    """Variable atoms with engine-readable names."""
    return names().map(Variable)


def numbers():
    """Numbers the engine's printer round-trips: integers within the
    tagged-integer range, floats without NaN (never compares equal) or
    infinity (prints as a symbol), both printer limits, not carried bugs.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()
    return st.one_of(
        st.integers(min_value=-(2**62), max_value=2**62),
        st.floats(allow_nan=False, allow_infinity=False, width=64),
    )


def library_scalars(library: Any):
    """Generate one registered array library's own scalar values.

    ``library`` is the module or its name. A library registered against the
    `array` point with a ``scalars`` field answers this; one without it is
    refused naming the field, because a strategy nobody declared cannot be
    invented from the module.
    """
    from metta import seam  # noqa: PLC0415  -- the seam, read at call time

    name = library if isinstance(library, str) else getattr(library, "__name__", library)
    for row in seam.array.table().values():
        if row.module == name:
            scalars = row.fields.get("scalars")
            if scalars is None:
                msg = (
                    f"the {name!r} array row declares no scalars field, so it "
                    f"generates no scalar values; register it with "
                    f"scalars=<a callable answering a strategy>"
                )
                raise MettaError(msg)
            return scalars()
    raise MettaError(seam.array.refusal(f"the array library {name!r}"))


def texts():
    """Strings as the engine stores them; NUL is the one exclusion."""
    st = _st()
    return st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters="\x00"),
        max_size=20,
    )


def grounded():
    """Grounded atoms over numbers, booleans and strings."""
    st = _st()
    return st.one_of(
        numbers().map(Grounded),
        st.booleans().map(Grounded),
        texts().map(Grounded),
    )


def atoms(max_leaves: int = 8, *, ground: bool = False):
    """Whole atoms: symbols, variables (unless ground=True), grounded
    values, and expressions recursively over all of them; max_leaves is
    hypothesis's own size knob for the recursion.

        from hypothesis import given
        from metta import testing

        @given(testing.atoms())
        def test_my_translator_round_trips(atom):
            assert decode(encode(atom)) == atom
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()
    leaves = [symbols(), grounded()]
    if not ground:
        leaves.insert(1, variables())
    return st.recursive(
        st.one_of(*leaves),
        lambda inner: st.lists(inner, max_size=4).map(Expression),
        max_leaves=max_leaves,
    )


def expressions(max_leaves: int = 8, *, ground: bool = False):
    """Non-empty expression-rooted atoms, the shape spaces store."""
    st = _st()
    return st.lists(atoms(max_leaves, ground=ground), min_size=1, max_size=4).map(Expression)


def ground_atoms(max_leaves: int = 8):
    """Atoms carrying no variables: what a store holds after matching.
    atoms(ground=True) under the name provider fuzzing reaches for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return atoms(max_leaves, ground=True)


def patterns(max_leaves: int = 8):
    """Expression-rooted atoms guaranteed to carry at least one variable:
    the query side of match, built rather than filtered so hypothesis
    never discards an example.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()

    def weave(parts):
        before, variable, after = parts
        return Expression([*before, variable, *after])

    return st.tuples(
        st.lists(atoms(max_leaves, ground=False), max_size=2),
        variables(),
        st.lists(atoms(max_leaves, ground=False), max_size=2),
    ).map(weave)


def from_pattern(pattern, max_leaves: int = 8):
    """Generate ground instances of ``pattern`` by consistent substitution.

    Repeated named variables share one draw. Each anonymous ``V._`` occurrence
    receives its own draw, matching the engine's non-binding anonymous law.
    """
    st = _st()
    term = _encode(pattern)
    values = ground_atoms(max_leaves)
    holes = tuple(item for item in term.vars if item.name != "_")

    @st.composite
    def instances(draw):
        bindings = {item: draw(values) for item in holes}

        def instantiate(atom):
            if not isinstance(atom, Variable):
                return atom
            # Anonymous holes are independent draws, so they cannot come from
            # the shared mapping.
            if atom.name == "_":
                return draw(values)
            return bindings[atom]

        return term.map(instantiate)

    return instances()


# ------------------------------------------------- programs from a head census

#: The census the fuzz lane draws from, generated by
#: `tests/conformance/petta_capture.py --census` and committed beside the
#: corpus it was read from. A checkout has it; an installed wheel does not, and
#: `programs(census=...)` is the door for that case.
_CENSUS = Path(__file__).resolve().parents[4] / "tests" / "conformance" / "petta" / "HEADS.json"

#: How many equations one program defines. Not a parameter, because it is not a
#: knob a caller turns: one exercises a defined head, two exercise a head
#: calling into another program's answers, and past two the shrunk report stops
#: being readable. ZERO is in the range so shrinking can reach it: `!(+ 1 2)`
#: alone is a program, and a report that carries an equation nothing in it uses
#: is a report a reader has to rule out by hand.
_EQUATIONS = (0, 2)

#: The ground vocabulary a leaf is drawn from, per census kind. Small on
#: purpose: what the fuzz lane is looking for is a disagreement about
#: REDUCTION, and a wide alphabet spends the budget on printing rather than on
#: reducing. `names()` above is the wide one, for the codec and store
#: properties that want it.
_LEAF_SYMBOLS = ("a", "b", "c", "true", "false")
_LEAF_STRINGS = ('"s"', '"t"', '""')

#: A position that ONLY ever held a variable is a binder, so it receives a
#: fresh name; one that held variables among values is a reference, so it
#: receives a name already in scope. `chain`'s second position is the first
#: kind and `+`'s first position is the second
#: [source: tests/conformance/petta/HEADS.json, the `chain`/3 and `+`/2 rows].
_BINDER = "variable"


class _Draft:
    """The mutable part of one drafted program: relations, scope, name counter."""

    __slots__ = ("fresh", "relations", "scope")

    def __init__(self, relations: list[str]) -> None:
        self.relations = relations
        self.scope: list[str] = []
        self.fresh = 0

    def mint(self) -> str:
        """A variable name no other part of this program has used."""
        self.fresh += 1
        return f"$v{self.fresh}"


class _Surface:
    """The drawable part of a census: which calls exist and what each answers.

    Only the (head, arity) pairs the arbiter REDUCED are here. A head it left
    standing, raised on, hung on, answered differently twice, or that reaches
    outside the program is in the census with that verdict and is not drawable,
    which is what keeps a generated program inside the arbiter's surface.
    """

    __slots__ = ("calls", "frames", "heads", "producers")

    def __init__(self, census: dict) -> None:
        self.calls: list[tuple[str, tuple[dict[str, int], ...], str | None]] = []
        self.producers: dict[str, list[int]] = {}
        self.frames: list[tuple[int, int, str]] = []
        for head, entry in sorted(census.get("heads", {}).items()):
            for row in [pair[1] for pair in
                        sorted(entry.get("arities", {}).items(), key=lambda kv: int(kv[0]))]:
                if row.get("verdict") != "reduces":
                    continue
                positions = tuple(row["positions"])
                at = len(self.calls)
                self.calls.append((head, positions, row.get("result")))
                if row.get("result"):
                    self.producers.setdefault(row["result"], []).append(at)
                for index, kinds in enumerate(positions):
                    for one in kinds:
                        if one != _BINDER:
                            self.frames.append((at, index, one))
        self.heads = frozenset(head for head, _, _ in self.calls)


def _kinds(seen: dict[str, int]) -> list[str]:
    """The kinds one census position saw, most written first, ties by name."""
    return sorted(seen, key=lambda name: (-seen[name], name)) or ["any"]


def _leaf(draw, kind: str, draft: _Draft) -> str:
    """One written value of `kind`, using what is in scope where it can."""
    st = _st()
    if kind == "space":
        return "&self"
    if kind == "string":
        return draw(st.sampled_from(_LEAF_STRINGS))
    if kind == "number":
        return str(draw(st.integers(min_value=-9, max_value=9)))
    if kind == "expression":
        if draft.relations and draw(st.booleans()):
            #A pattern over one of this program's own facts, which is what
            #gives `match` a hit instead of a miss. The variables it opens are
            #in scope for everything to the RIGHT of it, which is where a
            #template goes.
            opened = [draft.mint(), draft.mint()]
            draft.scope.extend(opened)
            return f"({draw(st.sampled_from(draft.relations))} {opened[0]} {opened[1]})"
        parts = [_leaf(draw, "symbol", draft) for _ in range(draw(st.integers(0, 2)))]
        return "(" + " ".join(parts) + ")"
    return draw(st.sampled_from(_LEAF_SYMBOLS))


def _argument(draw, seen: dict[str, int], depth: int, draft: _Draft, surface: _Surface) -> str:
    """One argument for a census position, either a value or a nested call.

    The position's own kinds decide both halves. A `variable`-only position is
    a binder and opens a fresh name; a position that saw variables among values
    reaches for one already in scope. A NESTED call has to ANSWER one of the
    kinds the position holds, which is the census reading of what an
    `expression` written there meant: `(/ $x (+ 1 1))` is a division whose
    second argument is a computation that yields a number, and the census says
    that position holds numbers as well as expressions.
    """
    st = _st()
    kinds = _kinds(seen)
    if kinds == [_BINDER]:
        opened = draft.mint()
        draft.scope.append(opened)
        return opened
    if _BINDER in kinds and draft.scope and draw(st.booleans()):
        return draw(st.sampled_from(sorted(draft.scope)))
    # `expression` at a position that ALSO holds values is the corpus writing a
    # COMPUTATION there, not a list: it is `(+ (f $x) 1)`, and a literal
    # `(b c)` in its place is an addition over a list, which the arbiter raises
    # on. So the leaf kinds are the position's non-expression kinds, and
    # `expression` survives only where it is all the position ever held, which
    # is `collapse` and `msort` and the rest of the list heads.
    #
    # Two other readings were run against this one over 120 programs at seed 0,
    # four rounds each, counted by the wasted runs (the arbiter raising, where
    # there is no oracle) and by the DISTINCT divergences found, which is what
    # the lane is for [measured 2026-09-07;
    # command=tests/checks/check_upstream_fuzz.py -n 120 --seed 0 --rounds 4;
    # fixture=tests/conformance/petta/HEADS.json; commit=5e53dfba208acc69c1eb8a5f2e8aa90c9864a5ce]:
    #
    #   this split                 93 agree, 10 arbiter errors, 4 divergences
    #   every written kind, evenly  47 agree, 38 arbiter errors, 4 divergences
    #   ... in corpus proportion    66 agree, 43 arbiter errors, 0 divergences
    #
    # The proportional one is the surprise and the reason the numbers are here:
    # weighting by how often the corpus writes each kind sounds like the
    # faithful choice and finds NOTHING, because an `expression` position drawn
    # in proportion still admits a call answering any kind at all, and those
    # programs land in the arbiter's error path rather than in its answers.
    values = [one for one in kinds if one not in (_BINDER, "any", "expression")]
    values = values or ["expression"]
    reachable = [one for one in values if one in surface.producers]
    if depth > 0 and reachable and draw(st.booleans()):
        wanted = draw(st.sampled_from(reachable))
        return _call(draw, draw(st.sampled_from(surface.producers[wanted])), depth, draft, surface)
    return _leaf(draw, draw(st.sampled_from(values)), draft)


def _call(draw, at: int, depth: int, draft: _Draft, surface: _Surface) -> str:
    """One written call of the surface's `at`-th (head, arity) pair."""
    head, positions, _ = surface.calls[at]
    written = [_argument(draw, seen, depth - 1, draft, surface) for seen in positions]
    return f"({head}{''.join(' ' + one for one in written)})"


def programs(*, census=None, depth: int = 3, facts=(1, 4), queries=(1, 3)):
    """Generate MeTTa program text over the heads an arbiter is known to reduce.

    The strategy for differential testing against another engine. Every head it
    writes comes from a CENSUS: the call heads of a corpus that engine ships,
    each one run on that engine and recorded with what it did, so a generated
    program is inside the surface being compared rather than exercising the two
    implementations' error paths. The shipped census is upstream PeTTa's, taken
    from `tests/conformance/petta/examples` and written by
    `tests/conformance/petta_capture.py --census`.

        from hypothesis import given
        from metta import testing

        @given(testing.programs())
        def test_both_engines_agree(source):
            assert run_here(source) == run_there(source)

    A program is one to four facts over fresh relation names, up to two
    equations over `$x`, and one to three `!` queries. Every equation body uses
    `$x`, which is the known weakness of generating well-typed terms freely:
    the generator that draws bodies at random writes functions ignoring their
    argument, and the comparison then says nothing about how the argument was
    reduced [source: Pałka, Claessen, Russo and Hughes, "Testing an optimising
    compiler by generating random lambda terms", AST 2011].

    `depth` bounds how deeply a call nests inside another. `facts` and
    `queries` are inclusive ranges. `census` takes a census dict for another
    arbiter; the default reads the one committed in this checkout and refuses
    with the command that writes it when there is none, which is the case in an
    installed wheel.
    """
    st = _st()
    surface = _Surface(_census_data(census))
    if not surface.calls:
        msg = (
            "programs() draws from the heads a census records the arbiter as REDUCING, "
            "and this census records none. Write one with\n"
            "  python tests/conformance/petta_capture.py --upstream <checkout> --census"
        )
        raise refusing(
            ValueError(msg),
            ground=_CENSUS_GROUND,
            remedy=Remedy(
                "capture a census from an upstream PeTTa checkout",
                "source",
                "prose",
                python=(
                    "python tests/conformance/petta_capture.py "
                    "--upstream <checkout> --census"
                ),
            ),
        )

    @st.composite
    def draft(draw) -> str:
        relations: list[str] = []
        lines: list[str] = []
        for index in range(draw(st.integers(*facts))):
            relations.append(f"rel{index}")
            ground = _Draft([])
            lines.append(f"(rel{index} {_leaf(draw, 'symbol', ground)} "
                         f"{_leaf(draw, 'symbol', ground)})")
        written = _Draft(relations)
        defined: list[tuple[str, str]] = []
        for index in range(draw(st.integers(*_EQUATIONS))):
            at, position, parameter = draw(st.sampled_from(surface.frames))
            head, positions, _ = surface.calls[at]
            written.scope = ["$x"]
            arguments = [
                "$x" if where == position
                else _argument(draw, seen, depth - 1, written, surface)
                for where, seen in enumerate(positions)
            ]
            defined.append((f"f{index}", parameter))
            lines.append(f"(= (f{index} $x) ({head}{''.join(' ' + one for one in arguments)}))")
        for _ in range(draw(st.integers(*queries))):
            written.scope = []
            if defined and draw(st.booleans()):
                name, parameter = draw(st.sampled_from(defined))
                lines.append(f"!({name} {_leaf(draw, parameter, written)})")
            else:
                lines.append("!" + _call(draw, draw(st.integers(0, len(surface.calls) - 1)),
                                         depth, written, surface))
        return "\n".join(lines) + "\n"

    return draft()


def _census_data(census: dict | None) -> dict:
    """The census to draw from: the one given, or this checkout's own."""
    if census is not None:
        return census
    if _CENSUS.is_file():
        return json.loads(_CENSUS.read_text(encoding="utf-8"))
    msg = (
        f"programs() draws from a head census and there is none at {_CENSUS}. "
        f"In a checkout, write one with\n"
        f"  python tests/conformance/petta_capture.py --upstream <checkout> --census\n"
        f"and elsewhere pass one: programs(census=json.loads(...))."
    )
    raise FileNotFoundError(msg)

# ------------------------------------------------------- contracts as tests
#
# deal.cases's shape over MeTTa's contracts: the declarations a head already
# carries ARE its property test. The arrow and the refinements say what may
# come in, the return refinement and the effect class say what must come out,
# and Hypothesis writes the sweep, shrinks the failure and prints it.


def _type_strategies() -> dict[str, Callable[[], Any]]:
    """The atom types a signature may name, and the strategy each draws from.

    The STRATEGY column of the one type table, resolved against this module.
    It was a dict here, keyed by the same type names the table already spells
    for four other targets, and it went stale the way any second copy does: a
    type that gains a strategy gains it in the table now, beside its Python,
    JSON, GraphQL and Arrow spellings.
    """
    module = sys.modules[__name__]
    found: dict[str, Callable[[], Any]] = {}
    for name, factory in _projection.STRATEGIES.items():
        drawn = getattr(module, factory, None)
        if drawn is None:
            msg = (
                f"the type table names {factory!r} as the strategy for "
                f"{name}, and metta.testing publishes no such factory"
            )
            raise AttributeError(msg)
        if not callable(drawn):
            msg = (
                f"the type table names {factory!r} as the strategy for "
                f"{name}, and metta.testing's {factory} is not callable"
            )
            raise TypeError(msg)
        found[name] = drawn
    return found


_TYPE_STRATEGIES: dict[str, Callable[[], Any]] = _type_strategies()


@functools.cache
def _register_atom_strategies() -> None:
    """Teach from_type the atom classes once, so ``x: Symbol`` resolves.

    Hypothesis's registry is process-wide and this is the library's own
    reading of its own classes, so registering them is what any user of
    ``from_type`` over an atom-typed signature would otherwise do by hand.
    """
    st = _st()
    st.register_type_strategy(Atom, atoms())
    st.register_type_strategy(Symbol, symbols())
    st.register_type_strategy(Variable, variables())
    st.register_type_strategy(Expression, expressions())
    st.register_type_strategy(Grounded, grounded())
