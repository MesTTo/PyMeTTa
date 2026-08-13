"""Purpose: what the library-evaluation batch shipped, engine-backed: term
building operators over the whole engine-evaluable algebra, and
declarations generalised (TypeVars, Unions superposing, Callable arrows,
tuple shapes, classes as declared types).
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, expr
from petta.atoms import Expr, Gnd, Var


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def _arrows_of(space, name):
    """Every (-> ...) a space declares for a name, as strings."""
    out = set()
    for atom in space.atoms():
        if (
            isinstance(atom, Expr)
            and len(atom) == 3
            and atom.head == S[":"]
            and atom[1] == S[name]
        ):
            out.add(str(atom[2]))
    return out


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


# ------------------------------------------------- generalised declarations


def test_typevar_annotations_declare_parametrically(m):
    from typing import Sequence, TypeVar

    A = TypeVar("A")

    @m.op(name="first-of")
    def first_of(items: Sequence[A]) -> A:
        return items[0]

    declaration = expr(
        S[":"], S["first-of"], expr(S["->"], S.Expression, Var("a"))
    )
    from petta import alpha_eq

    assert any(alpha_eq(a, declaration) for a in m.atoms())
    assert m.run("!(first-of (7 8 9))") == [[7]]


def test_union_annotations_superpose_declarations(m):
    from typing import Union

    @m.op(name="describe")
    def describe(x: Union[int, str]) -> str:
        return f"<{x}>"

    assert _arrows_of(m, "describe") == {
        "(-> Number String)",
        "(-> String String)",
    }
    assert m.run("!(describe 7)") == [["<7>"]]
    assert m.run('!(describe "a")') == [["<a>"]]
    # Outside the union the checker answers nothing, its own rejection.
    assert m.run("!(describe (1 2))") == [[]]


def test_optional_return_declares_the_value_type(m):
    from typing import Optional

    @m.op(name="lookup-age")
    def lookup_age(name: str) -> Optional[int]:
        return {"ada": 36}.get(name)

    # Returning None answers nothing, so the declared return is Number.
    assert _arrows_of(m, "lookup-age") == {"(-> String Number)"}
    assert m.run('!(lookup-age "ada")') == [[36]]
    assert m.run('!(lookup-age "bob")') == [[]]


def test_callable_and_tuple_annotations_declare_structurally(m):
    from typing import Callable

    @m.op(name="fixed-point-of")
    def fixed_point_of(f: Callable[[int], int]) -> int:
        raise NotImplementedError

    assert _arrows_of(m, "fixed-point-of") == {"(-> (-> Number Number) Number)"}

    @m.op(name="swap")
    def swap(pair: tuple[int, str]) -> tuple[str, int]:
        a, b = pair
        return (b, a)

    assert _arrows_of(m, "swap") == {"(-> (Number String) (String Number))"}
    assert m.run('!(swap (7 "x"))') == [[expr("x", 7)]]


def test_class_annotations_declare_the_class(m):
    import dataclasses

    from petta import val

    @dataclasses.dataclass
    class Particle:
        mass: float
        velocity: float

    @m.op(name="momentum")
    def momentum(p: Particle) -> float:
        return p.mass * p.velocity

    assert _arrows_of(m, "momentum") == {"(-> Particle Number)"}
    # The referenced class became a declared type, constructor arrow typed
    # from its field annotations.
    assert _arrows_of(m, "Particle") == {"(-> Number Number Particle)"}
    assert m.eval(S.momentum(val(Particle(2.0, 3.0)))) == [6.0]


def test_type_decorator_declares_field_types(m):
    import dataclasses

    @m.type
    @dataclasses.dataclass
    class Point:
        x: float
        y: float

    assert _arrows_of(m, "Point") == {"(-> Number Number Point)"}
