"""Purpose: what the library-evaluation batch shipped, engine-backed: term
building operators over the whole engine-evaluable algebra.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, expr
from petta.atoms import Gnd


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


# ------------------------------------------------------- operator building


def test_operators_build_terms_on_variables_and_symbols():
    assert (V.age >= 18) == expr(S[">="], V.age, 18)
    assert (V.x + 1) == expr(S["+"], V.x, 1)
    assert (2 * V.x) == expr(S["*"], 2, V.x)
    assert (V.x + 1 <= V.y) == expr(S["<="], expr(S["+"], V.x, 1), V.y)
    assert V.x.eq(3) == expr(S["=="], V.x, 3)
    assert (V.a % 2) == expr(S["%"], V.a, 2)
    assert (V.x ** 2) == expr(S["pow-math"], V.x, 2)
    assert (V.a @ V.b) == expr(S["matmul"], V.a, V.b)


def test_boolean_operators_compose_guards():
    guard = (V.age >= 18) & (V.age <= 40)
    assert guard == expr(
        S["and"], expr(S[">="], V.age, 18), expr(S["<="], V.age, 40)
    )
    assert (V.a | V.b) == expr(S["or"], V.a, V.b)
    assert (V.a ^ V.b) == expr(S["xor"], V.a, V.b)
    assert ~V.ok == expr(S["not"], V.ok)


def test_grounded_values_keep_value_semantics():
    assert Gnd(3) + 1 == 4
    assert Gnd(3) * Gnd(4) == 12
    assert 10 - Gnd(4) == 6
    assert Gnd(2) ** 10 == 1024
    assert Gnd(6) & 3 == 2
    assert Gnd(5) ^ 1 == 4
    assert ~Gnd(0) == -1
    assert (Gnd(7) >= 5) is True  # a boolean, never a term


def test_comparison_terms_refuse_truthiness():
    with pytest.raises(TypeError):
        bool(V.a < V.b)
    with pytest.raises(TypeError):
        sorted([V.a, V.b])
    with pytest.raises(TypeError):
        bool((V.a >= 1) & (V.b >= 2))
