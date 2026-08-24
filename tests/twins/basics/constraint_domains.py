"""Purpose: examples/basics/constraint_domains.metta in Python: CLP(Q) and CLP(B).

Both solvers take their constraint AS WRITTEN, unevaluated, which is exactly
what a built term is: `S.clpq(equation(2 * V.x).to(1))` hands over
`(= (* 2 $x) 1)` without running the multiplication. That is the same reason
the original writes it inside `clpq` rather than letting it evaluate, so the
Python spelling and the MeTTa spelling agree about why.

A constraint is written with the ordinary builders, because a constraint IS an
ordinary term: `equation(lhs).to(rhs)` builds `(= lhs rhs)` and `2 * V.x`
builds `(* 2 $x)`, the same atoms a rule or a query is made of. The comparison
relations all come from the naming door, `S[">="](V.a, 0)` for `(>= $a 0)`
beside `=<` and the disequation, because Python's four rich comparisons order
atoms and never build.

One rung is dropped, once, and named: `where`. A constraint has to be POSTED
and then asked about inside ONE derivation, because the store is undone on the
way out; two separate calls from Python would ask a question with nothing
standing. That scope is MeTTa's `(let True <constraint> <question>)`, and
`m.solve` does not reach it, since solve derives its answer template from the
subject and here the answer is another question.

The claims read through the answer view's cardinality doors, over answers that
still carry rational bindings: `m.answers(where(half, fn.repr(V.x))).one()`
answers `'1r2'`, because the view decodes a rational payload as a
`fractions.Fraction` [measured 2026-08-23: probe over the merged tree;
commit=WORKTREE].
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
  - expected constraint reprs are plain Python text rather than grounded data
    [tested: test_printing_text_is_not_forced_through_the_value_carrier;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
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
    m.fn["import!"](m, (S.library, S["lib_constraints"]))

    # ---------------------------------------------------------------- CLP(Q)
    # Exact rationals: clpfd has no answer to this at all, because 1/2 is not
    # an integer, and ordinary arithmetic cannot solve backwards. Asserted
    # through repr, because the reader has no rational literal to write 1r2
    # as: it would read back as a symbol and compare unequal to the number.
    half = S.clpq(equation(2 * V.x).to(1))
    assert m.answers(where(half, fn.repr(V.x))).one() == "1r2"
    assert m.answers(where(half, 2 * V.x)).one() == 1

    # Entailment: is this constraint already implied by what has been posted?
    # That is the question a plain post cannot ask.
    nonnegative = S.ge(V.a, 0)
    assert m.answers(
        where(S.clpq(nonnegative), S.clpq_entailed(nonnegative))
    ).one() is True
    assert m.answers(
        where(S.clpq(S.ge(V.b, 0)), S.clpq_entailed(S.ge(V.b, 5)))
    ).one() is False

    # A contradiction fails rather than answering, which is how a constraint
    # says no: no answers at all, which is an empty view.
    assert not m.answers(
        where(S.clpq(equation(V.c).to(1)), S.clpq(equation(V.c).to(2)))
    )

    # Disequations over the rationals, dif's numeric analogue.
    assert m.answers(
        where(
            S.clpq(equation(V.d).to(1)),
            where(S.clpq(equation(V.e).to(2)), S.clpq(S[r"=\="](V.d, V.e))),
        )
    ).one() is True

    # The constraints an answer still CARRIES read back through
    # residual-goals, rendered with repr rather than compared as a term,
    # because a term holding `(>= $g 0)` would run as arithmetic on an
    # unbound variable.
    residuals = where(
        S.clpq(S.ge(V.f, 0)),
        where(S.clpq(S["=<"](V.f, 3)), fn.repr(S.residual_goals(V.f))),
    )
    assert m.answers(residuals).one() == "(({} (, (>= $_0 0) (=< $_0 3))))"

    # ---------------------------------------------------------------- CLP(B)
    # `(card (1) ($p $q))` is "exactly one of these is true": a list of
    # admissible counts and a list of variables, so a list here stays a list
    # rather than becoming an operator.
    exactly_one = where(
        S.clpb(S.card((1,), (V.m, V.n))), S.clpb_labeling((V.m, V.n))
    )
    assert [tuple(pair) for pair in m.answers(exactly_one)] == [(0, 1), (1, 0)]

    # Tautology and contradiction, decided without enumerating anything. The
    # formula's own `$t` is bound inside it, so what the call answers is what
    # the formula DECIDES rather than a binding row.
    taut = m.fn["clpb-taut"]
    assert taut(V.t + S["~"](V.t)).one() is True
    assert taut(V.u * S["~"](V.u)).one() is False

    # The engine's own and/or/not are NOT replaced by this and should not be:
    # they are generate-and-test over two values, which is cheaper than
    # building a BDD until the formula constrains every variable at once.
    solutions = m.answers(if_((V.x | TRUE) & V.y, (V.x, V.y)))
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
