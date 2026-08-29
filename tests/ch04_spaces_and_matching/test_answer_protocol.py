"""Purpose: the explicit answer form, end to end: a provider or operation
answers bindings for the query's own variables, plain atoms and explicit
answers mix in one stream, and the staged slots (residue, annotation)
refuse loudly instead of dropping silently.
Guarantees:
  - operations returning explicit bindings request evaluated Atom wrappers
    through `(arguments name atoms)` declarations [tested:
    test_a_generator_op_answers_bindings,
    test_a_det_op_answers_bindings_with_a_value; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - lazy Answers cache one source, enforce cardinality, preserve caller
    projections, and back bound function calls [tested:
    test_answers_are_lazy_cached_and_cardinality_aware,
    test_bound_function_namespace_validates_at_access;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - bound calls iterate their values while exposing caller bindings through
    projections and the rows face [tested:
    test_answers_project_caller_variables_and_slices_stay_answers;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - the settled ``reacts`` declaration spelling installs an ``(on ...)``
    bridge that runs under matched bindings [tested:
    test_a_bridge_inserts_under_the_matched_bindings; commit=0cfc68a483d8d64fb499e53bbe9a3cc63f68990f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gc

import pytest

from metta import TRUE, Answer, Bindings, Expression, S, V, parse
from metta.atoms import Grounded, Symbol, Variable
from metta.errors import EngineError, MettaError, MettaResultError, TransportFailure
from metta.foreign import SpaceProvider
from metta.results import Answers


def test_answer_wire_form_is_exact():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    wire = Answer({"x": 3}).to_wire()
    assert wire == ["a", [["x", ["n", 3]]], True, None]
    wire = Answer({"$y": Symbol("b")}, value=Symbol("v"), k=2).to_wire()
    assert wire == ["a", [["y", ["s", "b"]]], True, 2, ["s", "v"]]
    residue = parse("(check $z)")
    wire = Answer({}, residue=residue).to_wire()
    assert wire[:2] == ["a", []]
    assert wire[2] == residue.to_wire()
    # Variable keys normalize like string keys.
    assert Bindings({Variable("q"): 1}).to_wire() == ["a", [["q", ["n", 1]]], True, None]


def test_answer_validates_eagerly():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        yield from self.answer_for(pattern)


def _pattern_vars(pattern):
    return [child for child in pattern.children if isinstance(child, Variable)]


def test_a_provider_answers_bindings(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Bindings({y: Symbol("b")})
        yield Bindings({y: Symbol("c")})

    metta._register_space(_AnswerProvider(answer), "&ap-bind")
    out = metta.run("!(collapse (match &ap-bind (edge a $y) (got $y)))")
    assert str(out[0][0]) == "((got b) (got c))"


def test_plain_atoms_and_answers_mix_in_one_stream(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield parse("(edge a plain)")
        yield Bindings({y: Symbol("bound")})

    metta._register_space(_AnswerProvider(answer), "&ap-mix")
    out = metta.run("!(collapse (match &ap-mix (edge a $y) $y))")
    assert str(out[0][0]) == "(plain bound)"


def test_an_explicit_value_unifies_under_theta(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        # The candidate-with-bindings form: the value is the answer atom,
        # and theta must agree with it.
        yield Answer({y: Symbol("b")}, value=parse("(edge a b)"))
        # A value that CONTRADICTS theta is one failed unification: that
        # answer drops, the stream continues.
        yield Answer({y: Symbol("clash")}, value=parse("(edge a other)"))
        yield Bindings({y: Symbol("after")})

    metta._register_space(_AnswerProvider(answer), "&ap-val")
    out = metta.run("!(collapse (match &ap-val (edge a $y) $y))")
    assert str(out[0][0]) == "(b after)"


def test_theta_aliases_query_variables(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        x, y = _pattern_vars(pattern)
        yield Bindings({y: x})

    metta._register_space(_AnswerProvider(answer), "&ap-alias")
    out = metta.run("!(collapse (match &ap-alias (edge $x $y) (pair $x $y)))")
    (answers,) = out[0]
    (pair,) = answers.children
    assert isinstance(pair.children[1], Variable)
    assert pair.children[1].name == pair.children[2].name


def test_fresh_variables_in_theta_values_stay_open(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Bindings({y: Expression([Symbol("f"), Variable("fresh")])})

    metta._register_space(_AnswerProvider(answer), "&ap-open")
    out = metta.run("!(collapse (match &ap-open (edge a $y) $y))")
    (answers,) = out[0]
    (value,) = answers.children
    assert str(value.children[0]) == "f"
    assert isinstance(value.children[1], Variable)


def test_an_annotation_is_refused_loudly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: Symbol("b")}, k=0.5)

    metta._register_space(_AnswerProvider(answer), "&ap-k")
    with pytest.raises(EngineError, match="annotation"):
        metta.run("!(collapse (match &ap-k (edge a $y) $y))")


def test_an_enumeration_refuses_answers(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Wrong(SpaceProvider):
        def atoms(self):
            yield Bindings({"x": 1})

    metta._register_space(_Wrong(), "&ap-enum")
    # The seam raises its own MettaError, and the boundary re-raises
    # the original object rather than an EngineError transcript.
    with pytest.raises(MettaError, match="enumeration has no query"):
        metta.run("!(collapse (get-atoms &ap-enum))")


def test_an_enumeration_refuses_answers_through_the_term_door_too(metta):
    """The same refusal, reached by eval() rather than run().

    The two doors cross janus by different entry points, and only the goal
    string one clears a Python exception raised inside the engine. eval() left
    it pending, so the next call -- janus's own PrologError.__str__, rendering
    the error being classified -- died on it and the caller received a raw
    janus_swi.janus.PrologError instead of this MettaError [measured
    2026-08-29]. Nothing caught it because the sibling above drives run().
    """
    class _Wrong(SpaceProvider):
        def atoms(self):
            yield Bindings({"x": 1})

    metta._register_space(_Wrong(), "&ap-enum-term")
    with pytest.raises(MettaError, match="enumeration has no query"):
        metta.eval(S["collapse"](S["get-atoms"](S["&ap-enum-term"])))


def test_a_generator_op_answers_bindings(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def relate(x):
        yield Bindings({x: 1})
        yield Bindings({x: 2})

    metta.op(
        relate,
        name="ap-rel",
        effect="nondeterministicReadOnly",
        declarations=[Expression(S.arguments, S["ap-rel"], S.atoms)],
    )
    metta.run("(= (ap-probe $x) (let $r (ap-rel $x) (pair $x $r)))")
    out = metta.run("!(collapse (ap-probe $q))")
    assert str(out[0][0]) == "((pair 1 ()) (pair 2 ()))"


def test_a_det_op_answers_bindings_with_a_value(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def solve(x):
        return Answer({x: Symbol("found")}, value=Symbol("done"))

    metta.op(
        solve,
        name="ap-solve",
        effect="pureStructural",
        declarations=[Expression(S.arguments, S["ap-solve"], S.atoms)],
    )
    metta.run("(= (ap-sprobe $x) (let $r (ap-solve $x) (pair $x $r)))")
    out = metta.run("!(collapse (ap-sprobe $q))")
    assert str(out[0][0]) == "((pair found done))"


def test_a_raw_op_refuses_answers(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def wrong(x):
        return Answer({"x": x})

    metta.op(wrong, name="ap-raw", transport="raw", effect="pureStructural")
    with pytest.raises(EngineError, match="raw"):
        metta.run("!(ap-raw 1)")


# ------------------------------------------------------------- residue (F2)


def test_a_residue_condition_filters_answers(metta):
    """The residue is the part of the query the provider did not discharge,
    written over the pattern's own variables and closed by the engine: a
    condition reducing to false drops that answer and nothing else.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        keeps = Expression([Symbol(">"), y, Grounded(3)])
        yield Answer({y: 5}, residue=keeps)
        yield Answer({y: 2}, residue=keeps)
        yield Answer({y: 9}, residue=keeps)

    metta._register_space(_AnswerProvider(answer), "&ap-cond")
    out = metta.run("!(collapse (match &ap-cond (edge a $y) $y))")
    assert str(out[0][0]) == "(5 9)"


def test_a_residue_match_form_composes_across_contexts(metta):
    """A residue may itself be a match, so one provider's answer closes
    against another context's atoms, composing bindings by sharing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(add-atom &ap-kb (allowed b))")

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        check = parse("(match &ap-kb (allowed $v) ok)")
        (v,) = [c for c in check.children[2].children if isinstance(c, Variable)]
        yield Answer({y: Symbol("b")}, residue=Expression([check.children[0], check.children[1], Expression([check.children[2].children[0], y]), Symbol("ok")]))
        yield Answer({y: Symbol("c")}, residue=Expression([check.children[0], check.children[1], Expression([check.children[2].children[0], y]), Symbol("ok")]))

    metta._register_space(_AnswerProvider(answer), "&ap-cross")
    out = metta.run("!(collapse (match &ap-cross (edge a $y) $y))")
    assert str(out[0][0]) == "(b)"


def test_a_nonreducing_residue_holds(metta):
    """A residue with no equation answers itself, exactly as !(edge q w)
    does at the top level, so it holds; the language's own rule.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: Symbol("kept")}, residue=parse("(ap-no-equation q w)"))

    metta._register_space(_AnswerProvider(answer), "&ap-hold")
    out = metta.run("!(collapse (match &ap-hold (edge a $y) $y))")
    assert str(out[0][0]) == "(kept)"


def test_a_conditional_answer_under_a_pushed_bound_is_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def answer(pattern):
        (y,) = _pattern_vars(pattern)
        yield Answer({y: 5}, residue=Expression([Symbol(">"), y, Grounded(3)]))

    metta._register_space(_AnswerProvider(answer), "&ap-bound")
    metta._at("&ap-bound").handles("(edge a $y)", "Exact")
    with pytest.raises(EngineError, match="Sound"):
        metta.run("!(collapse (take 2 (match &ap-bound (edge a $y) $y)))")
    # Without the bound the same conditional answer is fine.
    out = metta.run("!(collapse (match &ap-bound (edge a $y) $y))")
    assert str(out[0][0]) == "(5)"


def test_an_op_residue_closes_through_the_engine(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def pick(x):
        return Answer({x: 2}, value=Symbol("small"), residue=Expression([Symbol("<"), x, Grounded(10)]))

    def pickbig(x):
        return Answer({x: 50}, value=Symbol("big"), residue=Expression([Symbol("<"), x, Grounded(10)]))

    metta.op(
        pick,
        name="ap-pick",
        effect="pureStructural",
        declarations=[Expression(S.arguments, S["ap-pick"], S.atoms)],
    )
    metta.op(
        pickbig,
        name="ap-pickbig",
        effect="pureStructural",
        declarations=[Expression(S.arguments, S["ap-pickbig"], S.atoms)],
    )
    out = metta.run("!(collapse (ap-pick $x))")
    assert str(out[0][0]) == "(small)"
    # The failing residue makes the call answer nothing, the semidet rule.
    out = metta.run("!(collapse (ap-pickbig $x))")
    assert str(out[0][0]) == "()"


def test_planner_rows_may_be_bindings(metta):
    """SEAM-P-10: a plan row may bind the claimed patterns' variables
    directly instead of re-unifying atom rows, and the two mix.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    class _JoinProvider(SpaceProvider):
        def __init__(self):
            self.planned = []

        def atoms(self):
            return iter([parse("(edge a b)"), parse("(edge b c)")])

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
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
                        Answer({x: Symbol("a"), y: Symbol("b"), z: Symbol("c")}),
                        [parse("(edge b c)"), parse("(edge c d)")],
                    ]
                ),
            )

    provider = _JoinProvider()
    metta._register_space(provider, "&ap-plan")
    out = metta.run(
        "!(collapse (match &ap-plan (, (edge $x $y) (edge $y $z)) (path $x $z)))"
    )
    assert provider.planned
    assert str(out[0][0]) == "((path a c) (path b d))"


# ------------------------------------------------- annotations and top (F3)


def test_top_over_an_annotated_op_answers_the_k_best_in_order(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    lexicon = {"alpha": 0.4, "beta": 0.9, "gamma": 0.1, "delta": 0.7}

    def ap_lex(query, candidate=None):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        # Deliberately NOT best first: the engine's ordering must not
        # depend on the producer being polite. The op answers through the
        # general surface: the candidate is the value and the degree is
        # the answer's annotation, nothing pair-shaped.
        for word, degree in lexicon.items():
            yield Answer(value=word, k=degree)

    metta.op(ap_lex, name="ap-lex", effect="nondeterministicReadOnly")
    metta.annotations("ap-lex", "ranked")
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


def test_top_orders_mixed_integer_and_float_annotations_by_value(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # SWI compares numbers by value with type only breaking ties, unlike
    # the ISO standard order where every float precedes every integer, so
    # this pin protects top against any engine where that differs.
    def mixed(query, candidate=None):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield Answer(value=Symbol("intone"), k=1)
        yield Answer(value=Symbol("floathigh"), k=2.5)

    metta.op(mixed, name="ap-mixed-k", effect="nondeterministicReadOnly")
    metta.annotations("ap-mixed-k", "ranked")
    (best,) = metta.run("!(collapse (top 1 (ap-mixed-k q)))")[0]
    assert [str(a) for a in best.children] == ["floathigh"]


def test_top_refuses_an_unordered_context(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []

    def answer(pattern):
        calls.append(pattern)
        yield parse("(edge a b)")

    metta._register_space(_AnswerProvider(answer), "&ap-topfloor")
    with pytest.raises(EngineError, match="ranked"):
        metta.run("!(collapse (top 2 (match &ap-topfloor (edge $x $y) $y)))")
    assert calls == []


def test_top_pushes_the_bound_under_three_declarations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Ranked(SpaceProvider):
        def __init__(self):
            self.rows = [("a", 0.5), ("b", 0.9), ("c", 0.7)]
            self.limits = []

        def atoms(self):
            return iter(parse(f"(scored {name})") for name, _ in self.rows)

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            self.limits.append(limit)
            ordered = sorted(self.rows, key=lambda row: -row[1])
            if limit is not None:
                ordered = ordered[:limit]
            for name, k in ordered:
                yield Answer(value=parse(f"(scored {name})"), k=k)

    provider = _Ranked()
    metta._register_space(provider, "&ap-vec")
    metta.annotations("&ap-vec", "ranked")
    # Two of the three declarations: the bound stays here.
    metta._at("&ap-vec").handles("(scored $x)", "Exact")
    out = metta.run("!(collapse (top 2 (match &ap-vec (scored $x) $x)))")
    assert provider.limits == [None]
    assert str(out[0][0]) == "(b c)"
    # The third lands and the provider is handed the bound.
    metta._at("&ap-vec").emits("best-first")
    provider.limits.clear()
    out = metta.run("!(collapse (top 2 (match &ap-vec (scored $x) $x)))")
    assert provider.limits == [2]
    assert str(out[0][0]) == "(b c)"


def test_an_undeclared_annotation_names_the_declaration(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def scorer(x):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield Answer(value=Symbol("v"), k=0.5)

    metta.op(
        scorer,
        name="ap-undeclared",
        effect="nondeterministicReadOnly",
        declarations=[Expression(S.arguments, S["ap-undeclared"], S.atoms)],
    )
    with pytest.raises(EngineError, match="annotations ap-undeclared ranked"):
        metta.run("!(collapse (ap-undeclared 1))")


def test_declare_annotations_validates_and_replaces(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="ranked"):
        metta.annotations("&ap-v", "sorta")
    metta.annotations("&ap-v", "ranked")
    metta.annotations("&ap-v", "prob")
    rows = metta._at("&metta").match(parse("(annotations &ap-v $s)"))
    assert [str(row.s) for row in rows] == ["prob"]


def test_declare_emits_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="best-first"):
        metta._at("&ap-v").emits("fastest")
    metta._at("&ap-v").emits("best-first")
    rows = metta._at("&metta").match(parse("(emits &ap-v $p)"))
    assert [str(row.p) for row in rows] == ["best-first"]


def test_the_residue_honesty_differential_over_the_pattern_family(metta):
    """The F-phase lane: evaluating R under theta must equal brute force,
    over the same pattern family the conformance kit generates (ground,
    opened positions, repeated-variable folds). The provider answers every
    atom conditionally; brute force applies the same condition by hand.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta.testing import _claim_patterns, _unifiable

    stored = [parse(f"(edge {x} {n})") for x, n in [("a", 1), ("b", 5), ("c", 9)]]

    class _Conditional(SpaceProvider):
        def atoms(self):
            return iter(stored)

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            for atom in stored:
                yield Answer(
                    value=atom,
                    residue=Expression([Symbol(">"), atom.children[2], Grounded(3)]),
                )

    metta._register_space(_Conditional(), "&ap-diff")
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

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        yield parse("(edge a b)")
        raise self.boom


def test_the_undeclared_floor_aborts(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_FlakyProvider(ValueError("fell over")), "&oe-abort")
    with pytest.raises(EngineError, match="fell over"):
        metta.run("!(collapse (match &oe-abort (edge $x $y) $y))")


def test_keep_delivers_the_failure_as_an_answer(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_FlakyProvider(ValueError("fell over")), "&oe-keep")
    metta._at("&oe-keep").on_error("(edge $x $y)", "keep")
    out = metta.run("!(collapse (match &oe-keep (edge $x $y) $y))")
    answers = out[0][0].children
    # The streamed answer survives, and the failure is one more answer in
    # the language's own (Error <query> <reason>) shape.
    assert str(answers[0]) == "b"
    assert str(answers[1].children[0]) == "Error"
    assert "fell over" in str(answers[1].children[2])


def test_empty_ends_the_stream_by_declaration(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_FlakyProvider(ValueError("fell over")), "&oe-empty")
    metta._at("&oe-empty").on_error("(edge $x $y)", "empty")
    out = metta.run("!(collapse (match &oe-empty (edge $x $y) $y))")
    assert str(out[0][0]) == "(b)"


def test_the_mode_routes_by_shape_most_specific_first(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_FlakyProvider(ValueError("fell over")), "&oe-shape")
    metta._at("&oe-shape").on_error("(edge $x $y)", "keep")
    metta._at("&oe-shape").on_error("(edge a $y)", "empty")
    # The narrower shape empties; the general one keeps.
    out = metta.run("!(collapse (match &oe-shape (edge a $y) $y))")
    assert str(out[0][0]) == "(b)"
    out = metta.run("!(collapse (match &oe-shape (edge $q $y) $y))")
    assert "Error" in str(out[0][0])


def test_a_transport_failure_always_aborts(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_FlakyProvider(OSError("router gone")), "&oe-transport")
    metta._at("&oe-transport").on_error("(edge $x $y)", "keep")
    # The original TransportFailure re-arrives as itself, so the
    # trichotomy is testable by class rather than by transcript text.
    with pytest.raises(TransportFailure, match="router gone"):
        metta.run("!(collapse (match &oe-transport (edge $x $y) $y))")


def test_an_op_keeps_its_failure_as_the_error_atom(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def half(x):
        if x % 2:
            msg = f"{x} is odd"
            raise ValueError(msg)
        return x // 2

    metta.op(half, name="oe-half", effect="pureStructural")
    metta.on_error("oe-half", "(oe-half $x)", "keep")
    out = metta.run("!(collapse (oe-half 8))")
    assert str(out[0][0]) == "(4)"
    out = metta.run("!(collapse (oe-half 7))")
    (answer,) = out[0][0].children
    assert str(answer.children[0]) == "Error"
    assert "7 is odd" in str(answer.children[2])


def test_an_op_empty_answers_nothing(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def quarter(x):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        msg = "always broken"
        raise RuntimeError(msg)

    metta.op(quarter, name="oe-quarter", effect="pureStructural")
    metta.on_error("oe-quarter", "(oe-quarter $x)", "empty")
    out = metta.run("!(collapse (oe-quarter 8))")
    assert str(out[0][0]) == "()"


def test_declare_on_error_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="keep, empty, abort"):
        metta._at("&oe-v").on_error("(edge $x $y)", "retry")


def test_a_generator_op_keeps_its_mid_stream_failure(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def counting(x):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield 1
        yield 2
        msg = "stream died"
        raise ValueError(msg)

    metta.op(counting, name="oe-gen", effect="nondeterministicReadOnly")
    metta.on_error("oe-gen", "(oe-gen $x)", "keep")
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


def test_an_undeclared_foreign_write_in_a_transaction_is_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-un")
    with pytest.raises(EngineError, match="declares nothing about its"):
        metta.run("!(transaction (add-atom &tx-un (edge a b)))")
    assert store.rows == []


def test_best_effort_is_the_declared_acceptance(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-be")
    metta._at("&tx-be").writes("best-effort")
    metta.run(
        "!(transaction (let $t (add-atom &tx-be (edge a b))"
        " (match &self (tx-no-such $q) $q)))"
    )
    # The transaction failed; the declared best-effort write survives,
    # which is exactly what the author signed.
    assert [str(r) for r in store.rows] == ["(edge a b)"]


def test_a_transactional_provider_commits_with_the_engine(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-ok")
    metta._at("&tx-ok").writes("transactional")
    metta.run("!(add-atom &self (tx-native base))")
    metta.run(
        "!(transaction (let $t1 (add-atom &tx-ok (edge a b))"
        " (add-atom &self (tx-native committed))))"
    )
    assert [str(r) for r in store.rows] == ["(edge a b)"]
    assert store.calls == ["begin", "commit"]
    hits = metta.run("!(collapse (match &self (tx-native committed) hit))")
    assert str(hits[0][0]) == "(hit)"


def test_a_file_transaction_enlists_and_commits_a_foreign_provider(
    metta, tmp_path
):
    """A source load commits writes to its enlisted foreign provider."""
    store = _TxStore()
    metta._register_space(store, "&tx-file-ok")
    metta._at("&tx-file-ok").writes("transactional")
    source = tmp_path / "foreign_transaction_commit.metta"
    source.write_text("!(transaction (add-atom &tx-file-ok (edge a b)))\n")

    metta.load(source)

    assert [str(row) for row in store.rows] == ["(edge a b)"]
    assert store.calls == ["begin", "commit"]


def test_a_failed_file_transaction_rolls_a_foreign_provider_back(
    metta, tmp_path
):
    """A failed source load rolls its foreign-provider writes back."""
    store = _TxStore()
    metta._register_space(store, "&tx-file-rb")
    metta._at("&tx-file-rb").writes("transactional")
    source = tmp_path / "foreign_transaction_rollback.metta"
    source.write_text(
        "!(transaction (let $written (add-atom &tx-file-rb (edge a b)) "
        "(match &self (tx-file-no-such $x) $x)))\n"
    )

    metta.load(source)

    assert store.rows == []
    assert store.calls == ["begin", "rollback"]


def test_a_failed_transaction_rolls_both_stores_back(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-rb")
    metta._at("&tx-rb").writes("transactional")
    metta.run(
        "!(transaction (let $t1 (add-atom &tx-rb (edge a b))"
        " (let $t2 (add-atom &self (tx-native aborted))"
        " (match &self (tx-no-such $q) $q))))"
    )
    assert store.rows == []
    assert store.calls == ["begin", "rollback"]
    hits = metta.run("!(collapse (match &self (tx-native aborted) hit))")
    assert str(hits[0][0]) == "()"


def test_a_throwing_transaction_rolls_back_and_rethrows(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-throw")
    metta._at("&tx-throw").writes("transactional")
    with pytest.raises(EngineError):
        metta.run(
            "!(transaction (let $t1 (add-atom &tx-throw (edge a b))"
            " (+ $left $right)))"
        )
    assert store.rows == []
    assert store.calls == ["begin", "rollback"]


def test_atomic_single_refuses_transactional_writes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    store = _TxStore()
    metta._register_space(store, "&tx-as")
    metta._at("&tx-as").writes("atomic-single")
    with pytest.raises(EngineError, match="atomic-single"):
        metta.run("!(transaction (add-atom &tx-as (edge a b)))")
    # Outside a transaction the single write is untouched, the floor.
    metta.run("!(add-atom &tx-as (edge c d))")
    assert [str(r) for r in store.rows] == ["(edge c d)"]


def test_a_transactional_declaration_without_the_methods_is_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Plain(SpaceProvider):
        def __init__(self):
            self.rows = []

        def atoms(self):
            return iter(self.rows)

        def add(self, atom):
            self.rows.append(atom)

    metta._register_space(_Plain(), "&tx-nm")
    metta._at("&tx-nm").writes("transactional")
    with pytest.raises(MettaError, match="Transactional"):
        metta.run("!(transaction (add-atom &tx-nm (edge a b)))")


def test_declare_writes_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="transactional, atomic-single"):
        metta._at("&tx-v").writes("eventually")


# ------------------------------------------------------- merge policy (G4)


class _NamedRows(SpaceProvider):
    def __init__(self, rows):
        self.rows = [parse(r) for r in rows]

    def atoms(self):
        return iter(self.rows)

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        yield from self.rows


def test_the_undeclared_multi_context_merge_is_depth(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(row a1)", "(row a2)"]), "&mg-a")
    metta._register_space(_NamedRows(["(row b1)", "(row b2)"]), "&mg-b")
    out = metta.run("!(collapse (match (superpose (&mg-a &mg-b)) (row $x) $x))")
    assert str(out[0][0]) == "(a1 a2 b1 b2)"


def test_a_declared_fair_merge_interleaves(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(frow a1)", "(frow a2)", "(frow a3)"]), "&mg-fa")
    metta._register_space(_NamedRows(["(frow b1)", "(frow b2)"]), "&mg-fb")
    metta.merge("(frow $x)", "fair")
    out = metta.run("!(collapse (match (superpose (&mg-fa &mg-fb)) (frow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2 a3)"


def test_a_best_first_merge_orders_across_contexts(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Scored(SpaceProvider):
        def __init__(self, rows):
            self.rows = rows

        def atoms(self):
            return iter(parse(f"(srow {name})") for name, _ in self.rows)

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            for name, k in self.rows:
                yield Answer(value=parse(f"(srow {name})"), k=k)

    metta._register_space(_Scored([("a1", 0.9), ("a2", 0.4)]), "&mg-sa")
    metta._register_space(_Scored([("b1", 0.7), ("b2", 0.1)]), "&mg-sb")
    metta.annotations("&mg-sa", "ranked")
    metta.annotations("&mg-sb", "ranked")
    metta.merge("(srow $x)", "best-first")
    # Without both emission promises the merge is refused loudly.
    with pytest.raises(EngineError, match="emits"):
        metta.run("!(collapse (match (superpose (&mg-sa &mg-sb)) (srow $x) $x))")
    metta._at("&mg-sa").emits("best-first")
    metta._at("&mg-sb").emits("best-first")
    out = metta.run("!(collapse (match (superpose (&mg-sa &mg-sb)) (srow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2)"


def test_the_merge_routes_by_shape(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(rrow a1)", "(rrow a2)"]), "&mg-ra")
    metta._register_space(_NamedRows(["(rrow b1)", "(rrow b2)"]), "&mg-rb")
    metta.merge("(rrow $x)", "fair")
    metta.merge("(rrow a1)", "depth")
    # The narrower shape keeps depth; the general one interleaves.
    out = metta.run("!(collapse (match (superpose (&mg-ra &mg-rb)) (rrow $x) $x))")
    assert str(out[0][0]) == "(a1 b1 a2 b2)"


def test_declare_merge_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="depth, fair, best-first"):
        metta.merge("(x $y)", "roundrobin")


# ---------------------------------------------- bridges and admission (G5)


def test_a_bridge_inserts_under_the_matched_bindings(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._at("&br-src").reacts("(fact $x $y)", "(insert &br-mirror (mirrored $y $x))")
    metta.run("!(add-atom &br-src (fact one two))")
    out = metta.run("!(collapse (match &br-mirror (mirrored $a $b) ($a $b)))")
    assert str(out[0][0]) == "((two one))"


def test_a_revise_bridge_replaces(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(add-atom &br-state (mode old))")
    metta._at("&br-cmd").reaction("(set-mode $m)", "(revise &br-state (mode $_) (mode $m))"
    )
    metta.run("!(add-atom &br-cmd (set-mode new))")
    out = metta.run("!(collapse (match &br-state (mode $m) $m))")
    assert str(out[0][0]) == "(new)"


def test_a_bridge_cascade_is_bounded(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._at("&br-loop").reaction("(tick $n)", "(insert &br-loop (tick $n))")
    with pytest.raises(EngineError, match="cascade"):
        metta.run("!(add-atom &br-loop (tick 1))")


def test_an_unknown_bridge_head_is_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._at("&br-bad").reaction("(x $y)", "(teleport &elsewhere $y)")
    with pytest.raises(EngineError, match="managed head"):
        metta.run("!(add-atom &br-bad (x 1))")


def test_admission_types_the_pool(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._at("&pool").admits("Space")
    metta.run("!(add-atom &self (: &worker-a Space))")
    metta.run("!(add-atom &pool &worker-a)")
    with pytest.raises(EngineError, match="does-not-carry"):
        metta.run("!(add-atom &pool (not a space))")
    out = metta.run("!(collapse (match &pool $s $s))")
    assert str(out[0][0]) == "(&worker-a)"


def test_capacity_bounds_the_pool(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._at("&pool2").admits("Space")
    metta._at("&pool2").capacity(2)
    for name in ("&w1", "&w2"):
        metta.run(f"!(add-atom &self (: {name} Space))")
        metta.run(f"!(add-atom &pool2 {name})")
    metta.run("!(add-atom &self (: &w3 Space))")
    with pytest.raises(EngineError, match="capacity"):
        metta.run("!(add-atom &pool2 &w3)")
    # The pool stays queryable like anything else: how full, holding what.
    out = metta.run("!(collapse (match &pool2 $s $s))")
    assert str(out[0][0]) == "(&w1 &w2)"


def test_declare_capacity_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="positive integer"):
        metta._at("&pool3").capacity(0)


def test_admission_is_sugar_over_the_pre_add_hook(metta):
    """declare_admits claims the pool's pre-add hook like any handler.

    The claim is visible through the same &metta contract atom every hook
    claim leaves, and a second claimant meets the one-claimant rule, not a
    bespoke wrapper.
    """
    metta._at("&pool4").admits("Space")
    out = metta.run("!(match &metta (pre-add &pool4 $h) $h)")
    assert str(out[0][0]) == "space-admission-guard-&pool4"
    with pytest.raises(EngineError, match="claims"):
        metta.run("!(declare-pre-add! &pool4 my-own-guard)")


# ------------------------------------------------------- replay lane (G6)


def test_a_recorded_session_replays_verbatim(metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    import random

    from metta import testing

    class _Roulette(SpaceProvider):
        """A host-stateful context: answers differ across live runs."""

        def __init__(self):
            self.rng = random.Random()

        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
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


def test_a_replayer_refuses_an_unseen_query(metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

    class _One(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            yield parse("(edge a b)")

    recording, replay = testing.record_replay(_One())
    list(recording.match(parse("(edge $x $y)")))
    assert [str(a) for a in replay().match(parse("(edge $x $y)"))] == ["(edge a b)"]
    with pytest.raises(AssertionError, match="never asked"):
        list(replay().match(parse("(other $q)")))


def test_a_replayed_provider_registers_like_any_other(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

    class _Feed(SpaceProvider):
        def atoms(self):
            return iter([parse("(tick 1)"), parse("(tick 2)")])

    recording, replay = testing.record_replay(_Feed())
    metta._register_space(recording, "&rp-live")
    live = metta.run("!(collapse (get-atoms &rp-live))")
    metta._register_space(replay(), "&rp-replay")
    replayed = metta.run("!(collapse (get-atoms &rp-replay))")
    assert str(replayed[0][0]) == str(live[0][0])


# --------------------------------------------------- context worlds (H1)


def test_negation_refuses_an_undeclared_foreign_world(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(fact a)"]), "&cw-open")
    metta.run("(= (cw-ohas $x) (match &cw-open (fact $x) True))")
    # Positive queries are untouched, the floor.
    out = metta.run("!(collapse (match &cw-open (fact $x) $x))")
    assert str(out[0][0]) == "(a)"
    with pytest.raises(EngineError, match="closed-world"):
        metta.run("!(not-provable (cw-ohas b))")


def test_negation_runs_over_a_declared_closed_world(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(fact a)"]), "&cw-closed")
    metta._at("&cw-closed").context("closed-world")
    metta.run("(= (cw-chas $x) (match &cw-closed (fact $x) True))")
    absent = metta.run("!(not-provable (cw-chas b))")
    present = metta.run("!(not-provable (cw-chas a))")
    assert str(absent[0][0]) == "True"
    assert str(present[0][0]) == "False"


def test_negation_over_native_spaces_is_untouched(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(add-atom &self (cw-native here))")
    metta.run("(= (cw-nhas $x) (match &self (cw-native $x) True))")
    out = metta.run("!(not-provable (cw-nhas missing))")
    assert str(out[0][0]) == "True"


def test_declare_context_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="closed-world, open-world"):
        metta._at("&cw-v").context("half-open")


# ----------------------------------------------------------- explain (H3)


def test_explain_answers_the_route_and_the_route_is_honest(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Rec(SpaceProvider):
        def __init__(self):
            self.rows = [parse("(erow a)"), parse("(erow b)"), parse("(erow c)")]
            self.limits = []

        def atoms(self):
            return iter(self.rows)

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            self.limits.append(limit)
            yield from self.rows[: limit if limit is not None else None]

    provider = _Rec()
    metta._register_space(provider, "&ex-s")
    metta._at("&ex-s").handles("(erow $x)", "Exact")
    metta._at("&ex-s").source("repeated")
    metta._at("&ex-s").context("closed-world")
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


def test_explain_says_none_where_nothing_routes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(frow a)"]), "&ex-floor")
    out = metta.run("!(explain (match &ex-floor (frow $x) $x))")
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert str(explained["handles"].children[1]) == "none"
    assert str(explained["pushes"].children[1]) == "False"
    assert str(explained["writes"].children[1]) == "undeclared"


def test_explain_covers_operations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def ex_lex(query, candidate=None):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield Answer(value="x", k=1.0)

    metta.op(ex_lex, name="ex-lex", effect="nondeterministicReadOnly")
    metta.annotations("ex-lex", "ranked")
    out = metta.run('!(explain (ex-lex "q" $c))')
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert str(explained["annotations"].children[1]) == "ranked"
    assert str(explained["op"].children[3]) == "many"


def test_explain_refuses_the_unexplainable(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError, match="explain covers"):
        metta.run("!(explain 42)")


# ---------------------------------------------------------- provenance (H2)


def test_prov_annotations_carry_source_terms(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Sourced(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            yield Answer(value=parse("(fact rain)"), k=parse("(src weather-db)"))
            yield Answer(value=parse("(fact wet)"), k=parse("(src rules)"))

    metta._register_space(_Sourced(), "&pv-s")
    metta.annotations("&pv-s", "prov")
    out = metta.run(
        "!(collapse (let $r (match &pv-s (fact $x) $x) (pair $r (annotation))))"
    )
    assert (
        str(out[0][0])
        == "((pair rain (src weather-db)) (pair wet (src rules)))"
    )


def test_the_annotation_reads_one_outside_any_answer(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    out = metta.run("!(annotation)")
    assert str(out[0][0]) == "1"


def test_a_join_multiplies_provenance(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Twice(SpaceProvider):
        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            head = str(pattern.children[0])
            if head == "edge":
                yield Answer(value=parse("(edge a b)"), k=parse("(src e1)"))
            else:
                yield Answer(value=parse("(link b c)"), k=parse("(src l1)"))

    metta._register_space(_Twice(), "&pv-j")
    metta.annotations("&pv-j", "prov")
    out = metta.run(
        "!(collapse (let $p (match &pv-j (, (edge $x $y) (link $y $z)) (path $x $z))"
        " (pair $p (annotation))))"
    )
    assert str(out[0][0]) == "((pair (path a c) (times (src e1) (src l1))))"


def test_ranked_scores_read_through_the_annotation(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def pv_lex(query, candidate=None):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield Answer(value="hit", k=0.75)

    metta.op(pv_lex, name="pv-lex", effect="nondeterministicReadOnly")
    metta.annotations("pv-lex", "ranked")
    out = metta.run(
        '!(collapse (let $r (pv-lex "q" $c) (pair $r (annotation))))'
    )
    assert str(out[0][0]) == '((pair "hit" 0.75))'


def test_top_still_refuses_the_unordered_prov(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_NamedRows(["(prow a)"]), "&pv-t")
    metta.annotations("&pv-t", "prov")
    with pytest.raises(EngineError, match="no order"):
        metta.run("!(collapse (top 1 (match &pv-t (prow $x) $x)))")


# ------------------------------------------------- minted handles (H4)


def test_fabricated_space_identities_are_refused():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

    class _Minter(SpaceProvider):
        def atoms(self):
            yield parse("(stored-in &nowhere)")

    with pytest.raises(AssertionError, match="never minted"):
        testing.check_minted_handles(_Minter())
    # Naming the engine's own spaces is answering INTO them, which is fine.
    checks = testing.check_minted_handles(_Minter(), registered=["&nowhere"])
    assert any("engine's" in line for line in checks)


# ------------------------------------------------ surface consistency (I)


def test_hyperpose_is_parallel_under_the_languages_name(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (ic-sq $x) (* $x $x))")
    answers = metta.hyperpose("(ic-sq 2)", "(ic-sq 3)")
    assert sorted(str(a) for a in answers) == ["4", "9"]


def test_fn_decodes_exactly_as_value(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (ic-seven) 7)")
    assert metta._one("(ic-seven)") == 7
    assert metta.fn.ic_seven() == [7]
    assert type(metta.fn.ic_seven().one()) is type(metta._one("(ic-seven)"))


def test_the_three_families_share_the_tolerant_member(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (ic-many) (superpose (1 2 3)))")
    # first(): the first answer decoded; absence needs an explicit default.
    assert metta._first("(ic-many)") == 1
    assert metta.fn.ic_many().first() == 1
    rows = metta.match(parse("(ic-no-such-fact $x)"))
    marker = object()
    with pytest.raises(EngineError, match="pass default"):
        rows.first()
    assert rows.first(default=marker) is marker


def test_rows_one_raises_the_family_exception(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(add-atom &self (ic-fact a))")
    metta.run("!(add-atom &self (ic-fact b))")
    rows = metta.match(parse("(ic-fact $x)"))
    with pytest.raises(EngineError, match="exactly one answer"):
        rows.one()


# ------------------------------------------------ lazy evaluation answers (R3)


def test_answers_are_lazy_cached_and_cardinality_aware():  # noqa: D103 -- the test name states the contract
    pulled = []
    closed = []

    def source():
        try:
            for value in range(4):
                pulled.append(value)
                yield value
        finally:
            closed.append(True)

    answers = Answers(source())
    assert pulled == []
    assert bool(answers) is True
    assert pulled == [0]
    assert answers.first() == 0
    assert pulled == [0]
    assert list(answers) == [0, 1, 2, 3]
    assert list(answers) == [0, 1, 2, 3]
    assert pulled == [0, 1, 2, 3]
    assert hash(answers) == hash((0, 1, 2, 3))

    demanded = []

    def endless():
        value = 0
        while True:
            demanded.append(value)
            yield value
            value += 1

    with pytest.raises(EngineError, match="more than 1"):
        Answers(endless()).one()
    assert demanded == [0, 1]

    with pytest.raises(EngineError, match="pass default"):
        Answers(()).first()
    marker = object()
    assert Answers(()).first(default=marker) is marker

    abandoned = Answers(source())
    del abandoned
    gc.collect()
    assert closed


def test_bound_function_namespace_validates_at_access(metta):  # noqa: D103 -- the test name states the contract
    space = metta._new_space()
    assert space.fn.car_atom(Expression(1, 2)) == [1]
    assert space.fn["=="](1, 1).one() is True
    assert space.fn.pragma.__name__ == "pragma!"
    with pytest.raises(AttributeError, match="no function"):
        _ = space.fn.r3_typo_that_does_not_exist


def test_answers_project_caller_variables_and_slices_stay_answers(metta):  # noqa: D103 -- the test name states the contract
    space = metta._new_space()
    space.run("(= (r3-rel a) True) (= (r3-rel b) True)")
    answers = space.fn.r3_rel(V.who)
    assert answers.columns == ("who",)
    prefix = answers[:1]
    assert isinstance(prefix, Answers)
    assert list(prefix.who) == [S.a]
    assert list(answers[V.who]) == [S.a, S.b]
    assert list(answers) == [TRUE, TRUE]
    assert list(answers.rows) == [(S.a,), (S.b,)]

    colliding = space.fn.r3_rel(V.first)
    assert callable(colliding.first)
    assert list(colliding[V.first]) == [S.a, S.b]
    with pytest.raises(AttributeError, match="no answer variable"):
        _ = answers.typo


def test_answers_scalar_doors_raise_error_atoms_but_iteration_retains_them(metta):  # noqa: D103 -- the test name states the contract
    space = metta._new_space()
    answers = space.answers(S["/"](1, 0))
    assert len(list(answers)) == 1
    assert str(answers[0]).startswith("(Error ")
    with pytest.raises(MettaResultError):
        answers.one()
    with pytest.raises(MettaResultError):
        answers.first()


def test_function_calls_pull_engine_answers_only_as_demanded(metta):  # noqa: D103 -- the test name states the contract
    space = metta._new_space()
    pulled = []

    @space.op(name="r3-demand", effect="writesState")
    def demand():
        for value in (1, 2, 3):
            pulled.append(value)
            yield value

    answers = space.fn.r3_demand()
    assert pulled == []
    assert bool(answers)
    # The operation bridge keeps one host-generator lookahead, while Answers
    # itself has requested and cached exactly one engine answer.
    assert pulled == [1, 2]
    assert answers[0] == 1
    assert pulled == [1, 2]
    assert list(answers) == [1, 2, 3]
    assert pulled == [1, 2, 3]
