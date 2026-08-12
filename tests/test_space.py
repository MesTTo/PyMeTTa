"""Purpose: engine-backed tests for the MeTTa runtime surface: run, load,
space edits, queries, eval, parse, and the semantics matching the CLI's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import EngineError, MettaSyntaxError, S, V, decode, expr, parse, val
from petta.atoms import Gnd, Sym


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
    with pytest.raises(MettaSyntaxError):
        metta.run("! (broken")


def test_run_unknown_function_error_is_loud(metta):
    # An undefined head inside arithmetic is a hard engine error, exactly as
    # the CLI dies on it; nothing is swallowed.
    with pytest.raises(EngineError):
        metta.run("!(+ 1 (no-such-function-anywhere 2))")


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


def test_space_name_validation():
    from petta import MeTTa

    with pytest.raises(ValueError):
        MeTTa("kb")


def test_load_runs_a_file(metta, tmp_path):
    f = tmp_path / "prog.metta"
    f.write_text("(= (loaded-f) 5)\n!(loaded-f)\n")
    groups = metta.load(str(f))
    assert groups == [[5]]


def test_why(m):
    m.add(S.Parent(S.Tom, S.Bob))
    text = m.why(S.Parent(S.Nobody, V.x))
    assert "none unifies" in text
    assert "Missing" in m.why(S.Missing(V.x))
    m.add(S.Parent(S.a, S.b, S.c))
    assert "elements" in m.why(S.Parent(V.x,))
