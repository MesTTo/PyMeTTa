"""Purpose: exercise the minimal-MeTTa example through Python-built atoms.

The twin covers every instruction-set claim in examples/libraries/minimal_metta.metta.
Assumes:
  - minimal_metta_lib publishes the function, binding, switch, reducer, and
    Turing-machine operations used below
    [source: lib/minimal_metta_lib.metta:mm-tm; commit=WORKTREE]
Guarantees:
  - twin imports the library and asserts all twenty-eight source claims while
    keeping collapse-bind's fresh variable comparison alpha-invariant
    [measured: twin completed; command=bindings/python/tools/twin_coverage.py --measure examples/libraries/minimal_metta.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S, V, alpha_eq, encode, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 193216..193420 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 193216,
    "maximum": 193420,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Run the minimal evaluator, binding carrier, reducer, and machine."""
    m.eval(
        S["import!"](
            S["&self"],  # rung: import!'s target is a named space argument; handles do not yet encode there
            S.library(S.minimal_metta_lib),
        )
    )

    function = m.fn("function")
    assert function(S["return"](42)) == 42
    assert function(S.chain(S["+"](1, 2), V.x, S["return"](V.x))) == 3

    returned = S["return"](7)
    assert m.eval(returned) == [returned]

    failed_body = S.foo(S.bar)
    assert m.eval(S.function(failed_body)) == [S.Error(failed_body, S.NoReturn)]

    unify_mod = m.fn("unify-mod")
    otherwise = S["else"]
    assert unify_mod(V.a, S.Empty, S.then, otherwise) == S.then
    assert unify_mod(V.a, S[":="](S.Empty), S.then, otherwise) == otherwise
    assert unify_mod(S[":="](S.a, S.b), S[":="](V.x, V.y), S.then, otherwise) == S.then
    assert unify_mod(
        (S.A, S.B, S.C, S.D, S.E),
        (S.A, S["..."], S.D, S["..."]),
        S.matched,
        S.nomatch,
    ) == S.matched
    assert unify_mod(S.p(5), S.p(V.x), S.got(V.x), otherwise) == S.got(5)

    switch = m.fn("mm-switch")
    cases = ((1, S.one), (2, S.two))
    assert switch(1, cases) == S.one
    assert switch(2, cases) == S.two
    assert switch(S.p(5), ((S.p(V.x), S.got(V.x)),)) == S.got(5)

    collapse = m.fn("collapse")
    assert tuple(collapse(S["mm-switch"](9, cases))) == ()

    step_down = S["step-down"]
    m += equation(step_down(V.n)).to(
        S["if"](  # rung: lowercase `done` is data in a stored equation and cannot be returned by a compiled body yet
            V.n > 0,
            step_down(V.n - 1),
            S.done,
        )
    )

    reduce_ = m.fn("mm-reduce")
    assert reduce_(step_down(3), V.x, V.x) == S.done
    assert reduce_(step_down(3), V.x, S.wrapped(V.x)) == S.wrapped(S.done)
    assert reduce_(S["+"](1, 2), V.y, V.y) == 3

    m.add(S.edge(S.a, S.b), S.edge(S.a, S.c))
    matched_edges = S.match(S["&self"], S.edge(S.a, V.y), S.found(V.y))  # rung: match's space is an argument whose handle does not encode yet
    rows = m.fn("collapse-bind")(matched_edges)
    expected_rows = encode(
        (
            (S.found(S.b), S.bindings(S["<-"](V.v, S.b))),
            (S.found(S.c), S.bindings(S["<-"](V.v, S.c))),
        )
    )
    assert alpha_eq(rows, expected_rows)
    assert m.fn("superpose-bind").all(rows) == [S.found(S.b), S.found(S.c)]

    restored = S.chain(
        S["collapse-bind"](matched_edges),
        V.c,
        S.chain(S["superpose-bind"](V.c), V.x, (V.x, V.y)),
    )
    assert collapse(restored) == encode(((S.found(S.b), S.b), (S.found(S.c), S.c)))

    m.add(
        equation(S.rule(S.S, 0)).to((S.S, 1, S.R)),
        equation(S.rule(S.S, 1)).to((S.HALT, 1, S.N)),
    )
    run_machine = m.fn("mm-tm")
    move = m.fn("mm-move")

    assert run_machine(S.rule, S.S, ((), 1, ())) == encode(((), 1, ()))
    assert run_machine(S.rule, S.S, ((), 0, (1,))) == encode(((1,), 1, ()))
    assert run_machine(S.rule, S.S, ((), 0, (0, 0, 1))) == encode(((1, 1, 1), 1, ()))

    assert move(((), 0, (7,)), 1, S.R) == encode(((1,), 7, ()))
    assert move(((9,), 0, ()), 1, S.L) == encode(((), 9, (1,)))
    assert move(((), 0, ()), 1, S.R) == encode(((1,), 0, ()))
    assert move(((1,), 0, (2,)), 9, S.N) == encode(((1,), 9, (2,)))

    partial = m.fn("if-partial")
    assert partial(TRUE, S.yes) == S.yes
    assert partial.all(FALSE, S.yes) == [S.Empty]
