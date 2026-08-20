"""Purpose: `match` finds every row before any output template runs, so a
template that writes to the space cannot change what the match still has to
answer. The language specifies this rather than leaving it open, and the
arbiter pins it with an experiment built to tell an eager snapshot from a lazy
query that happens to be fully consumed.
Guarantees:
  - a conjunctive match answers every row it found, through templates that
    remove the atoms the later conjuncts would have read [tested
    test_match_snapshots_rows_before_template_effects]
  - a single pattern gets the same guarantee from the logical update view and
    keeps streaming, so a first answer off a large space does not walk it
    [tested test_a_single_pattern_snapshot_costs_nothing_extra]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, expr


@pytest.fixture()
def m(metta):
    return metta.new_space()


# Upstream's own graph-rewriting example, and the place the divergence was
# measured: three links form a loop, the template reverses each link it is
# given, and reversing the first one breaks the cycle for every conjunct that
# has not run yet. The doc states the required behaviour in the same
# paragraph: "match first finds all the matches, and then instantiates the
# output pattern with them, which is evaluated outside match. If remove-atom
# and add-atom would be executed right away for each found matching, the
# condition of circular links would be broken after the first rewrite".
def test_match_snapshots_rows_before_template_effects(m):
    m.run("(link A B)\n(link B C)\n(link C A)\n(link C E)")
    (rewrites,) = m.run(
        "!(collapse (match &self (, (link $x $y) (link $y $z) (link $z $x))"
        "                        (let () (remove-atom &self (link $x $y))"
        "                                (add-atom &self (link $y $x)))))"
    )
    # Three loop rotations, one unit each. One unit is what a lazy match gives.
    assert rewrites[0] == expr(expr(), expr(), expr())
    assert sorted(str(atom) for atom in m.atoms()) == [
        "(link A C)",
        "(link B A)",
        "(link C B)",
        "(link C E)",
    ]


# The arbiter's own detector, on one pattern: two rows, each template removing
# the OTHER one. A lazy query would lose the row it had not reached.
def test_a_single_pattern_keeps_the_row_its_sibling_removed(m):
    m.run("!(add-atom &self (item alpha))\n!(add-atom &self (item beta))")
    m.run(
        "(= (visit alpha) (let () (remove-atom &self (item beta)) alpha))\n"
        "(= (visit beta) (let () (remove-atom &self (item alpha)) beta))"
    )
    (answers,) = m.run("!(collapse (match &self (item $x) (visit $x)))")
    assert answers[0] == expr(S.alpha, S.beta)
    # Both templates ran, so both items are gone: each removed the other.
    # The two equations are atoms of this space too, so the items are counted
    # rather than the whole space.
    (left,) = m.run("!(collapse (match &self (item $x) $x))")
    assert left[0] == expr()


def test_a_single_pattern_snapshot_costs_nothing_extra(metta):
    """The snapshot is paid where the semantics needs it and nowhere else.

    A single pattern is one goal over one dynamic predicate, and the logical
    update view already fixes what it sees, so it keeps streaming: taking one
    answer costs the same whether the space holds ten atoms or two thousand.
    Measured 2026-08-19 on this box: 683 inferences either way, after a one-time first-use cost of 99 the probe below pays before comparing, first-use index and cache build; without the warm-up the verdict depended on which worker ran this file first, against the
    thousands a collapse over the same two thousand atoms spends.
    """
    def first_answer_cost(size):
        space = metta.new_space()
        try:
            space.add(*[S.bulk(n) for n in range(size)])
            with metta.stats() as spent:
                space.run("!(once (match &self (bulk $n) $n))")
            return spent.inferences
        finally:
            space.drop()

    first_answer_cost(2)  # the session's one-time first-use cost lands here, not in the comparison

    first_answer_cost(10)  # the first run compiles the directive; warm first
    small, large = first_answer_cost(10), first_answer_cost(2000)
    assert small == large, "taking one answer does not walk the space"


def test_a_conjunction_carries_each_rows_annotation(metta):
    """The rows are collected through a findall, and an answer's annotation
    rides a backtrackable global that a findall undoes. Reading it per row is
    what proves the snapshot did not drop the channel on the floor.
    """
    space = metta.new_space()
    try:
        space.add(S.edge(S.a, S.b), S.edge(S.b, S.c))
        (paired,) = space.run(
            "!(collapse (let $p (match &self (, (edge $x $y) (edge $y $z)) (path $x $z))"
            "            (pair $p (annotation))))"
        )
        # Unannotated atoms read the semiring's 1, once per row.
        assert paired[0] == expr(expr(S.pair, expr(S.path, S.a, S.c), 1))
    finally:
        space.drop()


def test_a_conjunction_over_a_python_provider_snapshots_too(metta):
    """The law is the space's, not the store's, so a provider-backed
    conjunction gets the same guarantee through the same door.
    """
    from petta.foreign import SpaceProvider

    class ListSpace(SpaceProvider):
        def __init__(self, atoms):
            self.stored = list(atoms)

        def match(self, pattern):
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
    metta.register_space(provider, name)
    try:
        (rows,) = metta.run(
            f"!(collapse (match {name} (, (step $x $y) (step $y $z))"
            f"                        (let () (remove-atom {name} (step $x $y)) ($x $z))))"
        )
        # Three rows found before the first removal, so three answers; a lazy
        # conjunction loses the rows whose first step the template just took.
        assert len(rows[0]) == 3
        assert provider.stored == []
    finally:
        metta.unregister_space(name)


def test_the_snapshot_does_not_hide_a_write_from_the_next_match(m):
    """It is a snapshot of ONE match, not a transaction: the writes a
    template makes are visible to everything that runs after it.
    """
    m.run("!(add-atom &self (seen 1))\n!(add-atom &self (seen 2))")
    m.run("!(collapse (match &self (, (seen $a) (seen $b)) (add-atom &self (pair $a $b))))")
    (pairs,) = m.run("!(collapse (match &self (pair $a $b) ($a $b)))")
    assert len(pairs[0]) == 4
    assert m.query(S.pair(V.a, V.b))
