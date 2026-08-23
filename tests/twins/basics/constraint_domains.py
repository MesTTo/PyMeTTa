"""Purpose: examples/basics/constraint_domains.metta in Python: CLP(Q) and CLP(B).

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
standing. That scope is MeTTa's `(let True <constraint> <question>)`, and
`m.solve` does not reach it, since solve derives its answer template from the
subject and here the answer is another question.

The claims read through `m.eval`, not through the answer view's `one()`. A
CLP(Q) answer still carries its rational bindings, and the lazy view decodes
them: `m.answers(...).one()` raises `ValueError: wire number payload must be
numeric, got Fraction(1, 2)` where `m.eval` answers `[Grounded('1r2')]`
[measured 2026-08-23 on this worktree; ai-report-twins2-d.md records it as a
defect in the answer view's decoder; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
  - expected constraint reprs are plain Python text rather than grounded data
    [tested: test_printing_text_is_not_forced_through_the_value_carrier;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V, equation, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


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

    # (import! &self (library lib_constraints)): the space is the handle
    # itself, and the library's MeTTa name really does carry an underscore,
    # so it takes the exact bracket rather than the attribute's hyphen map.
    m.eval(S["import!"](m, (S.library, S["lib_constraints"])))

    # ---------------------------------------------------------------- CLP(Q)
    # Exact rationals: clpfd has no answer to this at all, because 1/2 is not
    # an integer, and ordinary arithmetic cannot solve backwards. Asserted
    # through repr, because the reader has no rational literal to write 1r2
    # as: it would read back as a symbol and compare unequal to the number.
    #
    # DEFECT, and the two lines below are the workaround. The perfect spelling
    # of a one-answer claim is the cardinality door on the answer view,
    #
    #     assert m.answers(where(half, fn.repr(V.x))).one() == "1r2"
    #
    # and it raises `ValueError: wire number payload must be numeric, got
    # Fraction(1, 2)`: a CLP(Q) answer still carries its rational bindings and
    # the lazy view decodes every binding, where `m.eval` decodes only the
    # answer template. Every claim in this file that leaves a rational standing
    # has to go through `m.eval` until the view's decoder learns Fraction
    # [measured 2026-08-23 on this worktree; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    half = S.clpq(equation(2 * V.x).to(1))
    assert m.eval(where(half, fn.repr(V.x))) == ["1r2"]
    assert m.eval(where(half, 2 * V.x)) == [1]

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
        where(S.clpq(S["=<"](V.f, 3)), fn.repr(S["residual-goals"](V.f))),
    )
    assert m.eval(residuals) == ["(({} (, (>= $_0 0) (=< $_0 3))))"]

    # ---------------------------------------------------------------- CLP(B)
    # `(card (1) ($p $q))` is "exactly one of these is true": a list of
    # admissible counts and a list of variables, so a list here stays a list
    # rather than becoming an operator.
    exactly_one = where(
        S.clpb(S.card((1,), (V.m, V.n))), S["clpb-labeling"]((V.m, V.n))
    )
    assert [tuple(pair) for pair in m.eval(exactly_one)] == [(0, 1), (1, 0)]

    # Tautology and contradiction, decided without enumerating anything.
    #
    # DEFECT, and the two lines below are the workaround. The perfect spelling
    # is the bound namespace calling the function,
    #
    #     taut = m.fn["clpb-taut"]
    #     assert taut(V.t + S["~"](V.t)) == [True]
    #
    # and it answers `[Row(t=$_788)]`: a call carrying a caller variable
    # answers that variable's BINDINGS, which is right for `ancestor(V.who,
    # S.Jim).who` and wrong here, where `$t` is bound inside the formula and
    # the answer wanted is what the formula DECIDES. The two readings need
    # separate doors [measured 2026-08-23 on this worktree; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    taut = S["clpb-taut"]
    assert m.eval(taut(V.t + S["~"](V.t))) == [True]
    assert m.eval(taut(V.u * S["~"](V.u))) == [False]

    # The engine's own and/or/not are NOT replaced by this and should not be:
    # they are generate-and-test over two values, which is cheaper than
    # building a BDD until the formula constrains every variable at once.
    solutions = m.eval(S["if"]((V.x | TRUE) & V.y, (V.x, V.y)))  # rung: two-argument if
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
