"""Purpose: what the library-evaluation batch shipped, engine-backed: term
building operators over the whole engine-evaluable algebra, declarations
generalised (TypeVars, Unions superposing, Callable arrows, tuple shapes,
classes as declared types), guarded and bounded queries, assumptions,
prepared queries, general weighted relations, goal-directed soft proving with Proof objects, and
the &petta reflection space the library describes itself into.
Guarantees:
  - all rich comparisons order atoms while explicit symbolic heads retain
    truthiness-refusing comparison terms [tested:
    test_rich_comparisons_order_atoms_and_explicit_terms_refuse_truthiness;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - grounded atoms stage operators while their explicit value and conversion
    doors retain host-value semantics [tested:
    test_grounded_atoms_keep_values_but_stage_operators; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - Python classes declare through ``Space.define`` [tested:
    test_define_decorator_declares_field_types; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - an unannotated weighted operation stays untyped without a typed flag
    [tested: test_a_weighted_relation_is_an_annotated_op; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import dataclasses
from collections.abc import Callable, Sequence
from typing import Annotated, Generic, TypeVar

import pytest

from metta import Answer, Expression, S, V, ground
from metta import reflection as catalog
from metta.atoms import Grounded, Variable
from metta.ops import referenced_classes, type_atoms_for


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def _arrows_of(space, name):
    """Every (-> ...) a space declares for a name, as strings."""
    out = set()
    for atom in space.atoms():
        if (
            isinstance(atom, Expression)
            and len(atom) == 3
            and atom.head == S[":"]
            and atom[1] == S[name]
        ):
            out.add(str(atom[2]))
    return out


# ------------------------------------------------------- operator building


def test_operators_build_terms_on_variables_and_symbols():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert (V.x + 1) == Expression(S["+"], V.x, 1)
    assert (2 * V.x) == Expression(S["*"], 2, V.x)
    assert V.x.eq(3) == Expression(S["=="], V.x, 3)
    assert (V.a % 2) == Expression(S["%"], V.a, 2)
    assert (V.x**2) == Expression(S["pow-math"], V.x, 2)
    assert (V.a @ V.b) == Expression(S["matmul"], V.a, V.b)


def test_boolean_operators_compose_guards():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    guard = S[">="](V.age, 18) & S["<="](V.age, 40)
    assert guard == Expression(S["and"], Expression(S[">="], V.age, 18), Expression(S["<="], V.age, 40))
    assert (V.a | V.b) == Expression(S["or"], V.a, V.b)
    assert (V.a ^ V.b) == Expression(S["xor"], V.a, V.b)
    assert ~V.ok == Expression(S["not"], V.ok)


def test_grounded_atoms_keep_values_but_stage_operators():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert Grounded(3) + 1 == Expression(S["+"], 3, 1)
    assert Grounded(3) * Grounded(4) == Expression(S["*"], 3, 4)
    assert 10 - Grounded(4) == Expression(S["-"], 10, 4)
    assert Grounded(2) ** 10 == Expression(S["pow-math"], 2, 10)
    assert Grounded(6) & 3 == Expression(S["and"], 6, 3)
    assert Grounded(5) ^ 1 == Expression(S["xor"], 5, 1)
    assert ~Grounded(0) == Expression(S["not"], 0)
    assert (Grounded(7) >= 5) is True  # a boolean, never a term
    assert Grounded(7).value == 7
    assert int(Grounded(7)) == 7


def test_rich_comparisons_order_atoms_and_explicit_terms_refuse_truthiness():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert V.a < V.b and V.a <= V.b and V.b > V.a and V.b >= V.a
    assert sorted([V.b, V.a]) == [V.a, V.b]
    with pytest.raises(TypeError):
        bool(S["<"](V.a, V.b))
    with pytest.raises(TypeError):
        bool(S[">="](V.a, 1) & S[">="](V.b, 2))


def test_a_grounded_bool_is_falsey_and_nothing_else_is(m):
    """PEP 8 says write `if greeting:` rather than `greeting == True`, and
    without this the conformant spelling reads a MeTTa False as true: a user
    who tidies away the `# noqa: E712` gets a silent wrong answer.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (adult $a) (> $a 18))")
    answers = m.eval("(adult 5)")
    assert answers == [False]
    assert not any(answer for answer in answers)
    assert any(answer for answer in m.eval("(adult 21)"))

    assert bool(Grounded(True)) is True  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert bool(Grounded(False)) is False  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    # A Number 0 is not falsehood in MeTTa, and neither is an empty string
    # or an empty host container carried whole.
    assert all(bool(Grounded(value)) for value in (0, 0.0, "", [], None))


# ------------------------------------------------- generalised declarations


def test_typevar_annotations_declare_parametrically(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    A = TypeVar("A")

    @m.op(name="first-of", effect="pureStructural")
    def first_of(items: Sequence[A]) -> A:
        return items[0]

    declaration = Expression(S[":"], S["first-of"], Expression(S["->"], S.Expression, Variable("a")))
    assert any(a.alpha_eq(declaration) for a in m.atoms())
    assert m.run("!(first-of (7 8 9))") == [[7]]


def test_union_annotations_superpose_declarations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract

    @m.op(name="describe", effect="pureStructural")
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


def test_optional_return_declares_the_value_type(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract

    @m.op(name="lookup-age", effect="pureStructural")
    def lookup_age(name: str) -> int | None:
        return {"ada": 36}.get(name)

    # Returning None answers nothing, so the declared return is Number.
    assert _arrows_of(m, "lookup-age") == {"(-> String Number)"}
    assert m.run('!(lookup-age "ada")') == [[36]]
    assert m.run('!(lookup-age "bob")') == [[]]


def test_callable_and_tuple_annotations_declare_structurally(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.op(name="fixed-point-of", effect="pureStructural")
    def fixed_point_of(f: Callable[[int], int]) -> int:
        raise NotImplementedError

    assert _arrows_of(m, "fixed-point-of") == {"(-> (-> Number Number) Number)"}

    @m.op(name="swap", effect="pureStructural")
    def swap(pair: tuple[int, str]) -> tuple[str, int]:
        a, b = pair
        return (b, a)

    assert _arrows_of(m, "swap") == {"(-> (Number String) (String Number))"}
    assert m.run('!(swap (7 "x"))') == [[Expression("x", 7)]]


def test_class_annotations_declare_the_class(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclasses.dataclass
    class Particle:
        mass: float
        velocity: float

    @m.op(name="momentum", effect="pureStructural")
    def momentum(p: Particle) -> float:
        return p.mass * p.velocity

    assert _arrows_of(m, "momentum") == {"(-> Particle Number)"}
    # The referenced class became a declared type, constructor arrow typed
    # from its field annotations.
    assert _arrows_of(m, "Particle") == {"(-> Number Number Particle)"}
    assert m.eval(S.momentum(ground(Particle(2.0, 3.0)))) == [6.0]


def test_define_decorator_declares_field_types(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    @dataclasses.dataclass
    class DeclaredPoint:
        x: float
        y: float

    assert _arrows_of(m, "DeclaredPoint") == {"(-> Number Number DeclaredPoint)"}


# --------------------------------------------------- guarded bounded query


def test_query_where_guard_and_limit(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(
        S.person(S.ada, 36),
        S.person(S.bob, 12),
        S.person(S.cyd, 70),
    )
    adults = m.match(S.person(V.name, V.age), where=S[">="](V.age, 18))
    assert {str(r.name) for r in adults} == {"ada", "cyd"}
    # Guards compose with the boolean operators, the engine reading them.
    mid = m.match(
        S.person(V.name, V.age),
        where=S[">="](V.age, 18) & S["<="](V.age, 40),
    )
    assert {str(r.name) for r in mid} == {"ada"}
    assert len(m.match(S.person(V.name, V.age), limit=2)) == 2
    with pytest.raises(ValueError):
        m.match(S.person(V.name, V.age), limit=0)


# ------------------------------------------------------------- assumptions


def test_assuming_scopes_facts(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.road(S.a, S.b))
    with m.assuming(S.road(S.b, S.c)):
        assert len(m.match(S.road(V.x, V.y))) == 2
    assert len(m.match(S.road(V.x, V.y))) == 1
    # The exception path removes too.
    try:
        with m.assuming(S.road(S.b, S.c)):
            msg = "boom"
            raise RuntimeError(msg)  # noqa: TRY301  -- the raised exception is the deliberate catch-path probe exercised by this test
    except RuntimeError:
        pass
    assert len(m.match(S.road(V.x, V.y))) == 1


# --------------------------------------------------------- prepared queries


def test_prepared_query_with_given(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_a_weighted_relation_is_an_annotated_op(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # DeepProbLog's nn-predicate shape through the general seam: the op
    # answers its classes, each weight riding as the answer's annotation,
    # declared like any context; top orders, (annotation) reads.
    def mood(day):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        yield Answer(value=S.calm, k=0.25)
        yield Answer(value=S.tense, k=0.75)

    m.op(mood, name="mood", effect="nondeterministicReadOnly")
    m.annotations("mood", "prob")
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


def test_the_library_reflects_into_its_own_space(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    reflection = catalog

    @m.op(name="reflect-probe", effect="pureStructural")
    def reflect_probe(x: int) -> int:
        return x

    rows = reflection.match(S.op(S["reflect-probe"], V.arity, V.kind))
    assert [(r.arity, str(r.kind)) for r in rows] == [(1, "det")]
    m.unregister_op("reflect-probe")
    assert not reflection.match(S.op(S["reflect-probe"], V.arity, V.kind))

    @m.define(name="probe-twice")
    def probe_twice(x):
        return x + x

    assert reflection.match(S.defined(S[m.name], S["probe-twice"]))

    sub = m.subscribe(S.road(V.a, V.b))
    watched = reflection.match(S.subscription(S[m.name], V.p, V.on))
    assert len(watched) == 1 and str(watched[0].on) == "add"
    sub.cancel()
    assert not reflection.match(S.subscription(S[m.name], V.p, V.on))


def test_reflection_facts_follow_a_dropped_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    reflection = catalog
    space = metta._new_space()

    @space.define
    def fleeting(x):
        return x

    name = space.name
    assert reflection.match(S.defined(S[name], S.fleeting))
    space.drop()
    assert not reflection.match(S.defined(S[name], S.fleeting))


def test_metta_programs_steer_through_the_reflection_space(m):
    """Deeper control without forking: a Python subscription on &petta
    reacts to control atoms a MeTTa program writes there.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    reflection = catalog
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


def test_drop_cancels_the_spaces_subscriptions(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    reflection = catalog
    space = metta._new_space()
    name = space.name
    seen = []
    subscription = space.subscribe(S.ping(V.x), lambda e: seen.append(e))
    assert reflection.match(S.subscription(S[name], V.p, V.on))
    space.drop()
    # The watcher died with its space: inactive, and its reflection fact
    # removed, so a pooled name reused later starts unwatched.
    assert subscription._active is False
    assert not reflection.match(S.subscription(S[name], V.p, V.on))


def test_shared_class_declarations_survive_one_unregister(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclasses.dataclass
    class SharedReview:
        stars: float

    @m.op(name="rate-one", effect="pureStructural")
    def rate_one(r: SharedReview) -> float:
        return r.stars

    @m.op(name="rate-two", effect="pureStructural")
    def rate_two(r: SharedReview) -> float:
        return r.stars * 2

    constructor = "(-> Number SharedReview)"
    assert _arrows_of(m, "SharedReview") == {constructor}
    m.unregister_op("rate-one")
    # The other owner still declares the class.
    assert _arrows_of(m, "SharedReview") == {constructor}
    m.unregister_op("rate-two")
    assert _arrows_of(m, "SharedReview") == set()


def test_registration_failure_leaves_nothing_half_registered(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Unresolvable:
        pass

    def bad(x: "NoSuchName") -> int:  # noqa: ARG001, F821  -- the unresolved annotation is the refusal case under test; the test reflects this callable signature, so every declared parameter must remain visible
        return 1

    with pytest.raises(TypeError):
        m.op(bad, name="bad-op", effect="pureStructural")
    reflection = catalog
    assert not reflection.match(S.op(S["bad-op"], V.a, V.k))
    assert not m.is_function("bad-op")
    assert _arrows_of(m, "bad-op") == set()


# `from __future__ import annotations` makes every annotation a STRING, which
# is the default in a growing number of codebases and will be the default
# outright. A declaration generator reading the raw __annotations__ sees "int"
# rather than int and declares nothing useful, so the resolution has to happen
# before the atoms are built.
def test_postponed_annotations_generate_declarations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    namespace: dict = {}
    exec(
        "from __future__ import annotations\n"
        "def widen(count: int, label: str) -> str:\n"
        "    return label * count\n",
        namespace,
    )
    widen = namespace["widen"]
    assert widen.__annotations__["count"] == "int"

    m.op(widen, name="widen-op", effect="pureStructural")
    assert _arrows_of(m, "widen-op") == {"(-> Number String String)"}
    assert m.run('!(widen-op 2 "ab")') == [["abab"]]


def test_union_expansion_is_bounded(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    union_type = int | str | bool

    # Five inputs plus the return type produce 3**6 alternatives, over 512.
    def wide(
        a: union_type,
        b: union_type,
        c: union_type,
        d: union_type,
        e: union_type,
    ) -> union_type:
        return (a, b, c, d, e)[0]

    with pytest.raises(TypeError):
        m.op(wide, name="wide-op", effect="pureStructural")
    assert not m.is_function("wide-op")


def test_annotated_and_generic_annotations_map_faithfully(m):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    class Meta:
        pass

    T = TypeVar("T")

    class GenericBox(Generic[T]):
        pass

    assert [str(a) for a in type_atoms_for(Annotated[int, Meta])] == ["Number"]
    assert [str(a) for a in type_atoms_for(GenericBox[int])] == ["GenericBox"]
    referenced = referenced_classes([Annotated[int, Meta], GenericBox[int]])
    assert GenericBox in referenced and Meta not in referenced
