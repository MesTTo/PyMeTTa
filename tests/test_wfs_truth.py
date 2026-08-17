"""Purpose: the third truth value crosses whole. An answer that is
undefined under Well Founded Semantics reaches Python as Undefined with
its delay condition, residual programs fill on request, definite answers
stay plain atoms, and value() refuses to pretend an undefined answer is
a value. Before this surface, such answers arrived as ordinary-looking
unbound variables with wrapper truth True, the silently wrong shape
ai-tabling-review.md section 3 pinned.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

import petta as pkg
from petta import EngineError, PettaError
from petta.atoms import Undefined


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
        yield space


@pytest.fixture(scope="module")
def wfs_program(metta):
    pkg.janus.consult(
        "wfs_truth_test.pl",
        data=(
            ":- table wfs_loop/0.\n"
            "wfs_loop :- tnot(wfs_loop).\n"
            ":- table wfs_mixed/1.\n"
            "wfs_mixed(1).\n"
            "wfs_mixed(2) :- tnot(wfs_loop).\n"
        ),
    )
    return True


def test_undefined_answers_cross_as_undefined(m, wfs_program):
    answers = m.eval("(translatePredicate (wfs_loop))")
    assert len(answers) == 1
    answer = answers[0]
    assert isinstance(answer, Undefined)
    assert "wfs_loop" in answer.why
    assert answer.residual is None
    with pytest.raises(PettaError, match="undefined"):
        bool(answer)


def test_mixed_answers_keep_definite_ones_plain(m, wfs_program):
    answers = m.eval("(translatePredicate (wfs_mixed $x))")
    assert len(answers) == 2
    undefined = [a for a in answers if isinstance(a, Undefined)]
    definite = [a for a in answers if not isinstance(a, Undefined)]
    assert len(undefined) == 1 and len(definite) == 1
    # The delay names the conditional subgoal itself, the engine's own
    # granularity for the condition.
    assert "wfs_mixed(2)" in undefined[0].why


def test_residuals_fill_on_request(m, wfs_program):
    (answer,) = m.eval("(translatePredicate (wfs_loop))", residuals=True)
    assert isinstance(answer, Undefined)
    assert answer.residual is not None
    assert "tnot" in answer.residual


def test_value_refuses_undefined_truth(m, wfs_program):
    with pytest.raises(EngineError, match="undefined truth"):
        m.value("(translatePredicate (wfs_loop))")


def test_ordinary_evaluation_stays_plain(m):
    answers = m.eval("(+ 1 2)")
    assert answers == [3]
    assert not isinstance(answers[0], Undefined)
