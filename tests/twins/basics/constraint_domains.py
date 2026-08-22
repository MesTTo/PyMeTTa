"""examples/basics/constraint_domains.metta in Python: CLP(Q) and CLP(B).

Both solvers take their constraint AS WRITTEN, unevaluated, which is exactly
what a built term is: `S.clpq(equation(2 * V.x).to(1))` hands over
`(= (* 2 $x) 1)` without running the multiplication. That is the same reason
the original writes it inside `clpq` rather than letting it evaluate, so the
Python spelling and the MeTTa spelling agree about why.

A constraint is written with the ordinary builders, because a constraint IS an
ordinary term: `equation(lhs).to(rhs)` builds `(= lhs rhs)` and `V.a >= 0`
builds `(>= $a 0)`, the same atoms a rule or a query is made of. `=<` and the
disequation stay at the naming door, being CLP(Q) relation names Python has no
operator for.

One rung is dropped, once, and named: `where`. A constraint has to be POSTED
and then asked about inside ONE derivation, because the store is undone on the
way out; two separate calls from Python would ask a question with nothing
standing. That scope is MeTTa's `(let True <constraint> <question>)`, the same
guard form examples/functions/functionhead3.metta's twin names, and Python has
no spelling for it.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 92108 to 92903, +795, by the p14-tabling merge, the
#: sole change between the two readings: admission analysis and notification
#: on its many definitions. Ratio 92903/109228 = 0.8505 [measured 2026-08-23
#: min-of-3 via tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 94647 to 92108, -2539 (-2.7%), by the twin
#: contract change: the `test` wrapper and five `collapse` calls left the
#: engine for `assert` and the answer list; every constraint post,
#: entailment check and labelling stayed, which is why the saving is 2.8%
#: rather than the folder's usual half. Against the example's 108447 the
#: ratio is 0.8493 [measured 2026-08-22 min-of-3, `twin_coverage.py
#: --measure`]. The old figure priced a different program.
BUDGET = 92903


def twin(m):
    """Post rational and boolean constraints, and ask what they decide."""

    def where(condition, answer):
        """Answer `answer` only where `condition` reduces to True.

        MeTTa's `(let True <condition> <answer>)`, the guard reading of `let`.
        Everything it guards is evaluated in ONE derivation, which is what a
        posted constraint needs, since the store is undone on the way out.
        Python's `where=` says this on a query, but a guard over a CALL has no
        Python spelling; the residue table records it against P14.4.
        """
        return S.let(TRUE, condition, answer)  # rung: let as a guard

    m.eval(S["import!"](S["&self"], (S.library, S.lib_constraints)))  # rung: space as a symbol

    # ---------------------------------------------------------------- CLP(Q)
    # Exact rationals: clpfd has no answer to this at all, because 1/2 is not
    # an integer, and ordinary arithmetic cannot solve backwards. Asserted
    # through repr, because the reader has no rational literal to write 1r2
    # as: it would read back as a symbol and compare unequal to the number.
    half = S.clpq(equation(2 * V.x).to(1))
    assert m.one(where(half, S.repr(V.x))) == val("1r2")
    assert m.one(where(half, 2 * V.x)) == 1

    # Entailment: is this constraint already implied by what has been posted?
    # That is the question a plain post cannot ask.
    assert m.eval(where(S.clpq(V.a >= 0), S["clpq-entailed"](V.a >= 0))) == [True]
    assert m.eval(where(S.clpq(V.b >= 0), S["clpq-entailed"](V.b >= 5))) == [False]

    # A contradiction fails rather than answering, which is how a constraint
    # says no: no answers at all.
    assert m.eval(where(S.clpq(equation(V.c).to(1)), S.clpq(equation(V.c).to(2)))) == []

    # Disequations over the rationals, dif's numeric analogue.
    assert m.eval(
        where(
            S.clpq(equation(V.d).to(1)),
            where(S.clpq(equation(V.e).to(2)), S.clpq(S[r"=\="](V.d, V.e))),
        )
    ) == [True]

    # The constraints an answer still CARRIES read back through
    # residual-goals, rendered with repr rather than compared as a term,
    # because a term holding `(>= $g 0)` would run as arithmetic on an
    # unbound variable.
    residuals = where(
        S.clpq(V.f >= 0),
        where(S.clpq(S["=<"](V.f, 3)), S.repr(S["residual-goals"](V.f))),
    )
    assert m.one(residuals) == val("(({} (, (>= $_0 0) (=< $_0 3))))")

    # ---------------------------------------------------------------- CLP(B)
    # `(card (1) ($p $q))` is "exactly one of these is true": a list of
    # admissible counts and a list of variables, so a list here stays a list
    # rather than becoming an operator.
    exactly_one = where(
        S.clpb(S.card((1,), (V.m, V.n))), S["clpb-labeling"]((V.m, V.n))
    )
    assert [tuple(pair) for pair in m.eval(exactly_one)] == [(0, 1), (1, 0)]

    # Tautology and contradiction, decided without enumerating anything.
    taut = m.fn("clpb-taut")
    assert taut(V.t + S["~"](V.t)) is True
    assert taut(V.u * S["~"](V.u)) is False

    # The engine's own and/or/not are NOT replaced by this and should not be:
    # they are generate-and-test over two values, which is cheaper than
    # building a BDD until the formula constrains every variable at once.
    solutions = m.eval(S["if"]((V.x | TRUE) & V.y, (V.x, V.y)))  # rung: two-argument if
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
