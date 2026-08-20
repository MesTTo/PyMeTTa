"""Purpose: the explicit answer form, end to end: a provider or operation
answers bindings for the query's own variables, plain atoms and explicit
answers mix in one stream, and the staged slots (residue, annotation)
refuse loudly instead of dropping silently.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import Answer, Bindings, parse
from petta.atoms import Expr, Gnd, Sym, Var
from petta.errors import EngineError, PettaError, TransportFailure
from petta.foreign import SpaceProvider


def test_answer_wire_form_is_exact():
    wire = Answer({"x": 3}).to_wire()
    assert wire == ["a", [["x", ["n", 3]]], True, None]
    wire = Answer({"$y": Sym("b")}, value=Sym("v"), k=2).to_wire()
    assert wire == ["a", [["y", ["s", "b"]]], True, 2, ["s", "v"]]
    residue = parse("(check $z)")
    wire = Answer({}, residue=residue).to_wire()
    assert wire[:2] == ["a", []]
    assert wire[2] == residue.to_wire()
    # Var keys normalize like string keys.
    assert Bindings({Var("q"): 1}).to_wire() == ["a", [["q", ["n", 1]]], True, None]


def test_answer_validates_eagerly():
    with pytest.raises(TypeError, match="theta key"):
        Answer({3: 1})
    with pytest.raises(TypeError, match="residue is an Atom"):
        Answer({}, residue="not an atom")
    with pytest.raises(TypeError, match="annotation in the declared"):
        Answer({}, k=object())


class _AnswerProvider(SpaceProvider):
    """Answers each query by binding its variables, the okBind shape."""

    def __init__(self, answer_for):
        self.answer_for = answer_for

    def atoms(self):
        return iter(())

    def match(self, pattern, *, limit=None):
        yield from self.answer_for(pattern)


def _pattern_vars(pattern):
    return [child for child in pattern.children if isinstance(child, Var)]


def test_a_provider_answers_bindings(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Bindings({y: Sym("b")})
        yield Bindings({y: Sym("c")})

    metta.register_space(_AnswerProvider(answer), "&ap-bind")
    out = metta.run("!(collapse (match &ap-bind (edge a $y) (got $y)))")
    assert str(out[0][0]) == "((got b) (got c))"


def test_plain_atoms_and_answers_mix_in_one_stream(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield parse("(edge a plain)")
        yield Bindings({y: Sym("bound")})

    metta.register_space(_AnswerProvider(answer), "&ap-mix")
    out = metta.run("!(collapse (match &ap-mix (edge a $y) $y))")
    assert str(out[0][0]) == "(plain bound)"


def test_an_explicit_value_unifies_under_theta(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        # The candidate-with-bindings form: the value is the answer atom,
        # and theta must agree with it.
        yield Answer({y: Sym("b")}, value=parse("(edge a b)"))
        # A value that CONTRADICTS theta is one failed unification: that
        # answer drops, the stream continues.
        yield Answer({y: Sym("clash")}, value=parse("(edge a other)"))
        yield Bindings({y: Sym("after")})

    metta.register_space(_AnswerProvider(answer), "&ap-val")
    out = metta.run("!(collapse (match &ap-val (edge a $y) $y))")
    assert str(out[0][0]) == "(b after)"


def test_theta_aliases_query_variables(metta):
    def answer(pattern):
        x, y = _pattern_vars(pattern)
        yield Bindings({y: x})

    metta.register_space(_AnswerProvider(answer), "&ap-alias")
    out = metta.run("!(collapse (match &ap-alias (edge $x $y) (pair $x $y)))")
    (answers,) = out[0]
    (pair,) = answers.children
    assert isinstance(pair.children[1], Var)
    assert pair.children[1].name == pair.children[2].name


def test_fresh_variables_in_theta_values_stay_open(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Bindings({y: Expr([Sym("f"), Var("fresh")])})

    metta.register_space(_AnswerProvider(answer), "&ap-open")
    out = metta.run("!(collapse (match &ap-open (edge a $y) $y))")
    (answers,) = out[0]
    (value,) = answers.children
    assert str(value.children[0]) == "f"
    assert isinstance(value.children[1], Var)


def test_an_annotation_is_refused_loudly(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: Sym("b")}, k=0.5)

    metta.register_space(_AnswerProvider(answer), "&ap-k")
    with pytest.raises(EngineError, match="annotation"):
        metta.run("!(collapse (match &ap-k (edge a $y) $y))")


def test_an_enumeration_refuses_answers(metta):
    class _Wrong(SpaceProvider):
        def atoms(self):
            yield Bindings({"x": 1})

    metta.register_space(_Wrong(), "&ap-enum")
    # The seam raises its own PettaError, and the boundary re-raises
    # the original object rather than an EngineError transcript.
    with pytest.raises(PettaError, match="enumeration has no query"):
        metta.run("!(collapse (get-atoms &ap-enum))")


def test_a_generator_op_answers_bindings(metta):
    def relate(x):
        yield Bindings({x: 1})
        yield Bindings({x: 2})

    metta.register_op(relate, name="ap-rel", typed=False, pass_atoms=True)
    metta.run("(= (ap-probe $x) (let $r (ap-rel $x) (pair $x $r)))")
    out = metta.run("!(collapse (ap-probe $q))")
    assert str(out[0][0]) == "((pair 1 ()) (pair 2 ()))"


def test_a_det_op_answers_bindings_with_a_value(metta):
    def solve(x):
        return Answer({x: Sym("found")}, value=Sym("done"))

    metta.register_op(solve, name="ap-solve", typed=False, pass_atoms=True)
    metta.run("(= (ap-sprobe $x) (let $r (ap-solve $x) (pair $x $r)))")
    out = metta.run("!(collapse (ap-sprobe $q))")
    assert str(out[0][0]) == "((pair found done))"


def test_a_raw_op_refuses_answers(metta):
    def wrong(x):
        return Answer({"x": x})

    metta.register_op(wrong, name="ap-raw", typed=False, raw=True)
    with pytest.raises(EngineError, match="raw"):
        metta.run("!(ap-raw 1)")


# ------------------------------------------------------------- residue (F2)


def test_a_residue_condition_filters_answers(metta):
    """The residue is the part of the query the provider did not discharge,
    written over the pattern's own variables and closed by the engine: a
    condition reducing to false drops that answer and nothing else.
    """

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        keeps = Expr([Sym(">"), y, Gnd(3)])
        yield Answer({y: 5}, residue=keeps)
        yield Answer({y: 2}, residue=keeps)
        yield Answer({y: 9}, residue=keeps)

    metta.register_space(_AnswerProvider(answer), "&ap-cond")
    out = metta.run("!(collapse (match &ap-cond (edge a $y) $y))")
    assert str(out[0][0]) == "(5 9)"


def test_a_residue_match_form_composes_across_contexts(metta):
    """A residue may itself be a match, so one provider's answer closes
    against another context's atoms, composing bindings by sharing.
    """
    metta.run("!(add-atom &ap-kb (allowed b))")

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        check = parse("(match &ap-kb (allowed $v) ok)")
        (v,) = [c for c in check.children[2].children if isinstance(c, Var)]
        yield Answer({y: Sym("b")}, residue=Expr([check.children[0], check.children[1], Expr([check.children[2].children[0], y]), Sym("ok")]))
        yield Answer({y: Sym("c")}, residue=Expr([check.children[0], check.children[1], Expr([check.children[2].children[0], y]), Sym("ok")]))

    metta.register_space(_AnswerProvider(answer), "&ap-cross")
    out = metta.run("!(collapse (match &ap-cross (edge a $y) $y))")
    assert str(out[0][0]) == "(b)"


def test_a_nonreducing_residue_holds(metta):
    """A residue with no equation answers itself, exactly as !(edge q w)
    does at the top level, so it holds; the language's own rule.
    """

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: Sym("kept")}, residue=parse("(ap-no-equation q w)"))

    metta.register_space(_AnswerProvider(answer), "&ap-hold")
    out = metta.run("!(collapse (match &ap-hold (edge a $y) $y))")
    assert str(out[0][0]) == "(kept)"


def test_a_conditional_answer_under_a_pushed_bound_is_loud(metta):
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: 5}, residue=Expr([Sym(">"), y, Gnd(3)]))

    metta.register_space(_AnswerProvider(answer), "&ap-bound")
    metta.declare_handles("&ap-bound", "(edge a $y)", "Exact")
    with pytest.raises(EngineError, match="Sound"):
        metta.run("!(collapse (take 2 (match &ap-bound (edge a $y) $y)))")
    # Without the bound the same conditional answer is fine.
    out = metta.run("!(collapse (match &ap-bound (edge a $y) $y))")
    assert str(out[0][0]) == "(5)"


def test_an_op_residue_closes_through_the_engine(metta):
    def pick(x):
        return Answer({x: 2}, value=Sym("small"), residue=Expr([Sym("<"), x, Gnd(10)]))

    def pickbig(x):
        return Answer({x: 50}, value=Sym("big"), residue=Expr([Sym("<"), x, Gnd(10)]))

    metta.register_op(pick, name="ap-pick", typed=False, pass_atoms=True)
    metta.register_op(pickbig, name="ap-pickbig", typed=False, pass_atoms=True)
    out = metta.run("!(collapse (ap-pick $x))")
    assert str(out[0][0]) == "(small)"
    # The failing residue makes the call answer nothing, the semidet rule.
    out = metta.run("!(collapse (ap-pickbig $x))")
    assert str(out[0][0]) == "()"


def test_planner_rows_may_be_bindings(metta):
    """SEAM-P-10: a plan row may bind the claimed patterns' variables
    directly instead of re-unifying atom rows, and the two mix.
    """

    class _JoinProvider(SpaceProvider):
        def __init__(self):
            self.planned = []

        def atoms(self):
            return iter([parse("(edge a b)"), parse("(edge b c)")])

        def match(self, pattern, *, limit=None):
            yield from self.atoms()

        def plan(self, patterns):
            self.planned.append(patterns)
            # Positional, because the engine's variable names carry no
            # order: (edge $x $y) then (edge $y $z).
            first, second = patterns
            x, y = first.children[1], first.children[2]
            z = second.children[2]
            return (
                patterns,
                [],
                iter(
                    [
                        Answer({x: Sym("a"), y: Sym("b"), z: Sym("c")}),
                        [parse("(edge b c)"), parse("(edge c d)")],
                    ]
                ),
            )

    provider = _JoinProvider()
    metta.register_space(provider, "&ap-plan")
    out = metta.run(
        "!(collapse (match &ap-plan (, (edge $x $y) (edge $y $z)) (path $x $z)))"
    )
    assert provider.planned
    assert str(out[0][0]) == "((path a c) (path b d))"


# ------------------------------------------------- annotations and top (F3)


def test_top_over_an_annotated_op_answers_the_k_best_in_order(metta):
    lexicon = {"alpha": 0.4, "beta": 0.9, "gamma": 0.1, "delta": 0.7}

    def ap_lex(query, candidate=None):
        # Deliberately NOT best first: the engine's ordering must not
        # depend on the producer being polite. The op answers through the
        # general surface: the candidate is the value and the degree is
        # the answer's annotation, nothing pair-shaped.
        for word, degree in lexicon.items():
            yield Answer(value=word, k=degree)

    metta.register_op(ap_lex, name="ap-lex", typed=False)
    metta.declare_annotations("ap-lex", "ranked")
    out = metta.run('!(collapse (top 2 (ap-lex "q" $c)))')
    assert str(out[0][0]) == '("beta" "delta")'
    # The differential: brute force over every answer paired with its own
    # annotation, sorted by degree, must agree with top's prefix for
    # every k.
    weighted = metta.run(
        '!(collapse (let $w (ap-lex "q" $c) (pair (annotation) $w)))'
    )[0][0].children
    ranked = sorted(weighted, key=lambda pair: -pair.children[1].value)
    for k in (1, 2, 3, 4):
        best = metta.run(f'!(collapse (top {k} (ap-lex "q" $c)))')[0][0].children
        assert [str(a) for a in best] == [str(p.children[2]) for p in ranked[:k]]


def test_top_orders_mixed_integer_and_float_annotations_by_value(metta):
    # SWI compares numbers by value with type only breaking ties, unlike
    # the ISO standard order where every float precedes every integer, so
    # this pin protects top against any engine where that differs.
    def mixed(query, candidate=None):
        yield Answer(value=Sym("intone"), k=1)
        yield Answer(value=Sym("floathigh"), k=2.5)

    metta.register_op(mixed, name="ap-mixed-k", typed=False)
    metta.declare_annotations("ap-mixed-k", "ranked")
    (best,) = metta.run("!(collapse (top 1 (ap-mixed-k q)))")[0]
    assert [str(a) for a in best.children] == ["floathigh"]


def test_top_refuses_an_unordered_context(metta):
    calls = []

    def answer(pattern):
        calls.append(pattern)
        yield parse("(edge a b)")

    metta.register_space(_AnswerProvider(answer), "&ap-topfloor")
    with pytest.raises(EngineError, match="ranked"):
        metta.run("!(collapse (top 2 (match &ap-topfloor (edge $x $y) $y)))")
    assert calls == []


def test_top_pushes_the_bound_under_three_declarations(metta):
    class _Ranked(SpaceProvider):
        def __init__(self):
            self.rows = [("a", 0.5), ("b", 0.9), ("c", 0.7)]
            self.limits = []

        def atoms(self):
            return iter(parse(f"(scored {name})") for name, _ in self.rows)

        def match(self, pattern, *, limit=None):
            self.limits.append(limit)
            ordered = sorted(self.rows, key=lambda row: -row[1])
            if limit is not None:
                ordered = ordered[:limit]
            for name, k in ordered:
                yield Answer(value=parse(f"(scored {name})"), k=k)

    provider = _Ranked()
    metta.register_space(provider, "&ap-vec")
    metta.declare_annotations("&ap-vec", "ranked")
    # Two of the three declarations: the bound stays here.
    metta.declare_handles("&ap-vec", "(scored $x)", "Exact")
    out = metta.run("!(collapse (top 2 (match &ap-vec (scored $x) $x)))")
    assert provider.limits == [None]
    assert str(out[0][0]) == "(b c)"
    # The third lands and the provider is handed the bound.
    metta.declare_emits("&ap-vec", "best-first")
    provider.limits.clear()
    out = metta.run("!(collapse (top 2 (match &ap-vec (scored $x) $x)))")
    assert provider.limits == [2]
    assert str(out[0][0]) == "(b c)"


def test_an_undeclared_annotation_names_the_declaration(metta):
    def scorer(x):
        yield Answer(value=Sym("v"), k=0.5)

    metta.register_op(scorer, name="ap-undeclared", typed=False, pass_atoms=True)
    with pytest.raises(EngineError, match="annotations ap-undeclared ranked"):
        metta.run("!(collapse (ap-undeclared 1))")


def test_declare_annotations_validates_and_replaces(metta):
    with pytest.raises(ValueError, match="ranked"):
        metta.declare_annotations("&ap-v", "sorta")
    metta.declare_annotations("&ap-v", "ranked")
    metta.declare_annotations("&ap-v", "prob")
    rows = metta.space("&petta").query(parse("(annotations &ap-v $s)"))
    assert [str(row.s) for row in rows] == ["prob"]


def test_declare_emits_validates(metta):
    with pytest.raises(ValueError, match="best-first"):
        metta.declare_emits("&ap-v", "fastest")
    metta.declare_emits("&ap-v", "best-first")
    rows = metta.space("&petta").query(parse("(emits &ap-v $p)"))
    assert [str(row.p) for row in rows] == ["best-first"]


def test_the_residue_honesty_differential_over_the_pattern_family(metta):
    """The F-phase lane: evaluating R under theta must equal brute force,
    over the same pattern family the conformance kit generates (ground,
    opened positions, repeated-variable folds). The provider answers every
    atom conditionally; brute force applies the same condition by hand.
    """
    from petta.testing import _claim_patterns, _unifiable

    stored = [parse(f"(edge {x} {n})") for x, n in [("a", 1), ("b", 5), ("c", 9)]]

    class _Conditional(SpaceProvider):
        def atoms(self):
            return iter(stored)

        def match(self, pattern, *, limit=None):
            for atom in stored:
                yield Answer(
                    value=atom,
                    residue=Expr([Sym(">"), atom.children[2], Gnd(3)]),
                )

    metta.register_space(_Conditional(), "&ap-diff")
    checked = 0
    for base in stored:
        for pattern in _claim_patterns(base):
            got = metta.run(f"!(collapse (match &ap-diff {pattern} {pattern}))")
            answered = sorted(str(a) for a in got[0][0].children)
            brute = sorted(
                str(atom)
                for atom in stored
                if _unifiable(pattern, atom) and atom.children[2].value > 3
            )
            assert answered == brute, (str(pattern), answered, brute)
            checked += 1
    assert checked == 24  # three atoms, eight family patterns each


# --------------------------------------------------------- error modes (G2)


class _FlakyProvider(SpaceProvider):
    def __init__(self, boom):
        self.boom = boom

    def atoms(self):
        return iter(())

    def match(self, pattern, *, limit=None):
        yield parse("(edge a b)")
        raise self.boom


def test_the_undeclared_floor_aborts(metta):
    metta.register_space(_FlakyProvider(ValueError("fell over")), "&oe-abort")
    with pytest.raises(EngineError, match="fell over"):
        metta.run("!(collapse (match &oe-abort (edge $x $y) $y))")


def test_keep_delivers_the_failure_as_an_answer(metta):
    metta.register_space(_FlakyProvider(ValueError("fell over")), "&oe-keep")
    metta.declare_on_error("&oe-keep", "(edge $x $y)", "keep")
    out = metta.run("!(collapse (match &oe-keep (edge $x $y) $y))")
    answers = out[0][0].children
    # The streamed answer survives, and the failure is one more answer in
    # the language's own (Error <query> <reason>) shape.
    assert str(answers[0]) == "b"
    assert str(answers[1].children[0]) == "Error"
    assert "fell over" in str(answers[1].children[2])


def test_empty_ends_the_stream_by_declaration(metta):
    metta.register_space(_FlakyProvider(ValueError("fell over")), "&oe-empty")
    metta.declare_on_error("&oe-empty", "(edge $x $y)", "empty")
    out = metta.run("!(collapse (match &oe-empty (edge $x $y) $y))")
    assert str(out[0][0]) == "(b)"


def test_the_mode_routes_by_shape_most_specific_first(metta):
    metta.register_space(_FlakyProvider(ValueError("fell over")), "&oe-shape")
    metta.declare_on_error("&oe-shape", "(edge $x $y)", "keep")
    metta.declare_on_error("&oe-shape", "(edge a $y)", "empty")
    # The narrower shape empties; the general one keeps.
    out = metta.run("!(collapse (match &oe-shape (edge a $y) $y))")
    assert str(out[0][0]) == "(b)"
    out = metta.run("!(collapse (match &oe-shape (edge $q $y) $y))")
    assert "Error" in str(out[0][0])


def test_a_transport_failure_always_aborts(metta):
    metta.register_space(_FlakyProvider(OSError("router gone")), "&oe-transport")
    metta.declare_on_error("&oe-transport", "(edge $x $y)", "keep")
    # The original TransportFailure re-arrives as itself, so the
    # trichotomy is testable by class rather than by transcript text.
    with pytest.raises(TransportFailure, match="router gone"):
        metta.run("!(collapse (match &oe-transport (edge $x $y) $y))")


def test_an_op_keeps_its_failure_as_the_error_atom(metta):
    def half(x):
        if x % 2:
            raise ValueError(f"{x} is odd")
        return x // 2

    metta.register_op(half, name="oe-half", typed=False)
    metta.declare_on_error("oe-half", "(oe-half $x)", "keep")
    out = metta.run("!(collapse (oe-half 8))")
    assert str(out[0][0]) == "(4)"
    out = metta.run("!(collapse (oe-half 7))")
    (answer,) = out[0][0].children
    assert str(answer.children[0]) == "Error"
    assert "7 is odd" in str(answer.children[2])


def test_an_op_empty_answers_nothing(metta):
    def quarter(x):
        raise RuntimeError("always broken")

    metta.register_op(quarter, name="oe-quarter", typed=False)
    metta.declare_on_error("oe-quarter", "(oe-quarter $x)", "empty")
    out = metta.run("!(collapse (oe-quarter 8))")
    assert str(out[0][0]) == "()"


def test_declare_on_error_validates(metta):
    with pytest.raises(ValueError, match="keep, empty, abort"):
        metta.declare_on_error("&oe-v", "(edge $x $y)", "retry")


def test_a_generator_op_keeps_its_mid_stream_failure(metta):
    def counting(x):
        yield 1
        yield 2
        raise ValueError("stream died")

    metta.register_op(counting, name="oe-gen", typed=False)
    metta.declare_on_error("oe-gen", "(oe-gen $x)", "keep")
    out = metta.run("!(collapse (oe-gen 0))")
    answers = out[0][0].children
    assert [str(a) for a in answers[:2]] == ["1", "2"]
    assert str(answers[2].children[0]) == "Error"
    assert "stream died" in str(answers[2].children[2])


# ------------------------------------------------------- writes and G3


class _TxStore(SpaceProvider):
    """A store with real begin/commit/rollback, journal-style."""

    def __init__(self):
        self.rows = []
        self.journal = None
        self.calls = []

    def atoms(self):
        return iter(self.rows)

    def add(self, atom):
        self.rows.append(atom)

    def begin(self):
        self.calls.append("begin")
        self.journal = list(self.rows)

    def commit(self):
        self.calls.append("commit")
        self.journal = None

    def rollback(self):
        self.calls.append("rollback")
        self.rows = self.journal
        self.journal = None


def test_an_undeclared_foreign_write_in_a_transaction_is_loud(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-un")
    with pytest.raises(EngineError, match="declares nothing about its"):
        metta.run("!(transaction (add-atom &tx-un (edge a b)))")
    assert store.rows == []


def test_best_effort_is_the_declared_acceptance(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-be")
    metta.declare_writes("&tx-be", "best-effort")
    metta.run(
        "!(transaction (let $t (add-atom &tx-be (edge a b))"
        " (match &self (tx-no-such $q) $q)))"
    )
    # The transaction failed; the declared best-effort write survives,
    # which is exactly what the author signed.
    assert [str(r) for r in store.rows] == ["(edge a b)"]


def test_a_transactional_provider_commits_with_the_engine(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-ok")
    metta.declare_writes("&tx-ok", "transactional")
    metta.run("!(add-atom &self (tx-native base))")
    metta.run(
        "!(transaction (let $t1 (add-atom &tx-ok (edge a b))"
        " (add-atom &self (tx-native committed))))"
    )
    assert [str(r) for r in store.rows] == ["(edge a b)"]
    assert store.calls == ["begin", "commit"]
    hits = metta.run("!(collapse (match &self (tx-native committed) hit))")
    assert str(hits[0][0]) == "(hit)"


def test_a_failed_transaction_rolls_both_stores_back(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-rb")
    metta.declare_writes("&tx-rb", "transactional")
    metta.run(
        "!(transaction (let $t1 (add-atom &tx-rb (edge a b))"
        " (let $t2 (add-atom &self (tx-native aborted))"
        " (match &self (tx-no-such $q) $q))))"
    )
    assert store.rows == []
    assert store.calls == ["begin", "rollback"]
    hits = metta.run("!(collapse (match &self (tx-native aborted) hit))")
    assert str(hits[0][0]) == "()"


def test_a_throwing_transaction_rolls_back_and_rethrows(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-throw")
    metta.declare_writes("&tx-throw", "transactional")
    with pytest.raises(EngineError):
        metta.run(
            "!(transaction (let $t1 (add-atom &tx-throw (edge a b))"
            " (% 1 0)))"
        )
    assert store.rows == []
    assert store.calls == ["begin", "rollback"]


def test_atomic_single_refuses_transactional_writes(metta):
    store = _TxStore()
    metta.register_space(store, "&tx-as")
    metta.declare_writes("&tx-as", "atomic-single")
    with pytest.raises(EngineError, match="atomic-single"):
        metta.run("!(transaction (add-atom &tx-as (edge a b)))")
    # Outside a transaction the single write is untouched, the floor.
    metta.run("!(add-atom &tx-as (edge c d))")
    assert [str(r) for r in store.rows] == ["(edge c d)"]


def test_a_transactional_declaration_without_the_methods_is_loud(metta):
    class _Plain(SpaceProvider):
        def __init__(self):
            self.rows = []

        def atoms(self):
            return iter(self.rows)

        def add(self, atom):
            self.rows.append(atom)

    metta.register_space(_Plain(), "&tx-nm")
    metta.declare_writes("&tx-nm", "transactional")
    with pytest.raises(PettaError, match="Transactional"):
        metta.run("!(transaction (add-atom &tx-nm (edge a b)))")


def test_declare_writes_validates(metta):
    with pytest.raises(ValueError, match="transactional, atomic-single"):
        metta.declare_writes("&tx-v", "eventually")


# ------------------------------------------------------- merge policy (G4)


class _NamedRows(SpaceProvider):
    def __init__(self, rows):
        self.rows = [parse(r) for r in rows]

    def atoms(self):
        return iter(self.rows)

    def match(self, pattern, *, limit=None):
        yield from self.rows


def test_the_undeclared_multi_context_merge_is_depth(metta):
    metta.register_space(_NamedRows(["(row a1)", "(row a2)"]), "&mg-a")
    metta.register_space(_NamedRows(["(row b1)", "(row b2)"]), "&mg-b")
    out = metta.run("!(collapse (match (superpose (&mg-a &mg-b)) (row $x) $x))")
    assert str(out[0][0]) == "(a1 a2 b1 b2)"


def test_a_declared_fair_merge_interleaves(metta):
    metta.register_space(_NamedRows(["(frow a1)", "(frow a2)", "(frow a3)"]), "&mg-fa")
    metta.register_space(_NamedRows(["(frow b1)", "(frow b2)"]), "&mg-fb")
    metta.declare_merge("(frow $x)", "fair")
    out = metta.run("!(collapse (match (superpose (&mg-fa &mg-fb)) (frow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2 a3)"


def test_a_best_first_merge_orders_across_contexts(metta):
    class _Scored(SpaceProvider):
        def __init__(self, rows):
            self.rows = rows

        def atoms(self):
            return iter(parse(f"(srow {name})") for name, _ in self.rows)

        def match(self, pattern, *, limit=None):
            for name, k in self.rows:
                yield Answer(value=parse(f"(srow {name})"), k=k)

    metta.register_space(_Scored([("a1", 0.9), ("a2", 0.4)]), "&mg-sa")
    metta.register_space(_Scored([("b1", 0.7), ("b2", 0.1)]), "&mg-sb")
    metta.declare_annotations("&mg-sa", "ranked")
    metta.declare_annotations("&mg-sb", "ranked")
    metta.declare_merge("(srow $x)", "best-first")
    # Without both emission promises the merge is refused loudly.
    with pytest.raises(EngineError, match="emits"):
        metta.run("!(collapse (match (superpose (&mg-sa &mg-sb)) (srow $x) $x))")
    metta.declare_emits("&mg-sa", "best-first")
    metta.declare_emits("&mg-sb", "best-first")
    out = metta.run("!(collapse (match (superpose (&mg-sa &mg-sb)) (srow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2)"


def test_the_merge_routes_by_shape(metta):
    metta.register_space(_NamedRows(["(rrow a1)", "(rrow a2)"]), "&mg-ra")
    metta.register_space(_NamedRows(["(rrow b1)", "(rrow b2)"]), "&mg-rb")
    metta.declare_merge("(rrow $x)", "fair")
    metta.declare_merge("(rrow a1)", "depth")
    # The narrower shape keeps depth; the general one interleaves.
    out = metta.run("!(collapse (match (superpose (&mg-ra &mg-rb)) (rrow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2)"


def test_declare_merge_validates(metta):
    with pytest.raises(ValueError, match="depth, fair, best-first"):
        metta.declare_merge("(x $y)", "roundrobin")


# ---------------------------------------------- bridges and admission (G5)


def test_a_bridge_inserts_under_the_matched_bindings(metta):
    metta.declare_reaction("&br-src", "(fact $x $y)", "(insert &br-mirror (mirrored $y $x))")
    metta.run("!(add-atom &br-src (fact one two))")
    out = metta.run("!(collapse (match &br-mirror (mirrored $a $b) ($a $b)))")
    assert str(out[0][0]) == "((two one))"


def test_a_revise_bridge_replaces(metta):
    metta.run("!(add-atom &br-state (mode old))")
    metta.declare_reaction(
        "&br-cmd", "(set-mode $m)", "(revise &br-state (mode $_) (mode $m))"
    )
    metta.run("!(add-atom &br-cmd (set-mode new))")
    out = metta.run("!(collapse (match &br-state (mode $m) $m))")
    assert str(out[0][0]) == "(new)"


def test_a_bridge_cascade_is_bounded(metta):
    metta.declare_reaction("&br-loop", "(tick $n)", "(insert &br-loop (tick $n))")
    with pytest.raises(EngineError, match="cascade"):
        metta.run("!(add-atom &br-loop (tick 1))")


def test_an_unknown_bridge_head_is_loud(metta):
    metta.declare_reaction("&br-bad", "(x $y)", "(teleport &elsewhere $y)")
    with pytest.raises(EngineError, match="managed head"):
        metta.run("!(add-atom &br-bad (x 1))")


def test_admission_types_the_pool(metta):
    metta.declare_admits("&pool", "Space")
    metta.run("!(add-atom &self (: &worker-a Space))")
    metta.run("!(add-atom &pool &worker-a)")
    with pytest.raises(EngineError, match="does-not-carry"):
        metta.run("!(add-atom &pool (not a space))")
    out = metta.run("!(collapse (match &pool $s $s))")
    assert str(out[0][0]) == "(&worker-a)"


def test_capacity_bounds_the_pool(metta):
    metta.declare_admits("&pool2", "Space")
    metta.declare_capacity("&pool2", 2)
    for name in ("&w1", "&w2"):
        metta.run(f"!(add-atom &self (: {name} Space))")
        metta.run(f"!(add-atom &pool2 {name})")
    metta.run("!(add-atom &self (: &w3 Space))")
    with pytest.raises(EngineError, match="capacity"):
        metta.run("!(add-atom &pool2 &w3)")
    # The pool stays queryable like anything else: how full, holding what.
    out = metta.run("!(collapse (match &pool2 $s $s))")
    assert str(out[0][0]) == "(&w1 &w2)"


def test_declare_capacity_validates(metta):
    with pytest.raises(ValueError, match="positive integer"):
        metta.declare_capacity("&pool3", 0)


def test_admission_is_sugar_over_the_pre_add_hook(metta):
    """declare_admits claims the pool's pre-add hook like any handler.

    The claim is visible through the same &petta contract atom every hook
    claim leaves, and a second claimant meets the one-claimant rule, not a
    bespoke wrapper.
    """
    metta.declare_admits("&pool4", "Space")
    out = metta.run("!(match &petta (pre-add &pool4 $h) $h)")
    assert str(out[0][0]) == "space-admission-guard-&pool4"
    with pytest.raises(EngineError, match="claims"):
        metta.run("!(declare-pre-add! &pool4 my-own-guard)")


# ------------------------------------------------------- replay lane (G6)


def test_a_recorded_session_replays_verbatim(metta):
    import random

    from petta import testing

    class _Roulette(SpaceProvider):
        """A host-stateful context: answers differ across live runs."""

        def __init__(self):
            self.rng = random.Random()

        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):
            yield parse(f"(spin {self.rng.randrange(1_000_000)})")

    recording, replay = testing.record_replay(_Roulette())
    pattern = parse("(spin $n)")
    live = [str(a) for a in recording.match(pattern)]
    # The replayer serves the log verbatim, twice, however random the
    # host was; that is the oracle for a backend nobody can re-run.
    assert [str(a) for a in replay().match(pattern)] == live
    assert [str(a) for a in replay().match(pattern)] == live
    checks = testing.check_replay(_Roulette(), [parse("(spin $n)")])
    assert any("verbatim" in line for line in checks)


def test_a_replayer_refuses_an_unseen_query(metta):
    from petta import testing

    class _One(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):
            yield parse("(edge a b)")

    recording, replay = testing.record_replay(_One())
    list(recording.match(parse("(edge $x $y)")))
    assert [str(a) for a in replay().match(parse("(edge $x $y)"))] == ["(edge a b)"]
    with pytest.raises(AssertionError, match="never asked"):
        list(replay().match(parse("(other $q)")))


def test_a_replayed_provider_registers_like_any_other(metta):
    from petta import testing

    class _Feed(SpaceProvider):
        def atoms(self):
            return iter([parse("(tick 1)"), parse("(tick 2)")])

    recording, replay = testing.record_replay(_Feed())
    metta.register_space(recording, "&rp-live")
    live = metta.run("!(collapse (get-atoms &rp-live))")
    metta.register_space(replay(), "&rp-replay")
    replayed = metta.run("!(collapse (get-atoms &rp-replay))")
    assert str(replayed[0][0]) == str(live[0][0])


# --------------------------------------------------- context worlds (H1)


def test_negation_refuses_an_undeclared_foreign_world(metta):
    metta.register_space(_NamedRows(["(fact a)"]), "&cw-open")
    metta.run("(= (cw-ohas $x) (match &cw-open (fact $x) True))")
    # Positive queries are untouched, the floor.
    out = metta.run("!(collapse (match &cw-open (fact $x) $x))")
    assert str(out[0][0]) == "(a)"
    with pytest.raises(EngineError, match="closed-world"):
        metta.run("!(not-provable (cw-ohas b))")


def test_negation_runs_over_a_declared_closed_world(metta):
    metta.register_space(_NamedRows(["(fact a)"]), "&cw-closed")
    metta.declare_context("&cw-closed", "closed-world")
    metta.run("(= (cw-chas $x) (match &cw-closed (fact $x) True))")
    absent = metta.run("!(not-provable (cw-chas b))")
    present = metta.run("!(not-provable (cw-chas a))")
    assert str(absent[0][0]) == "True"
    assert str(present[0][0]) == "False"


def test_negation_over_native_spaces_is_untouched(metta):
    metta.run("!(add-atom &self (cw-native here))")
    metta.run("(= (cw-nhas $x) (match &self (cw-native $x) True))")
    out = metta.run("!(not-provable (cw-nhas missing))")
    assert str(out[0][0]) == "True"


def test_declare_context_validates(metta):
    with pytest.raises(ValueError, match="closed-world, open-world"):
        metta.declare_context("&cw-v", "half-open")


# ----------------------------------------------------------- explain (H3)


def test_explain_answers_the_route_and_the_route_is_honest(metta):
    class _Rec(SpaceProvider):
        def __init__(self):
            self.rows = [parse("(erow a)"), parse("(erow b)"), parse("(erow c)")]
            self.limits = []

        def atoms(self):
            return iter(self.rows)

        def match(self, pattern, *, limit=None):
            self.limits.append(limit)
            yield from self.rows[: limit if limit is not None else None]

    provider = _Rec()
    metta.register_space(provider, "&ex-s")
    metta.declare_handles("&ex-s", "(erow $x)", "Exact")
    metta.declare_source("&ex-s", "repeated")
    metta.declare_context("&ex-s", "closed-world")
    out = metta.run("!(explain (match &ex-s (erow $x) $x))")
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert str(explained["handles"].children[2]) == "Exact"
    assert str(explained["pushes"].children[1]) == "True"
    assert str(explained["source"].children[1]) == "repeated"
    assert str(explained["context"].children[1]) == "closed-world"
    assert str(explained["on-error"].children[1]) == "abort"
    assert str(explained["merge"].children[1]) == "depth"
    # The self-honesty law: explain said the bound pushes, so it must.
    metta.run("!(collapse (take 2 (match &ex-s (erow $x) $x)))")
    assert provider.limits == [2]


def test_explain_says_none_where_nothing_routes(metta):
    metta.register_space(_NamedRows(["(frow a)"]), "&ex-floor")
    out = metta.run("!(explain (match &ex-floor (frow $x) $x))")
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert str(explained["handles"].children[1]) == "none"
    assert str(explained["pushes"].children[1]) == "False"
    assert str(explained["writes"].children[1]) == "undeclared"


def test_explain_covers_operations(metta):
    def ex_lex(query, candidate=None):
        yield Answer(value="x", k=1.0)

    metta.register_op(ex_lex, name="ex-lex", typed=False)
    metta.declare_annotations("ex-lex", "ranked")
    out = metta.run('!(explain (ex-lex "q" $c))')
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert str(explained["annotations"].children[1]) == "ranked"
    assert str(explained["op"].children[3]) == "many"


def test_explain_refuses_the_unexplainable(metta):
    with pytest.raises(EngineError, match="explain covers"):
        metta.run("!(explain 42)")


# ---------------------------------------------------------- provenance (H2)


def test_prov_annotations_carry_source_terms(metta):
    class _Sourced(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):
            yield Answer(value=parse("(fact rain)"), k=parse("(src weather-db)"))
            yield Answer(value=parse("(fact wet)"), k=parse("(src rules)"))

    metta.register_space(_Sourced(), "&pv-s")
    metta.declare_annotations("&pv-s", "prov")
    out = metta.run(
        "!(collapse (let $r (match &pv-s (fact $x) $x) (pair $r (annotation))))"
    )
    assert (
        str(out[0][0])
        == "((pair rain (src weather-db)) (pair wet (src rules)))"
    )


def test_the_annotation_reads_one_outside_any_answer(metta):
    out = metta.run("!(annotation)")
    assert str(out[0][0]) == "1"


def test_a_join_multiplies_provenance(metta):
    class _Twice(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):
            head = str(pattern.children[0])
            if head == "edge":
                yield Answer(value=parse("(edge a b)"), k=parse("(src e1)"))
            else:
                yield Answer(value=parse("(link b c)"), k=parse("(src l1)"))

    metta.register_space(_Twice(), "&pv-j")
    metta.declare_annotations("&pv-j", "prov")
    out = metta.run(
        "!(collapse (let $p (match &pv-j (, (edge $x $y) (link $y $z)) (path $x $z))"
        " (pair $p (annotation))))"
    )
    assert str(out[0][0]) == "((pair (path a c) (times (src e1) (src l1))))"


def test_ranked_scores_read_through_the_annotation(metta):
    def pv_lex(query, candidate=None):
        yield Answer(value="hit", k=0.75)

    metta.register_op(pv_lex, name="pv-lex", typed=False)
    metta.declare_annotations("pv-lex", "ranked")
    out = metta.run(
        '!(collapse (let $r (pv-lex "q" $c) (pair $r (annotation))))'
    )
    assert str(out[0][0]) == '((pair "hit" 0.75))'


def test_top_still_refuses_the_unordered_prov(metta):
    metta.register_space(_NamedRows(["(prow a)"]), "&pv-t")
    metta.declare_annotations("&pv-t", "prov")
    with pytest.raises(EngineError, match="no order"):
        metta.run("!(collapse (top 1 (match &pv-t (prow $x) $x)))")


# ------------------------------------------------- minted handles (H4)


def test_fabricated_space_identities_are_refused():
    from petta import testing

    class _Minter(SpaceProvider):
        def atoms(self):
            yield parse("(stored-in &nowhere)")

    with pytest.raises(AssertionError, match="never minted"):
        testing.check_minted_handles(_Minter())
    # Naming the engine's own spaces is answering INTO them, which is fine.
    checks = testing.check_minted_handles(_Minter(), registered=["&nowhere"])
    assert any("engine's" in line for line in checks)


# ------------------------------------------------ surface consistency (I)


def test_hyperpose_is_parallel_under_the_languages_name(metta):
    metta.run("(= (ic-sq $x) (* $x $x))")
    answers = metta.hyperpose("(ic-sq 2)", "(ic-sq 3)")
    assert sorted(str(a) for a in answers) == ["4", "9"]


def test_fn_decodes_exactly_as_value(metta):
    metta.run("(= (ic-seven) 7)")
    assert metta.one("(ic-seven)") == 7
    assert metta.fn("ic-seven")() == 7
    assert type(metta.fn("ic-seven")()) is type(metta.one("(ic-seven)"))


def test_the_three_families_share_the_tolerant_member(metta):
    metta.run("(= (ic-many) (superpose (1 2 3)))")
    # first(): the first answer decoded, or None.
    assert metta.first("(ic-many)") == 1
    assert metta.fn("ic-many").first() == 1
    rows = metta.query(parse("(ic-no-such-fact $x)"))
    assert rows.first() is None


def test_rows_one_raises_the_family_exception(metta):
    metta.run("!(add-atom &self (ic-fact a))")
    metta.run("!(add-atom &self (ic-fact b))")
    rows = metta.query(parse("(ic-fact $x)"))
    with pytest.raises(EngineError, match="exactly one row"):
        rows.one()
