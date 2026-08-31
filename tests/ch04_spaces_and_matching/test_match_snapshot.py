"""Purpose: `match` finds every row before any output template runs, so a
template that writes to the space cannot change what the match still has to
answer. The language specifies this rather than leaving it open, and the
arbiter pins it with an experiment built to tell an eager snapshot from a lazy
query that happens to be fully consumed.
Guarantees:
  - a conjunctive match answers every row it found, through templates that
    remove the atoms the later conjuncts would have read
    [tested: test_match_snapshots_rows_before_template_effects; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a single pattern gets the same guarantee from the logical update view and
    keeps streaming, so a first answer off a large space does not walk it
    [tested: test_a_single_pattern_snapshot_costs_nothing_extra; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a CONJUNCTION under `once` or `take N` stops at the bound instead of
    walking the join, and stops only where nothing between the row and the
    answer could fail
    [tested: test_a_bounded_conjunctive_match_stops_at_the_bound; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the bounded forms keep match/4's answer-shaped refusal, which the fused
    template-and-result spelling had lost
    [tested: test_a_bounded_match_on_an_unbound_space_answers_the_error; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import TRUE, Expression, S, V


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


# Upstream's own graph-rewriting example, and the place the divergence was
# measured: three links form a loop, the template reverses each link it is
# given, and reversing the first one breaks the cycle for every conjunct that
# has not run yet. The doc states the required behaviour in the same
# paragraph: "match first finds all the matches, and then instantiates the
# output pattern with them, which is evaluated outside match. If remove-atom
# and add-atom would be executed right away for each found matching, the
# condition of circular links would be broken after the first rewrite".
def test_match_snapshots_rows_before_template_effects(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(link A B)\n(link B C)\n(link C A)\n(link C E)")
    (rewrites,) = m.run(
        "!(collapse (match &self (, (link $x $y) (link $y $z) (link $z $x))"
        "                        (let $_ (remove-atom &self (link $x $y))"
        "                                (add-atom &self (link $y $x)))))"
    )
    # Three loop rotations, one True each, because add-atom answers True. One
    # answer is what a lazy match gives.
    assert rewrites[0] == Expression(TRUE, TRUE, TRUE)
    assert sorted(str(atom) for atom in m.atoms()) == [
        "(link A C)",
        "(link B A)",
        "(link C B)",
        "(link C E)",
    ]


# The arbiter's own detector, on one pattern: two rows, each template removing
# the OTHER one. A lazy query would lose the row it had not reached.
def test_a_single_pattern_keeps_the_row_its_sibling_removed(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (item alpha))\n!(add-atom &self (item beta))")
    m.run(
        "(= (visit alpha) (let $_ (remove-atom &self (item beta)) alpha))\n"
        "(= (visit beta) (let $_ (remove-atom &self (item alpha)) beta))"
    )
    (answers,) = m.run("!(collapse (match &self (item $x) (visit $x)))")
    assert answers[0] == Expression(S.alpha, S.beta)
    # Both templates ran, so both items are gone: each removed the other.
    # The two equations are atoms of this space too, so the items are counted
    # rather than the whole space.
    (left,) = m.run("!(collapse (match &self (item $x) $x))")
    assert left[0] == Expression()


def test_a_single_pattern_snapshot_costs_nothing_extra(metta):
    """The snapshot is paid where the semantics needs it and nowhere else.

    A single pattern is one goal over one dynamic predicate, and the logical
    update view already fixes what it sees, so it keeps streaming: taking one
    answer has no workload-sized growth between ten atoms and two thousand.
    The probe pays the session's first-use work, then uses the benchmark
    harness's established minimum-of-three policy and four-inference absolute
    allowance for counter noise.
    """
    def first_answer_cost(size):
        space = metta._new_space()
        try:
            space.add(*[S.bulk(n) for n in range(size)])
            with metta.stats() as spent:
                space.run("!(once (match &self (bulk $n) $n))")
            return spent.inferences
        finally:
            space.drop()

    first_answer_cost(2)  # the session's one-time first-use cost lands here, not in the comparison

    first_answer_cost(10)  # the first run compiles the directive; warm first
    small_samples = [first_answer_cost(10) for _ in range(3)]
    large_samples = [first_answer_cost(2000) for _ in range(3)]
    small, large = min(small_samples), min(large_samples)
    assert large <= small + 4, (
        "taking one answer does not walk the space: "
        f"small={small_samples!r}, large={large_samples!r}"
    )


def _bounded_join_cost(metta, size, source):
    """What one bounded query over a `size`-edge chain self-join costs."""
    space = metta._new_space()
    try:
        space.add(*[S.edge(n, n + 1) for n in range(size)])
        with metta.stats() as spent:
            space.run(source)
        return spent.inferences
    finally:
        space.drop()


def test_a_bounded_conjunctive_match_stops_at_the_bound(metta):
    """The bound the caller wrote reaches the conjunctive snapshot.

    A conjunction finds every row before the first one leaves, which the
    language requires, so before this `(once (match &s (, ...) ...))` walked
    the whole join to answer one row: 1,328 inferences over ten edges against
    6,398 over four hundred [measured 2026-08-21]. The bound now reaches
    match_bounded/5, and the cost stops tracking the join.

    It stops only where nothing between the row and the answer could fail. A
    template that compiles to a call is exactly that case, so the last block
    runs one whose first row fails: a bound pushed there would answer nothing.
    """
    for source in (
        "!(once (match &self (, (edge $x $y) (edge $y $z)) $x))",
        "!(once (match &self (, (edge $x $y) (edge $y $z)) (path $x $z)))",
        "!(take 2 (match &self (, (edge $x $y) (edge $y $z)) (path $x $z)))",
    ):
        _bounded_join_cost(metta, 4, source)  # the session's first-use cost lands here
        small = min(_bounded_join_cost(metta, 10, source) for _ in range(3))
        large = min(_bounded_join_cost(metta, 400, source) for _ in range(3))
        assert large <= small + 4, f"{source} still walks the join: {small} then {large}"

    # Unbounded is untouched: it answers every row, so it pays for every row.
    # Compare the workload-dependent increment rather than a ratio against the
    # fixed runnable boundary.  Minimal-MeTTa result normalization adds the
    # same fixed cost at both sizes; the 390-row increase remains 18,722
    # inferences, against 17,550 before that boundary was implemented
    # [measured: 18722; command=pytest -q -p no:benchmark
    # tests/test_match_snapshot.py::test_a_bounded_conjunctive_match_stops_at_the_bound;
    # fixture=10 and 400 edge chains; commit=b77e3ce5233e5f6032cfc8546ff83ecf4dc3de87].
    unbounded = "!(match &self (, (edge $x $y) (edge $y $z)) (path $x $z))"
    _bounded_join_cost(metta, 4, unbounded)
    assert (
        _bounded_join_cost(metta, 400, unbounded)
        > _bounded_join_cost(metta, 10, unbounded) + 10_000
    )

    space = metta._new_space()
    try:
        space.add(*[S.edge(n, n + 1) for n in range(6)])
        space.run("(= (only-late $n) (if (> $n 2) (late $n) (empty)))")
        # Rows come out in edge order, so the first three rows fail the
        # template and the answer is the fourth row's. A bound pushed past a
        # goal that can fail would have stopped at the first row and answered
        # nothing.
        (answers,) = space.run(
            "!(once (match &self (, (edge $x $y) (edge $y $z)) (only-late $x)))"
        )
        assert answers == [Expression(S.late, 3)]
        (bounded,) = space.run(
            "!(take 2 (match &self (, (edge $x $y) (edge $y $z)) (only-late $x)))"
        )
        assert bounded == [Expression(S.late, 3), Expression(S.late, 4)]
    finally:
        space.drop()


@pytest.mark.parametrize(
    "form",
    [
        "(match $u (f 1) matched)",
        "(once (match $u (f 1) matched))",
        "(take 1 (match $u (f 1) matched))",
        "(match notaspace (f 1) matched)",
        "(once (match notaspace (f 1) matched))",
        "(take 1 (match notaspace (f 1) matched))",
    ],
)
def test_a_bounded_match_on_an_unbound_space_answers_the_error(metta, form):
    """A bound does not cost the refusal its shape.

    match/4 answers an Error ATOM through its result, so a compiled form that
    had already bound the result to the template left the refusal nothing to
    unify with and the query answered zero rows instead. `(take 1 ...)` did
    exactly that [measured 2026-08-21], and `once` now compiles through the
    same door, so both are pinned here beside the plain form they must agree
    with.
    """
    (answers,) = metta.run(f"!{form}")
    assert len(answers) == 1
    assert str(answers[0]).startswith("(Error (match ")
    assert "match expects a space as the first argument" in str(answers[0])


def test_a_conjunction_carries_each_rows_annotation(metta):
    """The rows are collected through a findall, and an answer's annotation
    rides a backtrackable global that a findall undoes. Reading it per row is
    what proves the snapshot did not drop the channel on the floor.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    space = metta._new_space()
    try:
        space.add(S.edge(S.a, S.b), S.edge(S.b, S.c))
        (paired,) = space.run(
            "!(collapse (let $p (match &self (, (edge $x $y) (edge $y $z)) (path $x $z))"
            "            (pair $p (annotation))))"
        )
        # Unannotated atoms read the semiring's 1, once per row.
        assert paired[0] == Expression(Expression(S.pair, Expression(S.path, S.a, S.c), 1))
    finally:
        space.drop()


def test_a_conjunction_over_a_python_provider_snapshots_too(metta):
    """The law is the space's, not the store's, so a provider-backed
    conjunction gets the same guarantee through the same door.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta.foreign import SpaceProvider

    class ListSpace(SpaceProvider):
        def __init__(self, atoms):
            self.stored = list(atoms)

        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(list(self.stored))

        def atoms(self):
            return iter(list(self.stored))

        def add(self, atom):
            self.stored.append(atom)

        def remove(self, atom):
            for index, held in enumerate(self.stored):
                if held == atom:
                    del self.stored[index]
                    return True
            return False

    provider = ListSpace([S.step(S.a, S.b), S.step(S.b, S.c), S.step(S.c, S.a)])
    name = f"&snapshot{id(provider) % 100000}"
    metta._register_space(provider, name)
    try:
        (rows,) = metta.run(
            f"!(collapse (match {name} (, (step $x $y) (step $y $z))"
            f"                        (let $_ (remove-atom {name} (step $x $y)) ($x $z))))"
        )
        # Three rows found before the first removal, so three answers; a lazy
        # conjunction loses the rows whose first step the template just took.
        assert len(rows[0]) == 3
        assert provider.stored == []
    finally:
        metta._unregister_space(name)


def test_the_snapshot_does_not_hide_a_write_from_the_next_match(m):
    """It is a snapshot of ONE match, not a transaction: the writes a
    template makes are visible to everything that runs after it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("!(add-atom &self (seen 1))\n!(add-atom &self (seen 2))")
    m.run("!(collapse (match &self (, (seen $a) (seen $b)) (add-atom &self (pair $a $b))))")
    (pairs,) = m.run("!(collapse (match &self (pair $a $b) ($a $b)))")
    assert len(pairs[0]) == 4
    assert m.match(S.pair(V.a, V.b))
