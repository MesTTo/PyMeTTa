"""Purpose: examples/libraries/minimal_metta.metta in Python: the instruction set, run.

Twenty-eight claims about minimal MeTTa's own instructions: `function` and
`return`, the `unify-mod` matcher, the recursive `mm-switch`, the reduction
loop, `collapse-bind` and `superpose-bind`, the Turing machine, and the partial
function. All of them are the file's subject, so all of them are named.

Each instruction is CALLED, `m.fn.function(...)` and `m.fn.unify_mod(...)`,
and most of them carry a MeTTa variable in an argument, because that is what
an instruction set is made of: `(chain (+ 1 2) $x (return $x))` binds `$x`,
`(unify-mod (p 5) (p $x) (got $x) else)` matches it, `(mm-reduce (step-down 3)
$x $x)` templates it. A call answers what the instruction reduced to whether
or not its arguments carry variables, so the call door says all of them.

Three claims keep a composed term instead, and each names its reason on the
line. `collapse` is one: at the call door `mm-switch` with no matching case
answers the `Empty` atom, where `(collapse ...)` is what PRUNES it, so
`list()` would collect an answer the engine does not give. `return` is the
other: it is an instruction inside `function` rather than a function of its
own, so the namespace has nothing to resolve.

Every name here descends the ladder exactly as far as it has to. Hyphenated
heads take the attribute door, `S.mm_switch` and `S.collapse_bind`, because
rung 4's map is total. The bracket is kept only for what Python's grammar
cannot say: the keywords `return` and `else`, the punctuation heads `:=`,
`...` and `<-`, and `minimal_metta_lib`, whose MeTTa name really does have
underscores.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, Expression, S, V, equation

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
    m.fn["import!"](m, S.library(S["minimal_metta_lib"]))

    assert m.fn.function(S["return"](42)) == [42]
    assert m.fn.function(S.chain(S.add(1, 2), V.x, S["return"](V.x))) == [3]

    returned = S["return"](7)
    assert m.eval(returned) == [returned]  # rung: `return` is an instruction of `function`, not a function of its own

    failed_body = S.foo(S.bar)
    assert m.fn.function(failed_body) == [S.Error(failed_body, S.NoReturn)]

    otherwise = S["else"]
    assert m.fn.unify_mod(V.a, S.Empty, S.then, otherwise) == [S.then]
    assert m.fn.unify_mod(V.a, S[":="](S.Empty), S.then, otherwise) == [otherwise]
    assert m.fn.unify_mod(
        S[":="](S.a, S.b), S[":="](V.x, V.y), S.then, otherwise
    ) == [S.then]
    assert m.fn.unify_mod(
        (S.A, S.B, S.C, S.D, S.E),
        (S.A, S["..."], S.D, S["..."]),
        S.matched,
        S.nomatch,
    ) == [S.matched]
    assert m.fn.unify_mod(S.p(5), S.p(V.x), S.got(V.x), otherwise) == [S.got(5)]

    cases = ((1, S.one), (2, S.two))
    assert m.fn.mm_switch(1, cases) == [S.one]
    assert m.fn.mm_switch(2, cases) == [S.two]
    assert m.fn.mm_switch(S.p(5), ((S.p(V.x), S.got(V.x)),)) == [S.got(5)]

    # No case matches, so the switch answers Empty and the collapse prunes it.
    unmatched = S.mm_switch(9, cases)
    assert m.eval(S.collapse(unmatched)) == [Expression(())]  # rung: `collapse` is what drops the Empty marker, and a Python list does not

    @m.define
    def step_down(n):
        # (= (step-down $n) (if (> $n 0) (step-down (- $n 1)) done))
        return step_down(n - 1) if n > 0 else S.done

    # The reduction loop is HANDED the call rather than making it, so these two
    # write `S.step_down(3)`: calling the Symbol builds where calling the
    # definition would evaluate.
    assert m.fn.mm_reduce(S.step_down(3), V.x, V.x) == [S.done]
    assert m.fn.mm_reduce(S.step_down(3), V.x, S.wrapped(V.x)) == [S.wrapped(S.done)]
    assert m.fn.mm_reduce(S.add(1, 2), V.y, V.y) == [3]

    m += S.edge(S.a, S.b)
    m += S.edge(S.a, S.c)
    matched_edges = S.match(m, S.edge(S.a, V.y), S.found(V.y))  # rung: match's space is an ARGUMENT of the instruction under test, and the whole term is what `collapse-bind` is handed
    rows = m.fn.collapse_bind(matched_edges).one()
    assert rows.alpha_eq(
        Expression((
            (S.found(S.b), S.bindings(S["<-"](V.v, S.b))),
            (S.found(S.c), S.bindings(S["<-"](V.v, S.c))),
        ))
    )
    assert m.fn.superpose_bind(rows) == [S.found(S.b), S.found(S.c)]

    restored = S.chain(
        S.collapse_bind(matched_edges),
        V.c,
        S.chain(S.superpose_bind(V.c), V.x, (V.x, V.y)),
    )
    assert m.eval(S.collapse(restored)) == [  # rung: `collapse` gathers the two answers into ONE atom, which the example's own claim compares against
        Expression(((S.found(S.b), S.b), (S.found(S.c), S.c)))
    ]

    m += equation(S.rule(S.S, 0)).to((S.S, 1, S.R))
    m += equation(S.rule(S.S, 1)).to((S.HALT, 1, S.N))

    assert m.fn.mm_tm(S.rule, S.S, ((), 1, ())) == [Expression(((), 1, ()))]
    assert m.fn.mm_tm(S.rule, S.S, ((), 0, (1,))) == [Expression(((1,), 1, ()))]
    assert m.fn.mm_tm(S.rule, S.S, ((), 0, (0, 0, 1))) == [
        Expression(((1, 1, 1), 1, ()))
    ]

    assert m.fn.mm_move(((), 0, (7,)), 1, S.R) == [Expression(((1,), 7, ()))]
    assert m.fn.mm_move(((9,), 0, ()), 1, S.L) == [Expression(((), 9, (1,)))]
    assert m.fn.mm_move(((), 0, ()), 1, S.R) == [Expression(((1,), 0, ()))]
    assert m.fn.mm_move(((1,), 0, (2,)), 9, S.N) == [Expression(((1,), 9, (2,)))]

    assert m.fn.if_partial(TRUE, S.yes) == [S.yes]
    assert m.fn.if_partial(FALSE, S.yes) == [S.Empty]
