"""Purpose: compare demand-transformed tagged derivations with full closure.

Guarantees:
  - the differential compares values, tags, occurrence ledgers, proofs, and
    rendered derivation trees, including duplicate facts and requests
    [tested: test_demand_preserves_complete_derivation_bags; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - unsupported programs retain the original failure and effect behavior
    [tested: test_demand_preserves_global_cycle_and_round_failures,
    test_demand_retains_custom_operation_effects; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - an atom that reached the evaluator without passing certification is
    refused by name, which an assert said only while asserts were compiled
    [tested: test_an_atom_the_certifier_would_decline_is_refused_by_name;
    commit=60d6ca9089f50521bba869c3b7a87c92fd6a990f]

Private access only selects the unchanged reference evaluator or plants a
fault in the optimized path; every result is produced by public evaluate.
"""

import sys
from collections import Counter

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import S, V, parse
from metta import algebra as carrier
from metta._algebra_demand import _certified_shape, _DemandEvaluator
from metta.algebra import AlgebraEvaluationError, evaluate


def _snapshot(result):
    return [
        (answer.value, answer.tag, answer.tokens, answer.proof, answer.why().render())
        for answer in result.answers
    ]


def _reference(program, goal, monkeypatch, **options):
    with monkeypatch.context() as patch:
        patch.setattr(carrier, "_demand_evaluate", lambda *_args, **_kwargs: None, raising=False)
        return evaluate(program, goal, **options)


def _differential(program, goal, monkeypatch, **options):
    expected = _reference(program, goal, monkeypatch, **options)
    actual = evaluate(program, goal, **options)
    assert _snapshot(actual) == _snapshot(expected)
    return actual


@pytest.mark.parametrize(
    ("source", "goals"),
    [
        (
            [
                "(fact 1 (seed a))",
                "(fact 1 (seed a))",
                "(rule 1 (both $x) (premises (seed $x) (seed $x)))",
            ],
            ["(both a)", "(both $x)", "(both missing)"],
        ),
        (
            [
                "(fact 2 (seed a))",
                "(fact 3 (seed b))",
                "(rule 5 (middle $x) (premises (seed $x)))",
                "(rule 5 (middle $x) (premises (seed $x)))",
                "(rule 7 (pair $x $y) (premises (middle $x) (middle $y)))",
            ],
            ["(pair a b)", "(pair $x $x)", "(pair $x $y)", "(pair $_ $_)"],
        ),
        (
            [
                "(fact 2 (seed a))",
                "(fact 3 (seed a))",
                "(rule 5 (right $x) (premises (seed $x)))",
                "(rule 7 (left $x) (premises (seed $x)))",
                "(rule 11 (join $x) (premises (left $x) (right $x)))",
                "(rule 13 (answer $x) (premises (join $x)))",
                "(rule 17 (answer a) (premises))",
            ],
            ["(answer a)", "(answer $x)", "(join a)", "(seed $x)"],
        ),
        (
            [
                "(fact 2 (edge a a))",
                "(fact 3 (edge a b))",
                "(fact 5 (edge b b))",
                "(rule 7 (same $x $x) (premises (edge $x $x)))",
                "(rule 11 (fixed a $y) (premises (edge $_ $y)))",
            ],
            ["(same a a)", "(same a b)", "(same $x $y)", "(fixed a $z)", "(fixed b b)"],
        ),
        (
            [
                "(fact 2 seed)",
                "(fact 3 (seed))",
                "(rule 5 answer (premises seed))",
                "(rule 7 (answer) (premises (seed)))",
                "(rule 11 (from-empty a) (premises))",
            ],
            ["answer", "(answer)", "(from-empty $x)", "(unknown $x)"],
        ),
        (
            [
                "(fact 2 (value 0))",
                "(fact 3 (value 0.0))",
                "(fact 5 (value -0.0))",
                "(fact 7 (value True))",
                '(fact 11 (value "0"))',
                "(fact 13 (value zero))",
                "(rule 17 (answer $x) (premises (value $x)))",
            ],
            ["(answer 0)", "(answer 0.0)", "(answer -0.0)", "(answer True)", '(answer "0")', "(answer $x)"],
        ),
        (
            [
                "(fact 1 (seed $stored))",
                "(fact 2 (seed a))",
                "(rule 3 (answer $x) (premises (seed $x)))",
            ],
            ["(answer a)", "(answer $x)"],
        ),
        (
            [
                "(fact 1 (seed (nested a)))",
                "(rule 3 (answer $x) (premises (seed $x)))",
            ],
            ["(answer (nested a))", "(answer $x)"],
        ),
        (
            [
                "(fact 1 (seed a))",
                "(rule 3 (answer $unbound) (premises (seed $x)))",
                "(rule 5 (anonymous $_) (premises (seed $x)))",
            ],
            ["(answer a)", "(anonymous $x)"],
        ),
    ],
)
def test_demand_preserves_complete_derivation_bags(metta, monkeypatch, source, goals):
    """Constants and query bindings restrict work without changing proof bags."""
    with metta._new_space() as program:
        for atom in source:
            program.add(parse(atom))
        for goal in goals:
            _differential(program, goal, monkeypatch, algebra="counting")


def _source_ids(program):
    """Map each stored declaration to the source number a proof will name.

    A proof number is the declaration's position in the space's own atom
    enumeration, and that enumeration groups by arity in an order the engine
    does not fix: `(fact tag prop)` and `(rule tag head premises)` are three
    and four wide, so which group is enumerated first varies with what else
    the process has compiled. Reading the same enumeration here pins the
    proof's SHAPE without pinning numbers that mean nothing outside one run.
    """
    return {str(atom): order for order, atom in enumerate(program.atoms())}


def test_demand_preserves_all_four_duplicate_combinations(metta, monkeypatch):
    """Two repeated occurrences in two premises contribute four proof trees."""
    with metta._new_space() as program:
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_rule(1, S.both(V.x), S.seed(V.x), S.seed(V.x))
        ids = _source_ids(program)
        rule = next(number for text, number in ids.items() if text.startswith("(rule "))
        result = _differential(program, S.both(0), monkeypatch, algebra="counting")
    assert [str(answer.tag) for answer in result.answers] == ["4"]
    assert result.answers[0].why().render().count(f"rule {rule}:") == 4
    assert result.plan[-1].optimization == "demand-directed-derivation"
    assert result.plan[-1].applied


@given(
    seeds=st.lists(st.tuples(st.integers(0, 4), st.integers(-2, 3)), max_size=6),
    edges=st.lists(st.tuples(st.integers(0, 4), st.integers(0, 4)), max_size=5),
    fixed=st.integers(0, 5),
)
@settings(max_examples=35, deadline=None)
def test_demand_generated_acyclic_programs_match_full_closure(metta, seeds, edges, fixed):
    """Generated duplicates, absent joins, and aliases exercise the same gate."""
    with metta._new_space() as program, pytest.MonkeyPatch.context() as patch:
        for value, tag in seeds:
            program.add_tagged_fact(tag, S.seed(value))
        for left, right in edges:
            program.add_tagged_fact(1, S.edge(left, right))
        program.add_tagged_rule(2, S.joined(V.x, V.z), S.seed(V.x), S.edge(V.x, V.z))
        program.add_tagged_rule(3, S.answer(V.x, V.y), S.joined(V.x, V.z), S.seed(V.y))
        for goal in (S.answer(fixed, V.y), S.answer(V.x, V.x), S.answer(V.x, V.y)):
            _differential(program, goal, patch, algebra="counting")


@pytest.mark.parametrize("rounds", [0, 1, 2, 4])
def test_demand_preserves_global_cycle_and_round_failures(metta, monkeypatch, rounds):
    """An unrelated productive cycle remains a global fixpoint failure."""
    with metta._new_space() as program:
        program.add_tagged_fact(1, S.wanted(0))
        program.add_tagged_fact(1, S.loop(0))
        program.add_tagged_rule(1, S.loop(V.x), S.loop(V.x))
        for runner in (
            lambda: _reference(program, S.wanted(0), monkeypatch, algebra="counting", max_rounds=rounds),
            lambda: evaluate(program, S.wanted(0), algebra="counting", max_rounds=rounds),
        ):
            with pytest.raises(AlgebraEvaluationError, match=f"rounds={rounds}"):
                runner()


def test_demand_preserves_the_last_empty_fixpoint_round(metta, monkeypatch):
    """A one-rule derivation needs its second round to certify a fixpoint."""
    with metta._new_space() as program:
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_rule(1, S.answer(V.x), S.seed(V.x))
        with pytest.raises(AlgebraEvaluationError, match="rounds=1"):
            evaluate(program, S.answer(0), algebra="counting", max_rounds=1)
        _differential(program, S.answer(0), monkeypatch, algebra="counting", max_rounds=2)


def test_demand_retains_custom_operation_effects(metta, monkeypatch):
    """Unrelated rules still execute a custom carrier's effectful operation."""
    calls = []

    def extend(left, right):
        calls.append((left, right))
        return left * right

    metta.op(extend, name="demand-effect-extend", effect="writesState")
    with metta._new_space() as program:
        # An algebra row is owned by the space that declares it, so it is
        # declared on the space the derivation runs in rather than on a
        # sibling. The operation it names is a host op and stays engine-wide.
        program.algebra(
            "demand-effect-carrier",
            combine="+",
            extend="demand-effect-extend",
            zero=0,
            one=1,
        )
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_fact(1, S.wanted(0))
        program.add_tagged_rule(2, S.unrelated(V.x), S.seed(V.x))
        expected = _reference(program, S.wanted(0), monkeypatch, algebra="demand-effect-carrier")
        prior_calls = list(calls)
        calls.clear()
        actual = evaluate(program, S.wanted(0), algebra="demand-effect-carrier")
        assert _snapshot(actual) == _snapshot(expected)
        assert calls == prior_calls
        assert len(calls) == 2
        assert not actual.plan[-1].applied


def test_demand_removes_unrequested_cubic_matching_work(metta, monkeypatch):
    """Profile the Python matcher that engine inference counters cannot see."""
    counts = Counter()
    ordinary_match = carrier._match
    mode = "reference"

    def counted_match(pattern, value):
        counts[mode] += 1
        return ordinary_match(pattern, value)

    monkeypatch.setattr(carrier, "_match", counted_match)
    with metta._new_space() as program:
        for value in range(16):
            program.add_tagged_fact(1, S.seed(value))
        program.add_tagged_rule(1, S.pair(V.x, V.y), S.seed(V.x), S.seed(V.y))
        expected = _reference(program, S.pair(0, 0), monkeypatch, algebra="counting")
        mode = "demand"
        actual = evaluate(program, S.pair(0, 0), algebra="counting")
    assert _snapshot(actual) == _snapshot(expected)
    assert counts["reference"] > 4000
    assert counts["demand"] < 10


@pytest.mark.parametrize("mutation", ["drop", "duplicate"])
def test_demand_differential_rejects_lost_and_duplicated_proofs(metta, monkeypatch, mutation):
    """Plant defects in the demanded bag and require the differential to reject them."""
    original = _DemandEvaluator._solve

    def corrupted(self, demand):
        answers = yield from original(self, demand)
        if len(answers) > 1:
            return answers[:1] if mutation == "drop" else answers + answers
        return answers

    with metta._new_space() as program:
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_rule(1, S.both(V.x), S.seed(V.x), S.seed(V.x))
        monkeypatch.setattr(_DemandEvaluator, "_solve", corrupted)
        with pytest.raises(AssertionError):
            _differential(program, S.both(0), monkeypatch, algebra="counting")


def test_demand_keeps_lawless_integer_proof_order(metta, monkeypatch):
    """A lawless carrier retains the same unfused derivation order."""
    with metta._new_space() as program:
        program.algebra("demand-lawless-integers", combine="+", extend="*", zero=0, one=1)
        program.add_tagged_fact(2, S.seed(S.a))
        program.add_tagged_fact(3, S.seed(S.b))
        program.add_tagged_rule(5, S.middle(V.x), S.seed(V.x))
        program.add_tagged_rule(7, S.answer(V.x), S.middle(V.x))
        program.add_tagged_rule(11, S.answer(S.a))
        result = _differential(program, S.answer(V.x), monkeypatch, algebra="demand-lawless-integers")
    assert [str(answer.tag) for answer in result.answers] == ["11", "70", "105"]
    assert not result.plan[0].applied
    assert result.plan[-1].applied


def test_demand_preserves_integer_rendering_failure(metta, monkeypatch):
    """An unrelated product that cannot be rendered must still fail."""
    prior = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        with metta._new_space() as program:
            program.add_tagged_fact(10**400, S.seed(0))
            program.add_tagged_fact(1, S.wanted(0))
            program.add_tagged_rule(10**400, S.unrelated(V.x), S.seed(V.x))
            for runner in (
                lambda: _reference(program, S.wanted(0), monkeypatch, algebra="counting"),
                lambda: evaluate(program, S.wanted(0), algebra="counting"),
            ):
                with pytest.raises(ValueError, match="Exceeds the limit"):
                    runner()
    finally:
        sys.set_int_max_str_digits(prior)


def test_demand_uses_an_explicit_stack_for_deep_rule_graphs(metta, monkeypatch):
    """An eighty-rule chain answers through the same complete proof as closure."""
    with metta._new_space() as program:
        program.add_tagged_fact(1, S["depth-0"](0))
        for level in range(1, 81):
            program.add_tagged_rule(1, S[f"depth-{level}"](V.x), S[f"depth-{level - 1}"](V.x))
        ids = _source_ids(program)
        result = _differential(program, S["depth-80"](0), monkeypatch, algebra="counting", max_rounds=82)
        chain = [
            next(number for text, number in ids.items()
                 if text.startswith(f"(rule 1 (depth-{level} "))
            for level in range(80, 0, -1)
        ]
        chain.append(next(number for text, number in ids.items()
                          if text.startswith("(fact ")))
    assert result.plan[-1].applied
    assert result.answers[0].proof == tuple(chain)


def test_demand_closes_suspended_rules_on_failure(metta, monkeypatch):
    """An interrupted child closes every suspended rule in its parent demands."""
    opened = []
    closed = []
    original = _DemandEvaluator._solve

    def observed(self, demand):
        opened.append(demand)
        try:
            if demand.relation[1] == "seed":
                message = "planted demand interruption"
                raise AlgebraEvaluationError(message)
            return (yield from original(self, demand))
        finally:
            closed.append(demand)

    with metta._new_space() as program:
        program.add_tagged_fact(1, S.seed(0))
        program.add_tagged_rule(1, S.middle(V.x), S.seed(V.x))
        program.add_tagged_rule(1, S.answer(V.x), S.middle(V.x))
        monkeypatch.setattr(_DemandEvaluator, "_solve", observed)
        with pytest.raises(AlgebraEvaluationError, match="planted demand interruption"):
            evaluate(program, S.answer(0), algebra="counting")
    assert len(opened) == 3
    assert Counter(opened) == Counter(closed)


def test_an_atom_the_certifier_would_decline_is_refused_by_name():
    """The readers are total because `_certify` admits only shaped atoms.

    That invariant used to be five bare asserts, which vanish under -O and say
    nothing when they hold. The refusal names the atom instead, and the plant
    is one `_shape` declines: a variable is neither a symbol nor an expression.
    """
    with pytest.raises(AlgebraEvaluationError, match="algebra_demand_uncertified_atom"):
        _certified_shape(V.x)
