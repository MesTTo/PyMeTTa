"""Purpose: what the library-evaluation batch shipped, engine-backed: term
building operators over the whole engine-evaluable algebra, declarations
generalised (TypeVars, Unions superposing, Callable arrows, tuple shapes,
classes as declared types), guarded and bounded queries, assumptions,
prepared queries, general weighted relations, goal-directed soft proving with Proof objects, and
the &petta reflection space the library describes itself into.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import dataclasses
from collections.abc import Callable, Sequence
from typing import Annotated, Generic, TypeVar

import pytest

from petta import REFLECTION_SPACE, Answer, MeTTa, S, V, alpha_eq, expr, val
from petta.atoms import Expr, Gnd, Var
from petta.ops import referenced_classes, type_atoms_for


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
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
    assert (V.x**2) == expr(S["pow-math"], V.x, 2)
    assert (V.a @ V.b) == expr(S["matmul"], V.a, V.b)


def test_boolean_operators_compose_guards():
    guard = (V.age >= 18) & (V.age <= 40)
    assert guard == expr(S["and"], expr(S[">="], V.age, 18), expr(S["<="], V.age, 40))
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


def test_a_grounded_bool_is_falsey_and_nothing_else_is(m):
    """PEP 8 says write `if greeting:` rather than `greeting == True`, and
    without this the conformant spelling reads a MeTTa False as true: a user
    who tidies away the `# noqa: E712` gets a silent wrong answer."""
    m.run("(= (adult $a) (> $a 18))")
    answers = m.eval("(adult 5)")
    assert answers == [False]
    assert not any(answer for answer in answers)
    assert any(answer for answer in m.eval("(adult 21)"))

    assert bool(Gnd(True)) is True
    assert bool(Gnd(False)) is False
    # A Number 0 is not falsehood in MeTTa, and neither is an empty string
    # or an empty host container carried whole.
    assert all(bool(Gnd(value)) for value in (0, 0.0, "", [], None))


# ------------------------------------------------- generalised declarations


def test_typevar_annotations_declare_parametrically(m):
    A = TypeVar("A")

    @m.register_op(name="first-of")
    def first_of(items: Sequence[A]) -> A:
        return items[0]

    declaration = expr(S[":"], S["first-of"], expr(S["->"], S.Expression, Var("a")))
    assert any(alpha_eq(a, declaration) for a in m.atoms())
    assert m.run("!(first-of (7 8 9))") == [[7]]


def test_union_annotations_superpose_declarations(m):

    @m.register_op(name="describe")
    def describe(x: int | str) -> str:
        return f"<{x}>"

    assert _arrows_of(m, "describe") == {
        "(-> Number String)",
        "(-> String String)",
    }
    assert m.run("!(describe 7)") == [["<7>"]]
    assert m.run('!(describe "a")') == [["<a>"]]
    # Outside the union the checker answers nothing, its own rejection.
    # One rejection per declared arrow, arrow-major, which is the arbiter's own
    # multiplicity [measured 2026-08-19: the same two errors in the same order].
    assert [str(a) for a in m.run("!(describe (1 2))")[0]] == [
        "(Error (describe (1 2)) (BadArgType 1 Number (Number Number)))",
        "(Error (describe (1 2)) (BadArgType 1 String (Number Number)))",
    ]


def test_optional_return_declares_the_value_type(m):

    @m.register_op(name="lookup-age")
    def lookup_age(name: str) -> int | None:
        return {"ada": 36}.get(name)

    # Returning None answers nothing, so the declared return is Number.
    assert _arrows_of(m, "lookup-age") == {"(-> String Number)"}
    assert m.run('!(lookup-age "ada")') == [[36]]
    assert m.run('!(lookup-age "bob")') == [[]]


def test_callable_and_tuple_annotations_declare_structurally(m):
    @m.register_op(name="fixed-point-of")
    def fixed_point_of(f: Callable[[int], int]) -> int:
        raise NotImplementedError

    assert _arrows_of(m, "fixed-point-of") == {"(-> (-> Number Number) Number)"}

    @m.register_op(name="swap")
    def swap(pair: tuple[int, str]) -> tuple[str, int]:
        a, b = pair
        return (b, a)

    assert _arrows_of(m, "swap") == {"(-> (Number String) (String Number))"}
    assert m.run('!(swap (7 "x"))') == [[expr("x", 7)]]


def test_class_annotations_declare_the_class(m):
    @dataclasses.dataclass
    class Particle:
        mass: float
        velocity: float

    @m.register_op(name="momentum")
    def momentum(p: Particle) -> float:
        return p.mass * p.velocity

    assert _arrows_of(m, "momentum") == {"(-> Particle Number)"}
    # The referenced class became a declared type, constructor arrow typed
    # from its field annotations.
    assert _arrows_of(m, "Particle") == {"(-> Number Number Particle)"}
    assert m.eval(S.momentum(val(Particle(2.0, 3.0)))) == [6.0]


def test_type_decorator_declares_field_types(m):
    @m.type
    @dataclasses.dataclass
    class DeclaredPoint:
        x: float
        y: float

    assert _arrows_of(m, "DeclaredPoint") == {"(-> Number Number DeclaredPoint)"}


# --------------------------------------------------- guarded bounded query


def test_query_where_guard_and_limit(m):
    m.add(
        S.person(S.ada, 36),
        S.person(S.bob, 12),
        S.person(S.cyd, 70),
    )
    adults = m.query(S.person(V.name, V.age), where=V.age >= 18)
    assert {str(r.name) for r in adults} == {"ada", "cyd"}
    # Guards compose with the boolean operators, the engine reading them.
    mid = m.query(S.person(V.name, V.age), where=(V.age >= 18) & (V.age <= 40))
    assert {str(r.name) for r in mid} == {"ada"}
    assert len(m.query(S.person(V.name, V.age), limit=2)) == 2
    with pytest.raises(ValueError):
        m.query(S.person(V.name, V.age), limit=0)


# ------------------------------------------------------------- assumptions


def test_assuming_scopes_facts(m):
    m.add(S.road(S.a, S.b))
    with m.assuming(S.road(S.b, S.c)):
        assert len(m.query(S.road(V.x, V.y))) == 2
    assert len(m.query(S.road(V.x, V.y))) == 1
    # The exception path removes too.
    try:
        with m.assuming(S.road(S.b, S.c)):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert len(m.query(S.road(V.x, V.y))) == 1


# --------------------------------------------------------- prepared queries


def test_prepared_query_with_given(m):
    m.add(S.edge(S.a, S.b))
    hop = m.prepare(S.edge(V.x, V.y))
    assert hop.columns == ("x", "y")
    assert len(hop.solve()) == 1
    # given= facts exist for this call alone.
    assert len(hop.solve(given=[S.edge(S.b, S.c)])) == 2
    assert len(hop.solve()) == 1
    guarded = m.prepare(S.edge(V.x, V.y), where=V.x.eq(S.a))
    assert len(guarded.solve(given=[S.edge(S.b, S.c)])) == 1


# ------------------------------------------------------- weighted relations


def test_a_weighted_relation_is_an_annotated_op(m):
    # DeepProbLog's nn-predicate shape through the general seam: the op
    # answers its classes, each weight riding as the answer's annotation,
    # declared like any context; top orders, (annotation) reads.
    def mood(day):
        yield Answer(value=S.calm, k=0.25)
        yield Answer(value=S.tense, k=0.75)

    m.register_op(mood, name="mood", typed=False)
    m.declare_annotations("mood", "prob")
    (classes,) = m.run("!(collapse (mood today))")[0]
    assert [str(c) for c in classes] == ["calm", "tense"]
    (best,) = m.run("!(collapse (top 1 (mood today)))")[0]
    assert list(best.children) == [S.tense]
    (weighted,) = m.run(
        "!(collapse (let $c (mood today) (pair (annotation) $c)))"
    )[0]
    assert [(p.children[1].value, str(p.children[2])) for p in weighted.children] == [
        (0.25, "calm"),
        (0.75, "tense"),
    ]


# --------------------------------------------------------- reflection space


def test_the_library_reflects_into_its_own_space(m):
    reflection = MeTTa(REFLECTION_SPACE)

    @m.register_op(name="reflect-probe")
    def reflect_probe(x: int) -> int:
        return x

    rows = reflection.query(S.op(S["reflect-probe"], V.arity, V.kind))
    assert [(r.arity, str(r.kind)) for r in rows] == [(1, "det")]
    m.unregister_op("reflect-probe")
    assert not reflection.query(S.op(S["reflect-probe"], V.arity, V.kind))

    @m.define(name="probe-twice")
    def probe_twice(x):
        return x + x

    assert reflection.query(S.defined(S[m.space_name], S["probe-twice"]))

    sub = m.subscribe(S.road(V.a, V.b))
    watched = reflection.query(S.subscription(S[m.space_name], V.p, V.on))
    assert len(watched) == 1 and str(watched[0].on) == "add"
    sub.cancel()
    assert not reflection.query(S.subscription(S[m.space_name], V.p, V.on))


def test_reflection_facts_follow_a_dropped_space(metta):
    reflection = MeTTa(REFLECTION_SPACE)
    space = metta.new_space()

    @space.define
    def fleeting(x):
        return x

    name = space.space_name
    assert reflection.query(S.defined(S[name], S.fleeting))
    space.drop()
    assert not reflection.query(S.defined(S[name], S.fleeting))


def test_metta_programs_steer_through_the_reflection_space(m):
    """Deeper control without forking: a Python subscription on &petta
    reacts to control atoms a MeTTa program writes there."""
    reflection = MeTTa(REFLECTION_SPACE)
    seen = []
    sub = reflection.subscribe(S.control(V.knob, V.value), lambda e: seen.append(e))
    try:
        m.run("!(add-atom &petta (control verbosity 2))")
        assert len(seen) == 1
        assert seen[0].bindings["knob"] == S.verbosity
        assert seen[0].bindings["value"] == 2
    finally:
        sub.cancel()
        reflection.remove(S.control(S.verbosity, 2))


def test_drop_cancels_the_spaces_subscriptions(metta):
    reflection = MeTTa(REFLECTION_SPACE)
    space = metta.new_space()
    name = space.space_name
    seen = []
    subscription = space.subscribe(S.ping(V.x), lambda e: seen.append(e))
    assert reflection.query(S.subscription(S[name], V.p, V.on))
    space.drop()
    # The watcher died with its space: inactive, and its reflection fact
    # removed, so a pooled name reused later starts unwatched.
    assert subscription._active is False
    assert not reflection.query(S.subscription(S[name], V.p, V.on))


def test_shared_class_declarations_survive_one_unregister(m):
    @dataclasses.dataclass
    class SharedReview:
        stars: float

    @m.register_op(name="rate-one")
    def rate_one(r: SharedReview) -> float:
        return r.stars

    @m.register_op(name="rate-two")
    def rate_two(r: SharedReview) -> float:
        return r.stars * 2

    constructor = "(-> Number SharedReview)"
    assert _arrows_of(m, "SharedReview") == {constructor}
    m.unregister_op("rate-one")
    # The other owner still declares the class.
    assert _arrows_of(m, "SharedReview") == {constructor}
    m.unregister_op("rate-two")
    assert _arrows_of(m, "SharedReview") == set()


def test_registration_failure_leaves_nothing_half_registered(m):
    class Unresolvable:
        pass

    def bad(x: "NoSuchName") -> int:  # noqa: F821
        return 1

    with pytest.raises(TypeError):
        m.register_op(bad, name="bad-op")
    reflection = MeTTa(REFLECTION_SPACE)
    assert not reflection.query(S.op(S["bad-op"], V.a, V.k))
    assert not m.is_function("bad-op")
    assert _arrows_of(m, "bad-op") == set()


# `from __future__ import annotations` makes every annotation a STRING, which
# is the default in a growing number of codebases and will be the default
# outright. A declaration generator reading the raw __annotations__ sees "int"
# rather than int and declares nothing useful, so the resolution has to happen
# before the atoms are built.
def test_postponed_annotations_generate_declarations(m):
    namespace: dict = {}
    exec(
        "from __future__ import annotations\n"
        "def widen(count: int, label: str) -> str:\n"
        "    return label * count\n",
        namespace,
    )
    widen = namespace["widen"]
    assert widen.__annotations__["count"] == "int"

    m.register_op(widen, name="widen-op")
    assert _arrows_of(m, "widen-op") == {"(-> Number String String)"}
    assert m.run('!(widen-op 2 "ab")') == [["abab"]]


def test_union_expansion_is_bounded(m):
    U = int | str | bool

    # Five inputs plus the return type produce 3**6 alternatives, over 512.
    def wide(a: U, b: U, c: U, d: U, e: U) -> U:
        return a

    with pytest.raises(TypeError):
        m.register_op(wide, name="wide-op")
    assert not m.is_function("wide-op")


def test_annotated_and_generic_annotations_map_faithfully(m):
    class Meta:
        pass

    T = TypeVar("T")

    class GenericBox(Generic[T]):
        pass

    assert [str(a) for a in type_atoms_for(Annotated[int, Meta])] == ["Number"]
    assert [str(a) for a in type_atoms_for(GenericBox[int])] == ["GenericBox"]
    referenced = referenced_classes([Annotated[int, Meta], GenericBox[int]])
    assert GenericBox in referenced and Meta not in referenced
