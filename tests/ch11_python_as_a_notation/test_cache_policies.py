"""Purpose: pin the cache-policy vocabulary and the (cache Name Policy) row as reached from Python.

The generated members, the policy `TabledMap.stats()` reports, a tripped
restraint as `RestraintError`, and every refusal crossing as its own sentence
rather than a downgrade.
Assumes: lib_tabling is imported into the space under test; nothing here
  declares a table by hand, and no Python verb exists for a policy, which is
  the memoisation ruling (test_memoization.py, `_memoized`).
Guarantees:
  - the vocabulary is generated: every word the engine's row names is a
    CachePolicy member that crosses as its symbol
  [tested: test_the_cache_policy_vocabulary_is_generated; commit=eb6b4de8ea70a6b2fe8312a1a23d0593fa764d54]
  - a monotonic row propagates an add-atom at delta cost: the consequence is
    in the table before the next call, no invalidation, and that call costs
    less than the incremental twin's re-evaluation, in inferences
  [tested: test_a_monotonic_table_propagates_an_add_at_delta_cost; commit=eb6b4de8ea70a6b2fe8312a1a23d0593fa764d54]
  - a lattice row answers the minimum over a cycle where plain evaluation
    spends its whole inference budget
  [tested: test_a_lattice_table_answers_the_minimum_where_plain_evaluation_loops;
   commit=eb6b4de8ea70a6b2fe8312a1a23d0593fa764d54]
  - a tripped restraint raises RestraintError under ResourceLimitError with
    the word, the bound and the call
  [tested: test_a_tripped_restraint_reaches_python_as_a_restraint_error;
   commit=eb6b4de8ea70a6b2fe8312a1a23d0593fa764d54]
  - every refusal names its remedy and leaves no row standing
  [tested: test_the_refusals_name_their_remedy; commit=eb6b4de8ea70a6b2fe8312a1a23d0593fa764d54]
Fails when: a counter is read after a LAZY call; a private lattice table
  belongs to the engine that fills it, so a lazy answer cursor computes its
  own copy and the counters read here would not see it. Every assertion below
  evaluates eagerly.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from metta import MeTTa, S
from metta.errors import EngineError, InferenceLimitError, ResourceLimitError, RestraintError
from metta.structures import TabledMap
from metta.vocabularies import CachePolicy


def _tabling_space(name: str):
    m = MeTTa().space(name)
    m.run("!(import! &self (library lib_tabling))")
    return m


def _reach(m, head: str, space: str) -> None:
    m.run(f"(= ({head} $x $y) (match {space} (link $x $y) $y))")
    m.run(f"(= ({head} $x $z) (let $y ({head} $x $y) (match {space} (link $y $z) $z)))")


def test_the_cache_policy_vocabulary_is_generated():
    """One row in &metta, one StrEnum, the same words in the same order."""
    m = MeTTa().self
    holes = " ".join(f"$w{index}" for index in range(len(CachePolicy)))
    (row,) = m.run(f"!(match &metta (vocabulary cache-policy {holes}) ({holes}))")[0]
    assert [str(word) for word in row.children] == [member.value for member in CachePolicy]
    assert CachePolicy.max_answers.value == "max-answers"
    assert str(CachePolicy.monotonic.__metta__()) == "monotonic"
    # force and refuse keep their meaning as lib_memo's words, in the same
    # vocabulary, and stand alone by claim.
    assert list(CachePolicy)[:2] == [CachePolicy.force, CachePolicy.refuse]
    rows = m.run("!(collapse (match &metta (claim cache-policy $w alone) $w))")
    assert sorted(str(word) for word in rows[0][0].children) == ["force", "refuse"]


def test_a_monotonic_table_propagates_an_add_at_delta_cost():
    """The class change: a write costs its consequences, not a rebuild.

    Two twins over a chain of links: `mono` under `(cache mono monotonic)`,
    `incr` under a bare `tabled`, the incremental default. After a write the
    monotonic table already holds the new answer with no invalidation, and a
    point read of it is flat in the chain length where the incremental twin
    re-evaluates its body. Measured 2026-09-07 over chains of 50, 100, 200
    and 400 links: the monotonic read after a write reads 863, 871, 871, 871
    inferences, the incremental one 1969, 3025, 5137, 9345, about 21 a link,
    with the writes themselves at 819-932 and 763-809. So per write the cost
    moves from O(N) to O(1); the assertion below reads that at 60 links as a
    ratio and a second write that leaves the monotonic read where it was.
    """
    m = _tabling_space("&p14-policy-mono")
    m.run("!(bind! &mono-links (new-space))")
    m.run("!(bind! &incr-links (new-space))")
    chain = 60
    for space in ("&mono-links", "&incr-links"):
        for index in range(chain):
            m.run(f"!(add-atom {space} (link n{index} n{index + 1}))")
    _reach(m, "p14-mono", "&mono-links")
    _reach(m, "p14-incr", "&incr-links")
    m.run(f"!(add-atom &metta (cache p14-mono {CachePolicy.monotonic}))")
    mono = TabledMap(m, "p14-mono", arity=2)
    incr = TabledMap(m, "p14-incr", arity=2)
    assert mono.stats()["policy"] == S.monotonic(S.shared)
    assert incr.stats()["policy"] == S.incremental(S.shared)

    assert len(m.run("!(collapse (p14-mono n0 $y))")[0][0].children) == chain
    assert len(m.run("!(collapse (p14-incr n0 $y))")[0][0].children) == chain

    def step(tail: int):
        m.run(f"!(add-atom &mono-links (link n{tail} n{tail + 1}))")
        m.run(f"!(add-atom &incr-links (link n{tail} n{tail + 1}))")
        before_mono, before_incr = mono.stats(), incr.stats()
        with m.stats() as mono_read:
            assert m.run("!(once (p14-mono n0 $y))") != [[]]
        with m.stats() as incr_read:
            assert m.run("!(once (p14-incr n0 $y))") != [[]]
        return before_mono, before_incr, mono_read.inferences, incr_read.inferences

    before_mono, before_incr, mono_first, incr_first = step(chain)
    # The consequence is in the monotonic table before anyone reads, and
    # nothing was invalidated; the incremental twin waits invalidated.
    assert before_mono["answers"] == chain + 1
    assert before_mono["invalidated"] == 0
    assert before_incr["answers"] == chain
    assert before_incr["invalidated"] == 1
    assert mono.stats()["reevaluated"] == 0
    assert incr.stats()["reevaluated"] == 1
    assert mono_first * 2 < incr_first, (
        f"a point read after a write costs {mono_first} inferences monotonic "
        f"against {incr_first} incremental over {chain} links"
    )
    _, _, mono_second, incr_second = step(chain + 1)
    assert mono_second == mono_first, (mono_first, mono_second)
    assert incr_second > mono_second * 2
    assert len(m.run("!(collapse (p14-mono n0 $y))")[0][0].children) == chain + 2


def test_a_lattice_table_answers_the_minimum_where_plain_evaluation_loops():
    """Shortest paths over a cycle: the fixpoint the bag semantics cannot reach."""
    m = _tabling_space("&p14-policy-lattice")
    for edge in ("(edge a b 1)", "(edge b c 1)", "(edge c a 1)", "(edge a c 5)"):
        m.run(f"!(add-atom &self {edge})")
    m.run("(= (p14-shortest $p $q) (if (< $p $q) $p $q))")
    m.run("(= (p14-cost $x $y) (match &self (edge $x $y $c) $c))")
    m.run(
        "(= (p14-cost $x $z) (let $c1 (p14-cost $x $y)"
        " (match &self (edge $y $z $c2) (+ $c1 $c2))))"
    )
    with pytest.raises(InferenceLimitError):
        m.run("!(p14-cost a c)", inferences=200_000)

    m.run("!(add-atom &metta (cache p14-cost (plain (lattice p14-shortest))))")
    cost = TabledMap(m, "p14-cost", arity=2)
    assert cost.stats()["policy"] == S.plain(S.private, S.lattice(S["p14-shortest"]))
    with m.stats() as lattice:
        assert m.run("!(p14-cost a c)") == [[2]]
    assert lattice.inferences < 200_000
    assert m.run("!(p14-cost a a)") == [[3]]
    assert cost[(S.a, S.b)] == 1
    # plain was written, so the table is cleared by hand after a write.
    m.run("!(add-atom &self (edge a c 1))")
    assert cost[(S.a, S.c)] == 2
    cost.clear()
    assert cost[(S.a, S.c)] == 1


def test_a_tripped_restraint_reaches_python_as_a_restraint_error():
    """max-answers through the answer's delay, subgoal-abstract through the tripwire."""
    m = _tabling_space("&p14-policy-restraint")
    m.run("(= (p14-upto $n) (superpose (1 2 3 4 5 6 7 8 9 10)))")
    m.run("(= (p14-deep $t) $t)")
    m.run(f"!(add-atom &metta (cache p14-upto ({CachePolicy.max_answers} 3)))")
    m.run(f"!(add-atom &metta (cache p14-deep ({CachePolicy.subgoal_abstract} 2)))")

    with pytest.raises(RestraintError) as counted:
        m.run("!(collapse (p14-upto 10))")
    assert isinstance(counted.value, ResourceLimitError)
    assert (counted.value.restraint, counted.value.bound, counted.value.call) == (
        "max-answers", 3, "(p14-upto 10)"
    )
    assert "(max-answers 3)" in str(counted.value)

    assert m.run("!(p14-deep (s 0))") == [[S.s(0)]]
    with pytest.raises(RestraintError) as sized:
        m.run("!(p14-deep (s (s (s (s 0)))))")
    assert (sized.value.restraint, sized.value.bound) == ("subgoal-abstract", 2)


def test_the_refusals_name_their_remedy():
    """A policy the engine cannot honour is refused, never downgraded."""
    m = _tabling_space("&p14-policy-refusals")
    m.run("(= (p14-noisy $k) (let $i (println! $k) $k))")
    m.run("(= (p14-pure $k) (+ $k 1))")
    m.run("(= (p14-shortest2 $p $q) (if (< $p $q) $p $q))")
    m.run("!(add-atom &self (fact 1 one))")
    m.run("(= (p14-r1 $k) (match &self (fact $k $v) $v))")
    m.run("(= (p14-r2 $k) (match &self (fact $k $v) $v))")

    def refused(row: str, *fragments: str) -> None:
        with pytest.raises(EngineError) as raised:
            m.run(f"!(add-atom &metta (cache {row}))")
        message = str(raised.value)
        for fragment in fragments:
            assert fragment in message, message
        name = row.split(maxsplit=1)[0]
        (standing,) = m.run(f"!(collapse (match &metta (cache {name} $p) $p))")[0]
        assert not standing.children, f"the refused row stands: {standing}"

    refused("p14-noisy monotonic", "println!/2", "(cache p14-noisy plain)")
    refused("p14-pure lazy", "(monotonic lazy)")
    refused("p14-pure (incremental monotonic)", "both written")
    refused("p14-pure (shared (lattice p14-shortest2))", "write private")
    refused("p14-pure (incremental subsumptive)", "write plain")
    refused("p14-pure (max-answers -1)", "non-negative integer")
    refused("p14-pure (lattice nosuch)", "not a function of two inputs")
    # The door's own refusals: a word outside the vocabulary and a memo word
    # beside a tabling word never reach the compiler.
    refused("p14-pure bogus", "(some-of cache-policy)")
    refused("p14-pure (force monotonic)", "(some-of cache-policy)")
    # One storage predicate carries one watch.
    m.run("!(tabled (p14-r1 $k))")
    refused("p14-r2 monotonic", "already watches incremental", "(cache p14-r2 incremental)")
    m.run("!(add-atom &metta (cache p14-r2 incremental))")
    assert TabledMap(m, "p14-r2", arity=1).stats()["policy"] == S.incremental(S.shared)
