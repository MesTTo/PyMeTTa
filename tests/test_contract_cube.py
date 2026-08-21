"""Purpose: the dogfood gate. register_op's whole declaration space,
enumerated exhaustively, and for every point the clause compiled FROM the
contract atoms must be a variant of the clause builder's expected body. If a
callable policy cannot be expressed as atoms, this fails and names the point.
Guarantees:
  - every valid callable declaration combination compiles the expected clause
    and invalid raw-Atom and immutable-raw-generator combinations are absent
    [tested: test_every_cube_point_compiles_the_expected_clause;
    commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import itertools

import pytest

from petta import parse

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
    petta_py_op_body(Kind, Name, Args, Result, Forward),
    petta_py_directed_body(Name, Kind, Args, Result, Forward, Expected),
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
    signature, atom-or-value argument declaration, immutable-or-undeclared
    effect, inverse, and the arity shape. Invalid combinations are excluded by
    the registration surface itself: a raw transport never decodes atoms, and
    an immutable raw generator cannot have all its answers observed whole.
    """
    for many, raw, typed, pass_atoms, pure, inverse in itertools.product(
        (False, True), repeat=6
    ):
        if raw and pass_atoms:
            continue
        if pure and raw and many:
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
        yield fn, kind, raw, pass_atoms, pure, inverse


def test_every_cube_point_compiles_the_expected_clause(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    points = list(_points())
    assert len(points) == 44  # 2^6 minus 16 raw+pass_atoms minus 4 pure raw generators
    for index, (fn, kind, raw, pass_atoms, pure, inverse) in enumerate(points):
        name = f"cube-{index}"
        declarations = []
        if pass_atoms:
            declarations.append(parse(f"(arguments {name} atoms)"))
        if pure:
            declarations.append(parse(f"(effect {name} immutable)"))
        kwargs = {
            "transport": "raw" if raw else "encoded",
            "declarations": declarations,
            "inverse": _inverse if inverse else None,
        }
        cube.register_op(fn, name=name, **kwargs)
        try:
            verdict = cube.one(f'(cube_check "{name}" 1 "{kind}")')
            assert str(verdict) == "match", (name, kind, kwargs, str(verdict))
        finally:
            cube.unregister_op(name)


def test_multi_arity_compiles_every_declared_clause(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def spread(*args):
        return len(args)

    cube.register_op(spread, name="cube-multi", arities=[1, 2, 3])
    try:
        for arity in (1, 2, 3):
            verdict = cube.one(f'(cube_check "cube-multi" {arity} "det")')
            assert str(verdict) == "match", (arity, str(verdict))
    finally:
        cube.unregister_op("cube-multi")


def test_the_lane_can_fail(cube):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # CalDar's law: a lane that cannot fail is a defect. The planted
    # mismatch compares a det registration against the many builder and
    # must NOT answer match.
    cube.register_op(_plain_untyped, name="cube-planted")
    try:
        verdict = cube.one('(cube_check "cube-planted" 1 "many")')
        assert str(verdict) != "match"
        assert "mismatch" in str(verdict)
    finally:
        cube.unregister_op("cube-planted")
