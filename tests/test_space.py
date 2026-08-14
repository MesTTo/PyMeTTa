"""Purpose: engine-backed tests for the MeTTa runtime surface: run, load,
space edits, queries, eval, parse, and the semantics matching the CLI's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

import petta
from petta import (
    EngineError,
    MeTTa,
    MettaOperationError,
    MettaSyntaxError,
    PettaError,
    S,
    StrictError,
    TimeLimitError,
    V,
    _engine,
    decode,
    expr,
    parse,
    val,
)
from petta.atoms import Gnd
from petta.foreign import SpaceProvider, register_provider, unregister_provider


@pytest.fixture()
def m(metta):
    """A fresh anonymous space per test, on the shared engine."""
    return metta.fresh_space()


def test_run_groups_answers_per_directive(metta):
    r = metta.run("!(+ 1 2)\n!(superpose (a b))")
    assert r == [[3], [S.a, S.b]]


def test_run_tutorial_shape(metta):
    r = metta.run("(= (foo42) boo)\n!(foo42)\n!(match &self (= (foo42) $b) $b)")
    assert r[0] == [S.boo]
    assert r[1] == [S.boo]


def test_run_booleans_and_strings(metta):
    r = metta.run('!(> 3 2)\n!(repr 42)')
    assert r[0] == [True]
    assert r[1] == ["42"]


def test_run_syntax_error_is_loud(metta):
    with pytest.raises(MettaSyntaxError) as failure:
        metta.run("! (broken")
    assert "line 1" in str(failure.value)
    assert "Unknown error term" not in str(failure.value)
    assert "petta_py_exception" not in str(failure.value)


def test_run_unknown_function_error_is_loud(metta):
    # An undefined head inside arithmetic is a hard engine error, exactly as
    # the CLI dies on it; nothing is swallowed.
    with pytest.raises(EngineError):
        metta.run("!(+ 1 (no-such-function-anywhere 2))")


@pytest.mark.parametrize(
    ("source", "operation", "expected", "culprit"),
    [
        ("!(+ 1 a)", "+", "evaluable", "a/0"),
        ("!(< 1 a)", "<", "evaluable", "a/0"),
        ("!(min-atom (a b))", "min-atom", "number", "a"),
        ("!(and true 5)", "and", "boolean", 5),
        ("!(reduce a)", "reduce", "list", "a"),
        ("!(change-state! (State 5) 6)", "change-state!", "atom", ["State", 5]),
    ],
)
def test_operation_error_carries_its_parts(metta, source, operation, expected, culprit):
    # The engine names the written operation in the error term, so the parts
    # arrive as data rather than as text a caller would have to parse.
    with pytest.raises(MettaOperationError) as failure:
        metta.run(source)
    assert failure.value.operation == operation
    assert failure.value.kind == "type_error"
    assert failure.value.expected == expected
    assert failure.value.culprit == culprit
    assert isinstance(failure.value, EngineError)
    assert "classifier failed" not in str(failure.value)


def test_engine_error_without_an_operation_stays_plain(metta):
    # A missing import carries an operation name in its context too, but it is
    # not a builtin refusing a value, so classification must not claim it.
    with pytest.raises(EngineError) as failure:
        metta.run('!(import! &self "definitely-not-here.metta")')
    assert not isinstance(failure.value, MettaOperationError)


def test_reserved_kinds_win_over_operation_classification(metta):
    with pytest.raises(MettaSyntaxError) as failure:
        metta.run("! (broken")
    assert not isinstance(failure.value, MettaOperationError)


def test_strict_refuses_a_typo_and_names_the_near_miss(m):
    m.run("(= (fact 0) 1)")
    with pytest.raises(StrictError) as failure:
        m.run("!(fct 5)", strict=True)
    assert failure.value.directive == 1
    assert str(failure.value.term) == "(fct 5)"
    assert "did you mean fact?" in str(failure.value)


def test_strict_refuses_an_empty_answer(m):
    m.run("(= (only-zero 0) yes)")
    with pytest.raises(StrictError) as failure:
        m.run("!(only-zero 0)\n!(only-zero 7)", strict=True)
    assert failure.value.directive == 2
    assert failure.value.term is None


@pytest.mark.parametrize(
    "source",
    [
        "!(+ 1 2)",
        "!(likes Ada Music)",  # stored data evaluating to itself is an answer
        "!(quote (+ 1 2))",
    ],
)
def test_strict_accepts_answers_that_are_not_silence(m, source):
    m.add(S.likes(S.Ada, S.Music))
    assert m.run(source, strict=True)


def test_strict_is_opt_in(m):
    # The default keeps every unreduced term, which is the point of the language.
    assert m.run("!(fct 5)") == [[parse("(fct 5)")]]


def test_eval_strict_refuses_silence(m):
    with pytest.raises(StrictError):
        m.eval(S.fct(5), strict=True)


def test_add_query_atoms(m):
    m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann))
    rows = m.query(S.Parent(V.x, S.Bob))
    assert rows.columns == ("x",)
    assert [r.x for r in rows] == [S.Tom]


def test_query_join(m):
    m.add(S.Edge(S.a, S.b), S.Edge(S.b, S.c), S.Edge(S.c, S.d))
    rows = m.query(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
    assert {(r.x, r.z) for r in rows} == {(S.a, S.c), (S.b, S.d)}


def test_query_projection_and_column(m):
    m.add(S.age(S.Ada, 36), S.age(S.Bob, 41))
    rows = m.query(S.age(V.who, V.years))
    assert set(rows.column("who")) == {S.Ada, S.Bob}
    assert sorted(rows.column("years"), key=int) == [36, 41]


def test_query_surfaces_share_column_order(m):
    patterns = (
        S.left(V.first, V.second, V.first, V._),
        S.right(V.third, V.second),
    )
    expected = ("first", "second", "third")
    assert m.query(*patterns).columns == expected
    assert m.prepare(*patterns).columns == expected
    with m.stream(*patterns) as cursor:
        assert cursor.columns == expected


def test_atoms_count_contains_remove_clear(m):
    m.add(S.item(1), S.item(2))
    assert m.count() == 2 and len(m) == 2
    assert S.item(1) in m
    assert S.item(3) not in m
    m.remove(S.item(1))
    assert m.count() == 1
    m.clear()
    assert m.count() == 0


def test_clear_removes_equations_too(m):
    m.add(parse("(= (clr-f) 77)"))
    assert m.run("!(clr-f)") == [[77]]
    m.clear()
    # The equation is gone: the call no longer reduces, it stays inert.
    assert m.run("!(clr-f)") == [[expr(S["clr-f"])]]


def test_eval(metta):
    assert metta.eval(S["car-atom"](expr(1, 2, 3))) == [1]
    assert metta.eval(S.superpose(expr(S.x, S.y))) == [S.x, S.y]
    assert metta.eval(expr(S["+"], 20, 22)) == [42]


def test_source_strings_are_parsed_where_atoms_are_expected(m):
    m.add("(likes Ada Coffee)")
    assert m.query("(likes $who Coffee)")[0].who == S.Ada


def test_parse_keeps_variable_names():
    p = parse("(Parent $x Bob)")
    assert p == S.Parent(V.x, S.Bob)


def test_parse_reads_booleans_the_way_the_engine_does():
    assert parse("True") == Gnd(True)
    assert parse("(a False)") == expr(S.a, False)


def test_live_object_identity(m):
    class Model:
        pass

    model = Model()
    m.add(S.model(S.main, val(model)))
    back = m.query(S.model(S.main, V.m))[0].m
    assert decode(back) is model


def test_boxed_container_identity(m):
    payload = {"weights": [1, 2]}
    m.add(S.blob(val(payload)))
    assert decode(m.query(S.blob(V.d))[0].d) is payload


def test_fact_isolation_between_spaces(metta):
    a, b = metta.fresh_space(), metta.fresh_space()
    a.add(S.fact(S.here))
    assert a.count() == 1
    assert b.count() == 0
    assert len(b.query(S.fact(V.x))) == 0


def test_default_metta_handles_share_the_self_space():
    first, second = MeTTa(), MeTTa()
    shared = S["shared-default-handle"](S.value)
    first.add(shared)
    try:
        assert shared in second
    finally:
        first.remove(shared)


def test_space_name_validation():
    with pytest.raises(ValueError):
        MeTTa("kb")


def test_load_runs_a_file(metta, tmp_path):
    f = tmp_path / "prog.metta"
    f.write_text("(= (loaded-f) 5)\n!(loaded-f)\n")
    groups = metta.load(str(f))
    assert groups == [[5]]


def test_load_adds_to_existing_space(m, tmp_path):
    path = tmp_path / "additive.metta"
    path.write_text("(loaded-copy value)\n")

    m.add(S.existing(S.value))
    m.load(path)
    m.load(path)

    assert m.count() == 3
    assert len(m.query(S["loaded-copy"](V.value))) == 2


def test_why(m):
    m.add(S.Parent(S.Tom, S.Bob))
    text = m.why(S.Parent(S.Nobody, V.x))
    assert "none unifies" in text
    assert "Missing" in m.why(S.Missing(V.x))
    m.add(S.Parent(S.a, S.b, S.c))
    assert "elements" in m.why(S.Parent(V.x,))
    assert "did you mean car-atom?" in m.why(S["car-atmo"](S.value))


def test_match_patterns_are_structural(m):
    """The engine's own rule: match evaluates its space and its body, never
    the pattern. A function call written inside a pattern is data there."""
    m.add(S.pair(S.small, S.yes))
    m.run("(= (sz-here) small)")
    # The evaluated idiom: compute first, then match the value.
    assert m.run("!(let $s (sz-here) (match (context-space) (pair $s $v) $v))") == [[S.yes]]
    # The literal idiom: the pattern (pair (sz-here) $v) matches nothing,
    # because no stored atom is literally shaped that way.
    assert m.run("!(collapse (match (context-space) (pair (sz-here) $v) $v))") == [[expr()]]


def test_bare_atoms_are_refused_loudly(m):
    """A stored atom is a non-empty expression; anything else must error,
    never vanish: the silent write was a real bug this pins."""
    with pytest.raises(TypeError):
        m.add(S.bare)
    with pytest.raises(TypeError):
        m.add(7)
    with pytest.raises(TypeError, match="non-empty expression"):
        m.add(expr())
    with pytest.raises(TypeError, match="non-empty expression"):
        m.remove(expr())


def test_remove_reports_presence_and_removes_every_duplicate(m):
    atom = S.duplicate(S.value)

    assert m.remove(atom) is False
    m.add(atom, atom)
    assert m.remove(atom) is True
    assert atom not in m
    assert m.remove(atom) is False


def test_object_identity_survives_the_boundary(m):
    """One live object is one box everywhere: stored, found, removed."""
    class Thing:
        pass

    thing = Thing()
    m.add(S.holds(val(thing)))
    assert S.holds(val(thing)) in m
    rows = m.query(S.holds(V.x))
    assert rows[0].x.value is thing
    assert m.remove(S.holds(val(thing))) is True
    assert S.holds(val(thing)) not in m


def test_anonymous_variables_do_not_join(m):
    """Two underscores are two fresh variables, exactly as parsed $_ $_."""
    m.add(S.duo(S.a, S.a), S.duo(S.a, S.b))
    assert len(m.query(S.duo(V._, V._))) == 2
    # And the anonymous variable never becomes a column.
    assert m.query(S.duo(V.x, V._)).columns == ("x",)


def test_fresh_spaces_drop_and_names_recycle(metta):
    """A dropped space's name returns to the pool, so churn does not grow
    the engine's module table; the with-block is the drop."""
    with metta.fresh_space() as scratch:
        first = scratch.space_name
        scratch.add(S.noted(S.here))
        assert len(scratch) == 1
    with metta.fresh_space() as again:
        assert again.space_name == first
        assert len(again) == 0
    with pytest.raises(TypeError):
        with metta:
            pass


def test_load_restores_the_working_directory(metta, tmp_path):
    """One load resolves its imports from its own directory and puts the
    process's directory back afterwards, so later runs are untouched."""
    inner = tmp_path / "prog.metta"
    inner.write_text("!(+ 1 1)\n")
    before = petta.janus.query_once("working_dir(D)")
    metta.load(str(inner))
    after = petta.janus.query_once("working_dir(D)")
    assert (before or {}).get("D") == (after or {}).get("D")


def test_runtime_refuses_a_second_tree(metta):
    with pytest.raises(ValueError):
        MeTTa(petta_path="/definitely/not/this/tree")


def test_a_dropped_handle_cannot_write_into_the_name_it_released(metta):
    # fresh_space() pools names, so a live handle to a dropped space would
    # otherwise write into whatever space took the name next.
    dead = metta.fresh_space()
    released = dead.space_name
    dead.drop()
    reused = metta.fresh_space()
    assert reused.space_name == released
    with pytest.raises(PettaError) as failure:
        dead.add(S.ghost(1))
    assert "was dropped" in str(failure.value)
    assert reused.count() == 0
    dead.drop()  # idempotent, as closing twice is
    assert "dropped" in repr(dead)


def test_add_table_reads_records_by_value(m):
    m.add(S.p(S.a, S.b))
    rows = m.query(S.p(V.x, V.y))
    records = m.fresh_space()
    records.add_table(S.p, rows.to_dicts())
    # Iterating a mapping yields keys, so this once stored ("x" "y").
    assert [str(atom) for atom in records.atoms()] == ['(p "a" "b")']
    lossless = m.fresh_space()
    lossless.add_table(S.p, {c: rows.column(c) for c in rows.columns})
    assert lossless.digest() == m.digest()


def test_add_table_refuses_records_whose_key_order_drifts(m):
    with pytest.raises(ValueError, match="same keys in the same order"):
        m.add_table(S.p, [{"x": 1, "y": 2}, {"y": 3, "x": 4}])


def test_the_empty_symbol_is_refused_rather_than_written_unreadably(m, tmp_path):
    m.add(S.t(S[""], 1))
    target = tmp_path / "empty.metta"
    with pytest.raises(ValueError, match="empty symbol"):
        m.save(str(target))
    assert not target.exists()


@pytest.mark.parametrize("guard", [123, "oops", 4.5, S.oops])
def test_a_where_guard_that_can_never_be_true_is_refused(m, guard):
    m.add(S.age(S.Ada, 36))
    with pytest.raises(TypeError, match="can never answer true"):
        m.query(S.age(V.who, V.n), where=guard)


def test_wrong_bound_types_name_the_argument(m):
    with pytest.raises(TypeError, match="limit must be"):
        m.query(S.age(V.who, V.n), limit="x")
    with pytest.raises(TypeError, match="timeout must be"):
        m.run("!(+ 1 2)", timeout="x")
    with pytest.raises(TypeError, match="inferences must be"):
        m.run("!(+ 1 2)", inferences="x")
    with pytest.raises(TypeError, match="space name is a string"):
        MeTTa(123)


def test_a_reserved_limit_does_not_leak_janus_framing(metta):
    metta.run("(= (spin $n) (spin (+ $n 1)))")
    with pytest.raises(TimeLimitError) as failure:
        metta.run("!(spin 0)", timeout=0.05)
    assert "0.05 second time limit" in str(failure.value)
    assert "Unknown error term" not in str(failure.value)
    assert "petta_py_exception" not in str(failure.value)


def test_build_never_hands_back_its_private_sentinel(m):
    m.add(S.p(S.a))
    rows = m.query(S.p(V.x))
    assert petta.convert.build(S.a, str) == S.a
    assert rows.build("x", str) == [S.a]


def test_a_provider_error_is_not_a_system_error(metta):
    class Exploding(SpaceProvider):
        def atoms(self):
            raise RuntimeError("provider exploded")

    register_provider(_engine.runtime(), "&exploding_probe", Exploding())
    try:
        with pytest.raises(EngineError) as failure:
            metta.space("&exploding_probe").atoms()
        # A generator body runs at the first pull, inside py_iter, where an
        # exception surfaces as SystemError naming apply_once.
        assert not isinstance(failure.value, SystemError)
        assert "provider exploded" in str(failure.value)
    finally:
        unregister_provider(_engine.runtime(), "&exploding_probe")


def test_a_provider_without_the_interface_is_refused_at_registration():
    class NotAProvider:
        def match(self, pattern):
            return iter(())

    with pytest.raises(TypeError, match="can_run"):
        register_provider(_engine.runtime(), "&not_a_provider", NotAProvider())


def test_removing_what_was_never_registered_is_reported(metta):
    with pytest.raises(KeyError):
        metta.unregister_op("no-such-operation-anywhere")
    with pytest.raises(KeyError):
        unregister_provider(_engine.runtime(), "&no_such_provider")


def test_an_unknown_column_names_the_columns_that_exist(m):
    m.add(S.p(S.a))
    rows = m.query(S.p(V.who))
    with pytest.raises(KeyError, match="did you mean 'who'"):
        rows.column("wh")


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda m: m.run(None), "source as a string"),
        (lambda m: m.is_function(None), "name as a string"),
        (lambda m: m.is_function_here(1), "name as a string"),
    ],
)
def test_a_wrong_argument_type_names_the_argument(m, call, match):
    with pytest.raises(TypeError, match=match):
        call(m)
