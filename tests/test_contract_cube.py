"""Purpose: the dogfood gate. register_op's whole declaration space,
enumerated exhaustively, and for every point the clause compiled FROM the
contract atoms must be a variant of the clause builder's expected body. If a
callable policy cannot be expressed as atoms, this fails and names the point.
Guarantees:
  - every valid callable declaration combination compiles the expected clause
    and invalid raw-Atom and under-ranked generator combinations are refused
    [tested: test_every_cube_point_compiles_the_expected_clause;
    test_generator_effects_below_nondeterministic_rank_are_refused;
    test_raw_transport_with_atom_arguments_is_refused;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import itertools

import pytest

from metta import parse
from metta.vocabularies import EffectClass

CHECKER = """
cube_check(Name0, Arity, Kind0, Verdict) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( atom(Kind0) -> Kind = Kind0 ; atom_string(Kind, Kind0) ),
    %A registered operation's clauses go into the base tier's module, which is
    %&self's, not into `user`.
    PredArity is Arity + 1,
    functor(Head, Name, PredArity),
    Head =.. [Name|HeadArgs],
    append(Args, [Result], HeadArgs),
    metta_py_op_body(Kind, Name, Args, Result, Forward),
    metta_py_directed_body(Name, Kind, Args, Result, Forward, Expected),
    space_module('&self', Base),
    (   clause(Base:Head, Actual)
    ->  (   (Head :- Actual) =@= (Head :- Expected)
        ->  Verdict = match
        ;   term_to_atom(mismatch(Actual, Expected), Verdict)
        )
    ;   Verdict = noclause
    ).
"""


@pytest.fixture(scope="module")
def cube(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.register_prolog(CHECKER, names=["cube_check"])
    return metta


def _plain(value: int) -> int:
    return value


def _plain_untyped(value):
    return value


def _gen(value: int):
    yield value


def _gen_untyped(value):
    yield value


def _inverse(result):
    return (result,)


def _points():
    """Every valid point of the parameter cube, exhaustively.

    Axes: generator-or-plain, raw-or-encoded op kind, annotated-or-unannotated
    signature, atom-or-value argument declaration, all five ordered effects,
    inverse, and the arity shape. Invalid combinations are excluded by the
    registration surface itself: a raw transport never decodes atoms, and
    every generator is at least nondeterministicReadOnly.
    """
    for many, raw, typed, pass_atoms, effect, inverse in itertools.product(
        (False, True),
        (False, True),
        (False, True),
        (False, True),
        tuple(EffectClass),
        (False, True),
    ):
        if raw and pass_atoms:
            continue
        if many and effect < EffectClass.nondeterministicReadOnly:
            continue
        fn = {
            (False, True): _plain,
            (False, False): _plain_untyped,
            (True, True): _gen,
            (True, False): _gen_untyped,
        }[(many, typed)]
        kind = {
            (False, False): "det",
            (True, False): "many",
            (False, True): "raw_det",
            (True, True): "raw_many",
        }[(many, raw)]
        yield fn, kind, raw, pass_atoms, effect, inverse


def test_every_cube_point_compiles_the_expected_clause(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    points = list(_points())
    # 2^5 * 5, minus 40 raw+Atom points, minus 24 under-ranked generators.
    assert len(points) == 96
    assert {point[4] for point in points} == set(EffectClass)
    for index, (fn, kind, raw, pass_atoms, effect, inverse) in enumerate(points):
        name = f"cube-{index}"
        declarations = []
        if pass_atoms:
            declarations.append(parse(f"(arguments {name} atoms)"))
        kwargs = {
            "transport": "raw" if raw else "encoded",
            "effect": effect,
            "declarations": declarations,
            "inverse": _inverse if inverse else None,
        }
        cube.op(fn, name=name, **kwargs)
        try:
            verdict = cube._one(f'(cube_check "{name}" 1 "{kind}")')
            assert str(verdict) == "match", (name, kind, kwargs, str(verdict))
        finally:
            cube.unregister_op(name)


def test_multi_arity_compiles_every_declared_clause(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def spread(*args):
        return len(args)

    cube.op(
        spread,
        name="cube-multi",
        arities=[1, 2, 3],
        effect=EffectClass.pureStructural,
    )
    try:
        for arity in (1, 2, 3):
            verdict = cube._one(f'(cube_check "cube-multi" {arity} "det")')
            assert str(verdict) == "match", (arity, str(verdict))
    finally:
        cube.unregister_op("cube-multi")


def test_the_lane_can_fail(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # CalDar's law: a lane that cannot fail is a defect. The planted
    # mismatch compares a det registration against the many builder and
    # must NOT answer match.
    cube.op(
        _plain_untyped,
        name="cube-planted",
        effect=EffectClass.pureStructural,
    )
    try:
        verdict = cube._one('(cube_check "cube-planted" 1 "many")')
        assert str(verdict) != "match"
        assert "mismatch" in str(verdict)
    finally:
        cube.unregister_op("cube-planted")


@pytest.mark.parametrize(
    "effect",
    (EffectClass.pureStructural, EffectClass.readOnlyLookup),
)
@pytest.mark.parametrize("transport", ("encoded", "raw"))
def test_generator_effects_below_nondeterministic_rank_are_refused(
    cube, effect, transport
):
    """A generator refuses either effect below its minimum valid rank."""
    name = f"cube-under-ranked-{transport}-{effect.value}"
    with pytest.raises(
        ValueError, match="nondeterministicReadOnly or a stronger class"
    ):
        cube.op(_gen, name=name, transport=transport, effect=effect)


def test_raw_transport_with_atom_arguments_is_refused(cube):
    """Raw transport still refuses a declaration that requires Atom decoding."""
    name = "cube-raw-atoms"
    with pytest.raises(ValueError, match="raw calls do not cross the atom codec"):
        cube.op(
            _plain_untyped,
            name=name,
            transport="raw",
            effect=EffectClass.pureStructural,
            declarations=[parse(f"(arguments {name} atoms)")],
        )
