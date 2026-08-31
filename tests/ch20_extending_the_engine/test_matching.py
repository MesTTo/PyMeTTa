"""Purpose: custom matching as a property of grounded atoms. Any object
whose class defines match_ owns its matching logic inside (unify ...) with
no registration, answering bindings for the operand it met, exactly
Hyperon's CustomMatch; a space operand routes through the engine's own
match. The ground cases mirror the arbiter's measured answers
[source: LeaTTa tests/semantics/matching/grounded_value_matching.metta,
unify_branch_evaluation.metta, measured 2026-08-11].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import (
    Answer,
    Bindings,
    Expression,
    S,
    V,
)
from metta.atoms import Grounded
from metta.errors import EngineError
from metta.foreign import CustomMatch


@pytest.fixture
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


def test_unify_ground_cases_match_the_arbiter(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The five measured decisions, including numeric promotion: 1 matches 1.0.
    assert m.run("!(unify 1 1 same different)") == [[S.same]]
    assert m.run("!(unify 1 2 same different)") == [[S.different]]
    assert m.run("!(unify 1 1.0 same different)") == [[S.same]]
    assert m.run('!(unify "x" "x" same different)') == [[S.same]]
    assert m.run('!(unify "x" "y" same different)') == [[S.different]]


def test_unify_binds_variables_both_ways(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.run("!(unify (f $x b) (f a $y) (pair $x $y) nope)") == [
        [Expression(S.pair, S.a, S.b)]
    ]


def test_unify_runs_only_the_selected_branch(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Branch non-evaluation, proven by markers as the arbiter proves it.
    m.run("(= (then-probe) (chain (add-atom (context-space) then-ran) $_ 3))")
    m.run("(= (else-probe) (chain (add-atom (context-space) else-ran) $_ 4))")
    assert m.run("!(unify A A (then-probe) (else-probe))") == [[3]]
    assert m.run("!(match (context-space) else-ran hit)") == [[]]
    assert m.run("!(unify A B (then-probe) (else-probe))") == [[4]]
    assert m.run("!(match (context-space) then-ran hit)") == [[S.hit]]


def test_unify_binds_a_cyclic_pair_raw(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Bindings are raw under the petta alignment: the pair unifies as a
    # rational tree and the then-branch runs, the engine's one binding law
    # (the LeaTTa-era occurs check left with that arbiter).
    assert m.run("!(unify $x (f $x) cyclic sound)") == [[S.cyclic]]


def test_a_space_operand_is_queried(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Hyperon: a space is a grounded atom whose custom matching is query.
    # &self is the reserved token for the space the code lives in, so the
    # upstream spelling works in a library-hosted named space too, and
    # the explicit name stays equivalent.
    m.run("(friend Bob Alice)")
    m.run("(friend Sam Alice)")
    rows = m.run("!(unify &self (friend $who Alice) $who no-friends)")
    assert rows == [[S.Bob, S.Sam]]
    rows = m.run(f"!(unify {m.name} (friend $who Alice) $who no-friends)")
    assert rows == [[S.Bob, S.Sam]]
    (missing,) = m.run("!(unify &self (friend Pol $who) $who no-friends)")
    assert missing == [S["no-friends"]]


def test_self_token_means_this_space_at_every_door(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The reader substitutes &self for the hosting space's name wherever
    # source says it, exactly as it substitutes bind! tokens: runnables,
    # equations and the eval door alike. Stored data expressions keep
    # their literal atoms, the engine's own token boundary.
    m.run("!(add-atom &self (sd here))")
    assert m.run("!(match &self (sd $x) $x)") == [[S.here]]
    m.run("(= (sd-count) (collapse (match &self (sd $y) $y)))")
    (counted,) = m.run("!(sd-count)")[0]
    assert list(counted.children) == [S.here]
    assert m.eval("(match &self (sd $x) $x)") == [S.here]


def test_a_variable_binds_a_space_without_querying_it(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Variables bind before any grounded logic is consulted.
    assert m.run("!(unify $s &self bound queried)") == [[S.bound]]


def test_a_matchable_value_owns_its_matching(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Interval:
        def __init__(self, lo, hi):
            self.lo, self.hi = lo, hi

        def match_(self, other):
            value = other.value if isinstance(other, Grounded) else other
            if isinstance(value, (int, float)) and self.lo <= value <= self.hi:
                yield other

    inside = Grounded(Interval(1, 5))
    assert m.eval(Expression(S.unify, inside, 3, S.inside, S.outside)) == [S.inside]
    assert m.eval(Expression(S.unify, inside, 9, S.inside, S.outside)) == [S.outside]
    # Left and right operands consult the same logic (the arbiter swaps
    # arguments so the grounded side is always handed first).
    assert m.eval(Expression(S.unify, 3, inside, S.inside, S.outside)) == [S.inside]


def test_a_matchable_answers_bindings_for_the_handed_variables(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Solver:
        def match_(self, other):
            var = other.children[1]
            yield Bindings({var: 2})
            yield Bindings({var: -2})

    rows = m.eval(
        Expression(S.unify, Grounded(Solver()), Expression(S.root, V.x), Expression(S.sol, V.x), S.none)
    )
    assert rows == [Expression(S.sol, 2), Expression(S.sol, -2)]


def test_a_matchable_with_no_answers_selects_else(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Nothing:
        def match_(self, other):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(())

    assert m.eval(Expression(S.unify, Grounded(Nothing()), S.a, S.t, S.e)) == [S.e]


def test_a_matchable_error_aborts(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Loud:
        def match_(self, other):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            msg = "my matcher broke"
            raise ValueError(msg)

    with pytest.raises(EngineError):
        m.eval(Expression(S.unify, Grounded(Loud()), S.a, S.t, S.e))


def test_a_matchable_annotation_is_refused_loudly(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A bare value has no context to declare a semiring on; weighted
    # matching belongs to a registered context.
    class Scored:
        def match_(self, other):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            yield Answer({}, k=0.9)

    with pytest.raises(EngineError, match="declares no semiring"):
        m.eval(Expression(S.unify, Grounded(Scored()), S.a, S.t, S.e))


def test_an_object_without_match_is_compared_by_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Plain:
        pass

    one, other = Grounded(Plain()), Grounded(Plain())
    assert m.eval(Expression(S.unify, one, one, S.same, S.different)) == [S.same]
    assert m.eval(Expression(S.unify, one, other, S.same, S.different)) == [S.different]


def test_the_protocol_recognizes_matchables():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class WithHook:
        def match_(self, other):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(())

    class Without:
        pass

    assert isinstance(WithHook(), CustomMatch)
    assert not isinstance(Without(), CustomMatch)


def test_empty_is_the_branch_remover(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The pinned minimal-metta.md rule: a finished Empty result "is not
    # returned among other results", literal or computed alike.
    assert m.run("!(unify a b then Empty)") == [[]]
    assert m.run("!(collapse (superpose (1 Empty 2)))") == [[Expression(1, 2)]]
    m.run("(= (maybe-e 1) Empty)")
    m.run("(= (maybe-e 2) kept)")
    (kept,) = m.run("!(collapse (superpose ((maybe-e 1) (maybe-e 2))))")[0]
    assert list(kept.children) == [S.kept]
