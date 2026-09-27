"""Purpose: (not-provable G) against the least fixpoint over random relations.

The negation engine/duals.pl builds is checked over random finite relations
and recursive definitions on them, against the least fixpoint computed here in
Python and against the empty-collapse reference
`(if (== (collapse G) ()) True False)`, read over G's True answers:
`(let True G True)` in place of G. On a relation that answers True or nothing
the two are one expression; the negated definition answers False wherever
reachability holds, and a False answer is an answer the unfiltered collapse
would count as a proof.

A relation is a random edge set over up to four nodes, stored as space atoms
read through `match` or as equation facts, drawn as a tree or DAG (every edge
from a lower node to a higher one) or with cycles and self-loops. A definition
over it is reachability recursing through the edge's own match-bound node, with
or without the reflexive nonlinear head `(= (r $x $x) True)`, spelled with
`and` or with `(let True ...)`; paths of even and odd length by mutual
recursion; or the negation of reachability, which a query then negates again.
Every definition recurses through the edge first, so the recursive call's
arguments are bound when it runs, the shape the negation decides on a cycle.

Four more definitions decide by the state of a term rather than only by
unification: reachability whose base case is an identity test, `(if (== $x $y)
True ...)`; an edge step kept only between different nodes, through `!=` or
through `(not (== ...))`; and a case that commits to its first row. An open
negation over the first three answers for every value of its variables, since
an identity test on a variable the negation answers for is read both ways; over
the committed case it may refuse, because a row that would bind such a
variable is a decision a later binding could change.

Guarantees:
  - every ground instance answers exactly once, True exactly when the least
    fixpoint excludes it, on cyclic relations included, where the definition's
    own evaluation does not terminate
    [tested 2026-09-26T20:47:28+10:00: test_a_ground_negation_answers_once_and_agrees_with_the_least_fixpoint]
  - wherever the empty-collapse reference returns within its inference budget,
    the negation answers what it answers
    [tested 2026-09-26T20:47:28+10:00: test_a_ground_negation_answers_once_and_agrees_with_the_least_fixpoint]
  - an open instance answers False once per distinct binding a proof makes and
    True for the rest, so each ground value of the open variables is answered
    exactly once and as the ground instance is
    [tested 2026-09-26T20:47:28+10:00: test_an_open_negation_partitions_its_ground_instances]
  - over definitions that decide by a term's state, a ground instance answers
    as the least fixpoint does, and an open one either answers each ground
    value exactly as the ground instance does or refuses, and refuses only
    where a case row would bind a variable it answers for
    [tested 2026-09-26T22:09:43+10:00: test_a_negation_over_decisions_by_state_answers_every_value_or_refuses,
    test_an_identity_test_never_makes_the_negation_refuse]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from metta._errors.errors import EngineError, InferenceLimitError

_COUNTER = itertools.count()

#: The nodes a relation is drawn over, and one it never mentions.
NODES = ("n0", "n1", "n2", "n3")
OUTSIDE = "zz"

#: Enough for every negation here on four nodes; a negation that needs more
#: has not terminated, which the ground property forbids.
BUDGET = 3_000_000
#: The reference is only compared where it returns, and on four nodes one that
#: returns does so in a few thousand inferences; one that loops spends
#: whatever it is given, so it is given little.
REFERENCE_BUDGET = 100_000


@dataclass(frozen=True)
class Program:
    """One relation, one definition over it, and the relation queried."""

    tag: str
    nodes: tuple[str, ...]
    edges: frozenset[tuple[str, str]]
    storage: str
    shape: str
    cyclic: bool
    #: Whether an equation-stored relation also carries (= (e $x $y) (empty)),
    #: the MeTTa spelling of a relation with no further answers. An empty
    #: relation always carries it: with no equation at all, e is undefined and
    #: (e a b) answers itself, a non-True answer the empty-collapse reference
    #: would read as a proof.
    closed: bool

    @property
    def domain(self) -> tuple[str, ...]:
        """The relation's nodes and one node it never mentions."""
        return (*self.nodes, OUTSIDE)

    def name(self, stem: str) -> str:
        """The stem made unique to this program, so no two draws share a head."""
        return f"{stem}{self.tag}"

    def edge(self, x: str, y: str) -> str:
        """The edge test between two terms, as the definitions read it."""
        if self.storage == "space":
            return f"(match &self ({self.name('e')} {x} {y}) True)"
        return f"({self.name('e')} {x} {y})"

    def source(self) -> str:
        """The program: the relation's atoms or facts and the definition over it."""
        e, r, ev, od, u = (self.name(stem) for stem in ("e", "r", "ev", "od", "u"))
        lines: list[str] = []
        if self.storage == "space":
            lines += [f"!(add-atom &self ({e} {a} {b}))" for a, b in sorted(self.edges)]
        else:
            lines += [f"(= ({e} {a} {b}) True)" for a, b in sorted(self.edges)]
            if self.closed or not self.edges:
                lines.append(f"(= ({e} $x $y) (empty))")
            # An unmatched fact call fails rather than answering itself, so
            # every definition answers True or nothing and the empty-collapse
            # reference reads provability directly.
            lines.append(f"!(add-atom &metta (dispatch-policy {e} NoMatchEnum NoMatchFail))")
        step = self.edge("$x", "$z")
        if self.shape == "parity":
            lines += [
                f"(= ({ev} $x $x) True)",
                f"(= ({ev} $x $y) (and {step} ({od} $z $y)))",
                f"(= ({od} $x $y) (and {step} ({ev} $z $y)))",
            ]
            return "\n".join(lines)
        if self.shape in DECIDING_SHAPES:
            lines += DECIDING_SHAPES[self.shape](r, self.edge("$x", "$y"), step)
            return "\n".join(lines)
        if self.shape == "reflexive":
            lines.append(f"(= ({r} $x $x) True)")
        lines.append(f"(= ({r} $x $y) {self.edge('$x', '$y')})")
        if self.shape == "let":
            lines.append(f"(= ({r} $x $y) (let True {step} ({r} $z $y)))")
        else:
            lines.append(f"(= ({r} $x $y) (and {step} ({r} $z $y)))")
        if self.shape == "negated":
            lines.append(f"(= ({u} $x $y) (not-provable ({r} $x $y)))")
        return "\n".join(lines)

    @property
    def queried(self) -> str:
        """The head the properties ask about: ev for parity, u for the negated shape, else r."""
        return self.name({"parity": "ev", "negated": "u"}.get(self.shape, "r"))

    def holds(self, a: str, b: str) -> bool:
        """The least fixpoint: whether (queried a b) has a True answer."""
        if self.shape == "parity":
            return (a, b, 0) in _parity_closure(self.edges, self.domain)
        if self.shape == "identity":
            return a == b or (a, b) in _closure(self.edges)
        if self.shape in ("distinct", "not-same"):
            return (a, b) in _distinct_closure(self.edges)
        if self.shape == "committed":
            return b == NODES[0] or (a, b) in self.edges
        reach = _closure(self.edges)
        if self.shape == "reflexive":
            reach |= {(v, v) for v in self.domain}
        if self.shape == "negated":
            return (a, b) not in reach
        return (a, b) in reach


def _closure(edges: frozenset[tuple[str, str]]) -> set[tuple[str, str]]:
    """Paths of length one or more."""
    reach = set(edges)
    while True:
        added = {(a, d) for a, b in reach for c, d in edges if b == c} - reach
        if not added:
            return reach
        reach |= added


def _parity_closure(edges, domain) -> set[tuple[str, str, int]]:
    """(a, b, p): a path from a to b whose length has parity p."""
    reach = {(v, v, 0) for v in domain}
    while True:
        added = {(a, d, 1 - p) for a, b, p in reach for c, d in edges if b == c} - reach
        if not added:
            return reach
        reach |= added


def _distinct_closure(edges: frozenset[tuple[str, str]]) -> set[tuple[str, str]]:
    """An edge between different nodes, or an edge and then such a path."""
    reach = {(a, b) for a, b in edges if a != b}
    while True:
        added = {(a, d) for a, b in edges for c, d in reach if b == c} - reach
        if not added:
            return reach
        reach |= added


#: The definitions that decide by a term's state, each as the equations of r
#: given its name, the edge test between $x and $y, and the step to $z; an
#: entry ignores the arguments its equations do not read.
DECIDING_SHAPES = {
    "identity": lambda r, _edge, step: [
        f"(= ({r} $x $y) (if (== $x $y) True (and {step} ({r} $z $y))))",
    ],
    "distinct": lambda r, edge, step: [
        f"(= ({r} $x $y) (and (!= $x $y) {edge}))",
        f"(= ({r} $x $y) (and {step} ({r} $z $y)))",
    ],
    "not-same": lambda r, edge, step: [
        f"(= ({r} $x $y) (and {edge} (not (== $x $y))))",
        f"(= ({r} $x $y) (and {step} ({r} $z $y)))",
    ],
    "committed": lambda r, edge, _step: [
        f"(= ({r} $x $y) (case $y (({NODES[0]} True) ($other {edge}))))",
    ],
}


@st.composite
def programs(draw, *, cyclic: bool | None = None,
             shapes=("reach", "reflexive", "let", "parity", "negated")) -> Program:
    """A relation and a definition over it, drawn by construction.

    `cyclic` fixes whether edges may run backwards and loop, drawn when it is
    None, and `shapes` names the definitions drawn from.
    """
    nodes = NODES[: draw(st.integers(2, len(NODES)))]
    looping = draw(st.booleans()) if cyclic is None else cyclic
    pairs = sorted((a, b) for a in nodes for b in nodes if looping or a < b)
    edges = frozenset(draw(st.sets(st.sampled_from(pairs), max_size=len(pairs))))
    return Program(
        tag=f"x{next(_COUNTER)}",
        nodes=nodes,
        edges=edges,
        storage=draw(st.sampled_from(("space", "equations"))),
        shape=draw(st.sampled_from(shapes)),
        cyclic=looping,
        closed=draw(st.booleans()),
    )


def _answers(space, source: str, budget: int = BUDGET) -> list[str]:
    """The one directive's answers, as their printed forms."""
    (group,) = space.run(source, inferences=budget)
    return [str(answer) for answer in group]


def _negation_of(*, holding: bool) -> str:
    """What (not-provable G) answers where G holds or does not."""
    return "False" if holding else "True"


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(program=programs())
def test_a_ground_negation_answers_once_and_agrees_with_the_least_fixpoint(metta, program):
    """Every ground instance answers once, as the least fixpoint says.

    It also answers as the empty-collapse reference does, wherever that
    returns.
    """
    with metta._new_space() as space:
        space.run(program.source())
        event(f"shape={program.shape} cyclic={program.cyclic}")
        for a, b in itertools.product(program.domain, repeat=2):
            call = f"({program.queried} {a} {b})"
            expected = _negation_of(holding=program.holds(a, b))
            answered = _answers(space, f"!(not-provable {call})")
            assert answered == [expected], (program.source(), call, answered)
            try:
                reference = _answers(
                    space,
                    f"!(if (== (collapse (let True {call} True)) ()) True False)",
                    REFERENCE_BUDGET,
                )
            except InferenceLimitError:
                # The definition's own evaluation does not return here, which
                # is the case the negation decides without it.
                event("the reference ran out and the negation answered")
                continue
            assert reference == answered, (program.source(), call, reference)


@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
@given(program=programs(cyclic=False))
def test_an_open_negation_partitions_its_ground_instances(metta, program):
    """An open negation bound afterwards leaves one answer, the ground instance's.

    Its False answers come from the definition's proofs, so the relation is
    drawn without cycles, where those proofs are finite.
    """
    with metta._new_space() as space:
        space.run(program.source())
        rel = program.queried
        for a, b in itertools.product(program.domain, repeat=2):
            expected = [_negation_of(holding=program.holds(a, b))]
            second_open = _answers(
                space, f"!(let $r (not-provable ({rel} {a} $y)) (let $y {b} $r))"
            )
            assert second_open == expected, (program.source(), a, b, second_open)
            both_open = _answers(
                space,
                f"!(let $r (not-provable ({rel} $x $y)) (let ($x $y) ({a} {b}) $r))",
            )
            assert both_open == expected, (program.source(), a, b, both_open)
        for a in program.domain:
            proved = _answers(space, f"!(let False (not-provable ({rel} {a} $y)) $y)")
            assert len(proved) == len(set(proved)), (program.source(), a, proved)
            if program.shape != "negated":
                # One False per node the relation reaches from a, however many
                # proofs reach it; the negated shape proves over a region.
                holding = sorted(b for b in program.domain if program.holds(a, b))
                assert sorted(proved) == holding, (program.source(), a, proved)


def _open_or_refused(space, source: str) -> list[str] | None:
    """The directive's answers, or None where the negation refused it."""
    try:
        return _answers(space, source)
    except EngineError as error:
        assert "not sufficiently instantiated" in str(error), str(error)
        return None


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(program=programs(cyclic=False, shapes=tuple(DECIDING_SHAPES)))
def test_a_negation_over_decisions_by_state_answers_every_value_or_refuses(metta, program):
    """Over decisions by state, each value answers as its ground instance does.

    Ground instances answer as the least fixpoint does. An open one answers
    each ground value as the ground instance does, or refuses, and only the
    committed case, asked with the variable its row would bind still open,
    refuses.
    """
    with metta._new_space() as space:
        space.run(program.source())
        rel = program.queried
        for a, b in itertools.product(program.domain, repeat=2):
            expected = [_negation_of(holding=program.holds(a, b))]
            assert _answers(space, f"!(not-provable ({rel} {a} {b}))") == expected, (
                program.source(), a, b)
            for label, query in (
                ("second", f"!(let $r (not-provable ({rel} {a} $y)) (let $y {b} $r))"),
                ("first", f"!(let $r (not-provable ({rel} $x {b})) (let $x {a} $r))"),
                ("both", f"!(let $r (not-provable ({rel} $x $y)) (let ($x $y) ({a} {b}) $r))"),
            ):
                answered = _open_or_refused(space, query)
                refusable = program.shape == "committed" and label != "first"
                event(f"shape={program.shape} open={label} "
                      f"{'refused' if answered is None else 'answered'}")
                if answered is None:
                    assert refusable, (program.source(), query)
                    continue
                assert answered == expected, (program.source(), query, answered)


@pytest.mark.parametrize("shape", sorted(set(DECIDING_SHAPES) - {"committed"}))
def test_an_identity_test_never_makes_the_negation_refuse(metta, shape):
    """The identity shapes answer every open query over a fixed chain.

    The three definitions that decide only through == and != never refuse
    there, so the property above cannot pass by refusing them.
    """
    program = Program(tag=f"x{next(_COUNTER)}", nodes=NODES[:3],
                      edges=frozenset({("n0", "n1"), ("n1", "n2")}),
                      storage="space", shape=shape, cyclic=False, closed=False)
    with metta._new_space() as space:
        space.run(program.source())
        rel = program.queried
        answered = _answers(space, f"!(collapse (let $r (not-provable ({rel} $x $y)) ($r $x $y)))")
        assert answered, (program.source(), answered)
