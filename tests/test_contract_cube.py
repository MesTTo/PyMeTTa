"""Purpose: the dogfood gate. register_op's whole parameter space, enumerated
exhaustively, and for every point the clause compiled FROM the contract atoms
must be a variant of the clause the builders produce from the point's
parameters directly. If a parameter cannot be expressed as atoms, this is
where it fails, naming the point.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import itertools

import pytest

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
def cube(metta):
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

    Axes: generator-or-plain (kind many/det), raw, typed, pass_atoms, pure,
    inverse, and the arity shape. Invalid combinations are excluded by the
    registration surface itself and listed here so the exclusion is visible
    rather than silent: typed=True needs annotations (the untyped functions
    pair with typed=False), and pass_atoms with raw=True is meaningless
    because the raw path never decodes, and pure with a raw generator is
    refused by the surface itself ("a raw generator's answers cross one at
    a time and are never seen whole").
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
        yield fn, kind, {
            "typed": typed,
            "raw": raw,
            "pass_atoms": pass_atoms,
            "pure": pure,
            "inverse": _inverse if inverse else None,
        }


def test_every_cube_point_compiles_the_expected_clause(cube):
    points = list(_points())
    assert len(points) == 44  # 2^6 minus 16 raw+pass_atoms minus 4 pure raw generators
    for index, (fn, kind, kwargs) in enumerate(points):
        name = f"cube-{index}"
        cube.register_op(fn, name=name, **kwargs)
        try:
            verdict = cube.one(f'(cube_check "{name}" 1 "{kind}")')
            assert str(verdict) == "match", (name, kind, kwargs, str(verdict))
        finally:
            cube.unregister_op(name)


def test_multi_arity_compiles_every_declared_clause(cube):
    def spread(*args):
        return len(args)

    cube.register_op(spread, name="cube-multi", typed=False, arities=[1, 2, 3])
    try:
        for arity in (1, 2, 3):
            verdict = cube.one(f'(cube_check "cube-multi" {arity} "det")')
            assert str(verdict) == "match", (arity, str(verdict))
    finally:
        cube.unregister_op("cube-multi")


def test_the_lane_can_fail(cube):
    # CalDar's law: a lane that cannot fail is a defect. The planted
    # mismatch compares a det registration against the many builder and
    # must NOT answer match.
    cube.register_op(_plain_untyped, name="cube-planted", typed=False)
    try:
        verdict = cube.one('(cube_check "cube-planted" 1 "many")')
        assert str(verdict) != "match"
        assert "mismatch" in str(verdict)
    finally:
        cube.unregister_op("cube-planted")
