"""Purpose: examples/ch05-equations-and-evaluation/05-04-arithmetic-that-runs-backwards/03-constraint_domains.metta in Python: CLP(Q) and CLP(B).

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
commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
  - expected constraint reprs are plain Python text rather than grounded data
    [tested: test_printing_text_is_not_forced_through_the_value_carrier;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, equation, fn, if_, lib


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

    # (import! &self (library lib_constraints)): the receiver is the target,
    # and the lib namespace joins with underscores kept, never the hyphen map.
    m += lib.constraints

    # ---------------------------------------------------------------- CLP(Q)
    # Exact rationals: clpfd has no answer to this at all, because 1/2 is not
    # an integer, and ordinary arithmetic cannot solve backwards. Asserted
    # through repr, because the reader has no rational literal to write 1r2
    # as: it would read back as a symbol and compare unequal to the number.
    half = S.clpq(equation(2 * V.x).to(1))
    assert m.answers(where(half, fn.repr(V.x))) == ["1r2"]
    assert m.answers(where(half, 2 * V.x)) == [1]

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
    assert m.answers(residuals) == ["(({} (, (>= $_0 0) (=< $_0 3))))"]

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


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 74898 to 74953, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 74953 to 74962, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 74962 to 74964, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 74964 to 74525 (-439), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 74525 to 76927 (+2402), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 76927 to 76907 (-20), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 76907 to 76966 (+59), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 76966 to 77461 (+495), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 77461 to 77508 (+47), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 77508
