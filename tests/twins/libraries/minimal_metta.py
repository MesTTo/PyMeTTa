"""Purpose: examples/libraries/minimal_metta.metta in Python: the instruction set, run.

Twenty-eight claims about minimal MeTTa's own instructions: `function` and
`return`, the `unify-mod` matcher, the recursive `mm-switch`, the reduction
loop, `collapse-bind` and `superpose-bind`, the Turing machine, and the partial
function. All of them are the file's subject, so all of them are named.

DEFECT, and it decides how this file is written. Every claim below ought to
read `m.fn.function(...)`, `m.fn.unify_mod(...)` and so on, the call door.
Twenty of the twenty-eight carry a MeTTa VARIABLE in an argument, because that
is what an instruction set is made of: `(chain (+ 1 2) $x (return $x))` binds
`$x`, `(unify-mod (p 5) (p $x) (got $x) else)` matches it, `(mm-reduce (step-
down 3) $x $x)` templates it. The answer view reads every variable in a call as
one of the caller's own and answers a binding ROW instead of the term the claim
is about. So the instruction names are bound as MENTIONS, each claim composes
one term, and `eval` performs it once, exactly as the example's own single form
does.

`return` and `if` take the bracket at the `S` door because Python's grammar
keeps those words, and `minimal_metta_lib` takes it because that library name
really has underscores.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, Expression, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 204 inferences over the concurrent lane's own observations, because
#: the shared engine's scheduling changes what a concurrent round costs
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Run the minimal evaluator, binding carrier, reducer, and machine."""
    m.eval(S["import!"](m, S.library(S["minimal_metta_lib"])))

    function, chain, returns = S.function, S.chain, S["return"]
    assert m.eval(function(returns(42))) == [42]
    assert m.eval(function(chain(S["+"](1, 2), V.x, returns(V.x)))) == [3]

    returned = returns(7)
    assert m.eval(returned) == [returned]

    failed_body = S.foo(S.bar)
    assert m.eval(function(failed_body)) == [S.Error(failed_body, S.NoReturn)]

    unify_mod, otherwise = S["unify-mod"], S["else"]
    assert m.eval(unify_mod(V.a, S.Empty, S.then, otherwise)) == [S.then]
    assert m.eval(unify_mod(V.a, S[":="](S.Empty), S.then, otherwise)) == [otherwise]
    assert m.eval(
        unify_mod(S[":="](S.a, S.b), S[":="](V.x, V.y), S.then, otherwise)
    ) == [S.then]
    assert m.eval(
        unify_mod(
            (S.A, S.B, S.C, S.D, S.E),
            (S.A, S["..."], S.D, S["..."]),
            S.matched,
            S.nomatch,
        )
    ) == [S.matched]
    assert m.eval(unify_mod(S.p(5), S.p(V.x), S.got(V.x), otherwise)) == [S.got(5)]

    switch = S["mm-switch"]
    cases = ((1, S.one), (2, S.two))
    assert m.eval(switch(1, cases)) == [S.one]
    assert m.eval(switch(2, cases)) == [S.two]
    assert m.eval(switch(S.p(5), ((S.p(V.x), S.got(V.x)),))) == [S.got(5)]

    collapse = S.collapse
    assert m.eval(collapse(switch(9, cases))) == [Expression(())]

    step_down = S["step-down"]
    m += equation(step_down(V.n)).to(
        S["if"](  # rung: lowercase `done` is data in a stored equation and cannot be returned by a compiled body yet
            V.n > 0,
            step_down(V.n - 1),
            S.done,
        )
    )

    reduce_ = S["mm-reduce"]
    assert m.eval(reduce_(step_down(3), V.x, V.x)) == [S.done]
    assert m.eval(reduce_(step_down(3), V.x, S.wrapped(V.x))) == [S.wrapped(S.done)]
    assert m.eval(reduce_(S["+"](1, 2), V.y, V.y)) == [3]

    m += S.edge(S.a, S.b)
    m += S.edge(S.a, S.c)
    matched_edges = S.match(m, S.edge(S.a, V.y), S.found(V.y))  # rung: match's space is an ARGUMENT of the instruction under test, and the whole term is what `collapse-bind` is handed
    [rows] = m.eval(S["collapse-bind"](matched_edges))
    assert rows.alpha_eq(
        Expression((
            (S.found(S.b), S.bindings(S["<-"](V.v, S.b))),
            (S.found(S.c), S.bindings(S["<-"](V.v, S.c))),
        ))
    )
    assert m.eval(S["superpose-bind"](rows)) == [S.found(S.b), S.found(S.c)]

    restored = chain(
        S["collapse-bind"](matched_edges),
        V.c,
        chain(S["superpose-bind"](V.c), V.x, (V.x, V.y)),
    )
    assert m.eval(collapse(restored)) == [
        Expression(((S.found(S.b), S.b), (S.found(S.c), S.c)))
    ]

    m += equation(S.rule(S.S, 0)).to((S.S, 1, S.R))
    m += equation(S.rule(S.S, 1)).to((S.HALT, 1, S.N))
    run_machine, move = S["mm-tm"], S["mm-move"]

    assert m.eval(run_machine(S.rule, S.S, ((), 1, ()))) == [Expression(((), 1, ()))]
    assert m.eval(run_machine(S.rule, S.S, ((), 0, (1,)))) == [Expression(((1,), 1, ()))]
    assert m.eval(run_machine(S.rule, S.S, ((), 0, (0, 0, 1)))) == [
        Expression(((1, 1, 1), 1, ()))
    ]

    assert m.eval(move(((), 0, (7,)), 1, S.R)) == [Expression(((1,), 7, ()))]
    assert m.eval(move(((9,), 0, ()), 1, S.L)) == [Expression(((), 9, (1,)))]
    assert m.eval(move(((), 0, ()), 1, S.R)) == [Expression(((1,), 0, ()))]
    assert m.eval(move(((1,), 0, (2,)), 9, S.N)) == [Expression(((1,), 9, (2,)))]

    partial = S["if-partial"]
    assert m.eval(partial(TRUE, S.yes)) == [S.yes]
    assert m.eval(partial(FALSE, S.yes)) == [S.Empty]
