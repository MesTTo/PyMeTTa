"""Purpose: the multi-shot functor, engine-backed: externals toggling truth
between solves, released externals refusing assignment, parts grounding
once per instantiation, and the incremental deepening loop the vocabulary
exists for.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, multishot


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_externals_toggle_truth_between_solves(m):
    lamp = multishot.external(m, S.on(S.lamp))
    assert lamp.value is False
    assert m.query(S.on(V.x)) == []

    lamp.assign(True)
    assert [str(r.x) for r in m.query(S.on(V.x))] == ["lamp"]
    lamp.assign(True)  # idempotent, no duplicate
    assert len(m.query(S.on(V.x))) == 1

    lamp.assign(False)
    assert m.query(S.on(V.x)) == []


def test_released_externals_refuse_assignment(m):
    lamp = multishot.external(m, S.on(S.lamp))
    lamp.assign(True)
    lamp.release()
    assert m.query(S.on(V.x)) == []
    assert lamp.released
    lamp.release()  # releasing again is quiet, as in clingo
    with pytest.raises(RuntimeError):
        lamp.assign(True)


def test_parts_ground_once_per_instantiation(m):
    m.add(S.edge(S.a, S.b), S.edge(S.b, S.c))
    m.run("(= (reach a 0) True)")
    step = multishot.part(
        m,
        "step",
        lambda t: f"(= (reach $x {t}) (match (context-space) (edge $y $x) "
                  f"(once (reach $y {t - 1}))))",
    )
    step.ground(1)
    step.ground(2)
    assert step.grounded() == {(1,), (2,)}
    with pytest.raises(RuntimeError):
        step.ground(1)
    # The deepening loop: b is reachable at step 1, c only at step 2.
    assert any(a == True for a in m.eval(m.parse("(reach b 1)")))  # noqa: E712
    assert not any(a == True for a in m.eval(m.parse("(reach c 1)")))  # noqa: E712
    assert any(a == True for a in m.eval(m.parse("(reach c 2)")))  # noqa: E712


def test_parts_take_atom_templates(m):
    fleet = multishot.part(
        m, "fleet", lambda n: [S.ship(i) for i in range(n)]
    )
    fleet.ground(3)
    assert len(m.query(S.ship(V.i))) == 3
    with pytest.raises(TypeError):
        multishot.part(m, "bad", lambda: 7).ground()


def test_the_incremental_solving_loop(m):
    """clingo's ground-solve-extend loop: extend the horizon until the
    query proves, the multi-shot reading of iterative deepening."""
    # Tabular facts: cells encode as the values they are, so symbols are
    # spelled as symbols (a text cell would store a grounded string).
    m.add_table("edge", [(S.a, S.b), (S.b, S.c), (S.c, S.d)])
    m.run("(= (reach a 0) True)")
    step = multishot.part(
        m,
        "step",
        lambda t: f"(= (reach $x {t}) (match (context-space) (edge $y $x) "
                  f"(once (reach $y {t - 1}))))",
    )
    def proved(t: int) -> bool:
        answers = m.eval(m.parse(f"(reach d {t})"))
        return any(a == True for a in answers)  # noqa: E712

    horizon = 0
    while not proved(horizon):
        horizon += 1
        step.ground(horizon)
        assert horizon < 10
    assert horizon == 3
