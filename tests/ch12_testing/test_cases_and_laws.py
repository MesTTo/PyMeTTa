"""Purpose: a head's declarations and a carrier's law rows are property tests.

Both are written by Hypothesis from what the declaration already states.
Guarantees:
  - cases(head) draws inside the refinements and passes a head that keeps its
    contract, in every shape deal.cases has
    [tested: test_cases_passes_a_head_that_keeps_its_contract,
    test_cases_is_a_decorator_an_iterable_and_a_pytest_test; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - a violated return refinement, a write under a read-only effect class, and
    a MeTTa type with no inhabitants are each reported with the MeTTa call
    form [tested: test_cases_reports_the_call_that_violates_a_return_refinement,
    test_cases_reports_a_write_under_a_read_only_effect,
    test_cases_refuses_a_type_nothing_inhabits_and_takes_a_strategy;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - a MeTTa-typed parameter draws its declared inhabitants and a Predicate
    over a defined head filters through the engine
    [tested: test_cases_draws_a_metta_type_from_its_declared_inhabitants,
    test_cases_filters_a_predicate_over_a_defined_head_through_the_engine;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - every ghostwriter law name is an AlgebraLaw member and a catalog row, the
    boolean semiring passes every generated law, and a wrong carrier fails
    each named law with the counterexample
    [tested: test_every_ghostwriter_law_name_is_a_catalog_row,
    test_the_boolean_semiring_passes_every_generated_law,
    test_a_wrong_carrier_fails_each_generated_law_by_name; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import inspect
import operator
from typing import Annotated

import pytest
from annotated_types import Ge, Gt, MinLen, Predicate
from hypothesis import strategies as st

from metta import G, S, Space, algebra, convert, testing
from metta._atoms.factories import Symbol
from metta.vocabularies import AlgebraLaw

GHOSTWRITER = (
    "associative",
    "commutative",
    "identity",
    "distributes_over",
    "idempotent",
    "roundtrip",
    "equivalent",
)


@pytest.fixture
def m(metta):
    """One fresh anonymous space per test."""
    return metta._new_space()


def test_cases_passes_a_head_that_keeps_its_contract(m):
    """The refinements bound the draw and the head answers inside its return refinement."""

    @m.define
    def double(x: Annotated[int, Gt(0)]) -> Annotated[int, Ge(0)]:
        return x * 2

    generated = testing.cases(double, examples=40)
    assert str(generated.strategy["x"]).startswith("integers()")
    generated()

    @m.define
    def initial(s: Annotated[str, MinLen(1)]) -> Annotated[str, MinLen(1)]:
        return s[0]

    testing.cases(initial, examples=40)()


def test_cases_reports_the_call_that_violates_a_return_refinement(m):
    """The failing example is Hypothesis's shrunk one, printed as the MeTTa call."""

    @m.define
    def shrink(x: Annotated[int, Gt(0)]) -> Annotated[int, Ge(0)]:
        return x - 5

    with pytest.raises(AssertionError) as caught:
        testing.cases(shrink, examples=60, seed=7)()
    message = str(caught.value)
    assert "(shrink 1) answered (Error (shrink 1) (BadReturnValue (Ge 0) -4))" in message


def test_cases_reports_a_write_under_a_read_only_effect(m):
    """An operation that writes while declaring pureStructural is caught on the first call."""

    def sneaky(x):
        m.add(S.seen(x))
        return x

    m.op(sneaky, name="sneaky", effect="pureStructural")

    @m.define
    def uses(x: int) -> int:
        return sneaky(x)

    assert str(uses.effect) == "pureStructural"
    with pytest.raises(AssertionError, match=r"\(uses 0\) wrote into .*declares the effect class pureStructural"):
        testing.cases(uses, examples=5, seed=1)()


def test_cases_draws_a_metta_type_from_its_declared_inhabitants(m):
    """A parameter typed by a MeTTa type draws the atoms the space declares."""
    m.run("(: Colour Type) (: red Colour) (: blue Colour)")

    @m.define
    def paint(c: S.Colour) -> S.Colour:
        return c

    drawn = sorted(str(case.call) for case in testing.cases(paint, examples=20, seed=3))
    assert set(drawn) <= {"(paint red)", "(paint blue)"}
    testing.cases(paint, examples=10)()


def test_cases_refuses_a_type_nothing_inhabits_and_takes_a_strategy(m):
    """An uninhabited type names the strategies= door; the door is honoured."""

    @m.define
    def wear(c: S.Hat) -> S.Hat:
        return c

    with pytest.raises(TypeError, match=r"typed Hat and nothing in .* is declared to inhabit it; pass strategies=\{'c': \.\.\.\}"):
        testing.cases(wear).strategy  # noqa: B018  -- the property builds the strategies, which is the refusal under test
    testing.cases(wear, examples=5, strategies={"c": st.sampled_from([Symbol("fez"), Symbol("cap")])})()
    with pytest.raises(TypeError, match="names no parameter"):
        testing.cases(wear, strategies={"hat": st.just(Symbol("fez"))})


def test_cases_filters_a_predicate_over_a_defined_head_through_the_engine(m):
    """A Predicate naming a defined head is decided by the engine on both sides."""

    @m.define
    def even(x: int) -> bool:
        return x % 2 == 0

    @m.define
    def half(x: Annotated[int, Predicate(even)]) -> int:
        return x // 2

    assert [str(answer) for answer in half(3)] == [
        "(Error (half 3) (BadArgValue 1 (Predicate even) 3))"
    ]
    for case in testing.cases(half, examples=20, seed=2):
        assert case.arguments[0] % 2 == 0
    testing.cases(half, examples=20)()


def test_cases_is_a_decorator_an_iterable_and_a_pytest_test(m):
    """deal.cases's three shapes: a test function, a decorator, an iterable of cases."""

    @m.define
    def double(x: Annotated[int, Gt(0)]) -> int:
        return x * 2

    generated = testing.cases(double, examples=8, seed=5)
    assert inspect.isfunction(generated.__func__)
    assert inspect.signature(generated.__func__).parameters == {}
    ran = []

    @testing.cases(double, examples=8, seed=5)
    def test_double(case):
        ran.append(case.call)
        assert case() == [G(case.arguments[0] * 2)]

    test_double()
    assert ran and all(str(call).startswith("(double ") for call in ran)
    listed = list(generated)
    assert len(listed) == len(ran)
    assert repr(listed[0]).startswith("Case((double ")
    with pytest.raises(TypeError, match=r"takes a head defined with @m\.define"):
        testing.cases(double.py)


def test_every_ghostwriter_law_name_is_a_catalog_row(m):
    """Hypothesis's names are AlgebraLaw members, catalog rows, and accepted declarations."""
    rows = {
        str(child)
        for atom in Space("&metta").atoms()
        if str(atom).startswith("(vocabulary algebra-law ")
        for child in atom.children[2:]
    }
    for name in GHOSTWRITER:
        member = AlgebraLaw[name]
        assert member.value in rows
        assert testing.laws(algebra.bool, m, laws=(name,)).laws
    assert AlgebraLaw.distributes_over.value == "distributes-over"
    assert testing.laws(algebra.bool, m, laws=("identity",)).laws == (
        "combine-zero-identity",
        "extend-one-identity",
    )


def test_the_boolean_semiring_passes_every_generated_law(m):
    """Every law row of bool, and every ghostwriter name asked of it, holds."""
    generated = testing.laws(algebra.bool, m, examples=30)
    assert inspect.isfunction(generated.__func__)
    generated()
    assert generated.notes == ["contraction: a declared capability, not a property"]
    for law, test in testing.laws(algebra.bool, m, laws=GHOSTWRITER, examples=20):
        test()
        assert law in AlgebraLaw


class LossyWeight:
    """A carrier value whose registered codec is deliberately lossy."""

    def __init__(self, n):
        """Hold one weight."""
        self.n = n

    def __eq__(self, other):
        """Weights compare by value, which is what the round trip must preserve."""
        return isinstance(other, LossyWeight) and other.n == self.n

    def __hash__(self):
        """Hash by value, consistent with equality."""
        return hash(self.n)

    def __repr__(self):
        """The weight as the counterexample prints it."""
        return f"LossyWeight({self.n})"


@pytest.mark.parametrize("name", GHOSTWRITER)
def test_a_wrong_carrier_fails_each_generated_law_by_name(m, name):
    """One fixture per family of law, each failing with its counterexample."""
    if name in ("associative", "commutative", "identity", "distributes_over", "idempotent"):
        m.op(operator.sub, name="wrong-plus", effect="pureStructural")
        m.op(operator.add, name="wrong-times", effect="pureStructural")
        algebra.declare(m, "wrong", combine="wrong-plus", extend="wrong-times", zero=0, one=0, type=S.Number)
        subject = "wrong"
    elif name == "equivalent":
        # The engine's `/` answers an integer where operator.truediv answers a float.
        algebra.declare(m, "halves", combine="/", extend="*", zero=1, one=1, carrier=(1, 2, 4))
        subject = "halves"
    else:
        convert.register_type(
            LossyWeight,
            image="expression",
            to_atom=lambda w: (w.n,),
            from_atom=lambda _n: LossyWeight(0),
        )
        m.op(operator.add, name="lossy-plus", effect="pureStructural")
        algebra.declare(
            m, "lossy", combine="lossy-plus", extend="lossy-plus",
            zero=LossyWeight(0), one=LossyWeight(0), carrier=(LossyWeight(0), LossyWeight(1)),
        )
        subject = "lossy"
    try:
        with pytest.raises(AssertionError, match=rf"algebra_law_violation: {subject} law \S+ fails at \(.*\): .* differs from ") as caught:
            testing.laws(subject, m, laws=(name,), examples=60, seed=11)()
        expected_laws = testing.laws(subject, m, laws=(name,)).laws
        assert any(f" law {law} fails" in str(caught.value) for law in expected_laws)
    finally:
        if subject == "lossy":
            convert.unregister_type(LossyWeight)
