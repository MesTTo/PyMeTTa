"""Purpose: prove compiled match statements and scoped stack blocks preserve their Python control laws.
Guarantees:
  - ordered match arms lower into one engine-side case tower with value,
    capture, as-pattern, guard, alternative, and fallback semantics [tested:
    test_match_statement_lowers_to_one_ordered_case_tower; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a compiled ``with space.limits(stack=N)`` block lowers to the sibling
    engine's ``stack-limit`` scoped pragma spelling [tested:
    test_compiled_stack_limit_uses_the_scoped_pragma_contract; commit=e3787593132a7ece2d300397045f7415709847c9]
  - star patterns lower to the engine's segment variables, named and anonymous
    [tested: test_match_star_lowers_to_a_segment_variable; commit=a3dff3abc83b9d82f3652093246e1d693d526cdb]
  - overlapping decorator clauses share one exclusive case equation while
    disjoint heads remain separate equations [tested:
    test_overlapping_clauses_materialize_as_one_case_equation; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

from metta import S


def test_match_statement_lowers_to_one_ordered_case_tower(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    @m.define
    def rps(x, y):
        match (x, y):
            case (S.Paper, S.Rock) | (S.Scissors, S.Paper) | (S.Rock, S.Scissors):
                return S.First
            case (left, right) if left == right:
                return S.Draw
            case _:
                return S.Second

    @m.define
    def retain_tagged(value):
        match value:
            case (S.Tag, payload) as whole if payload == 7:
                return whole
            case _:
                return S.Miss

    @m.define
    def unwrap_side(value):
        match value:
            case (S.Left, payload) | (S.Right, payload):
                return payload
            case _:
                return S.Miss

    assert list(rps(S.Rock, S.Scissors)) == [S.First]
    assert list(rps(S.Paper, S.Paper)) == [S.Draw]
    assert list(rps(S.Rock, S.Paper)) == [S.Second]
    assert list(retain_tagged(S.Tag(7))) == [S.Tag(7)]
    assert list(retain_tagged(S.Tag(8))) == [S.Miss]
    assert list(unwrap_side(S.Left(11))) == [11]
    assert list(unwrap_side(S.Right(12))) == [12]
    assert rps.source().count("(= ") == 1
    assert "(case $match-subject" in str(rps.body)


def test_compiled_stack_limit_uses_the_scoped_pragma_contract(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    @m.define
    def bounded_increment(value: int) -> int:
        with m.limits(stack=4_000_000):
            return value + 1

    assert str(bounded_increment.body) == ("(with-pragma! ((stack-limit 4000000)) (+ $value 1))")


def test_match_star_lowers_to_a_segment_variable(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    # A NAMED star is the engine's named segment and an unnamed one is its
    # anonymous gap, which is what Python's own `*_` already means.
    @m.define
    def head_of(items):
        match items:
            case (head, *tail):
                return S.Split(head, tail)
            case (*_,):
                return S.Empty

    assert "(:seg $tail)" in str(head_of.body)
    assert "..." in str(head_of.body)


def test_overlapping_clauses_materialize_as_one_case_equation(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    @m.define(name="ordered-clause")
    def zero(value=0):  # noqa: ARG001 -- the default is the clause-head pattern compiled by this test
        return S.Zero

    @m.define(name="ordered-clause")
    def otherwise(value):
        return value

    ordered = [atom for atom in m if str(atom).startswith("(= (ordered-clause ")]
    assert len(ordered) == 1
    assert "(case " in str(ordered[0])
    assert m.run("!(ordered-clause 0) !(ordered-clause 9)") == [[S.Zero], [9]]

    @m.define(name="disjoint-clause")
    def lower_left(x=0, y=0):  # noqa: ARG001 -- both defaults are clause-head patterns compiled by this test
        return S.LowerLeft

    @m.define(name="disjoint-clause")
    def upper_right(x=1, y=1):  # noqa: ARG001 -- both defaults are clause-head patterns compiled by this test
        return S.UpperRight

    disjoint = [atom for atom in m if str(atom).startswith("(= (disjoint-clause ")]
    assert len(disjoint) == 2
