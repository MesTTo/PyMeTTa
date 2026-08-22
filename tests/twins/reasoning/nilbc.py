"""examples/reasoning/nilbc.metta in Python: a dependently-typed backward chainer.

A proof search over Metamath's demo0, in three of the example's four levels of
difficulty: easy ignores the term and wff types, medium uses them, and hard adds
Metamath's own implication. Each level is a space of axioms, and each claim asks
the chainer to build a proof term and checks the one it built.

The chainer's five recursive clauses are ONE shape repeated for one through five
premises: recurse on the abstraction, recurse on each premise, answer the
fulfilled query. The example writes the five out; here `_chain(n)` writes the
n-premise clause and a `range` supplies the five, so the shape is stated once.
The Metamath vocabulary gets Python functions for the same reason: `eq`, `plus`,
`implies` and `typed` turn a wall of angle brackets into readable logic.

Everything stays at the container door, and the reasons are in the clauses:

- every `bc` clause destructures in the HEAD, `(S $depth)` and
  `(: ($rule $p1 ...) $thm)`, and a compiled head pattern must be a literal;
- `fromNat`'s two clauses have a SYMBOL head pattern (`Z`) and a structural one
  (`(S $k)`), which a stacked Python clause's literal default cannot spell;
- `fromNumber` would compile except for one collision: its body builds `(S ...)`
  and a capitalised free name in a compiled body is a data constructor UNLESS it
  is a module binding, which `S` is here because `S` is the symbol factory every
  twin imports. The refusal is right, silently dropping a host value would be
  worse, and the collision is real.

Each is a residue entry against P14.4. Three more show here: `typed(x, T)` is
the declaration-term builder the design names and it is not exported, so this
file defines its own; the three knowledge bases are named as symbols inside `bc`
calls, because a term carries no handle; and alpha-equality is still the module
function `alpha_eq(a, b)` rather than the `a.alpha_eq(b)` method the design
settled on, which the easy claim needs because its answer carries a free
variable.
"""

from petta import S, V, alpha_eq, equation

#: Why this file sits below the top rung: the chainer's clauses destructure in
#: the head, `fromNat` has a symbol head pattern, `fromNumber` collides with the
#: `S` factory, and `bc` takes its knowledge base as a NAME.
RUNG = "the chainer destructures in the head, fromNat has a symbol head pattern, fromNumber collides with the S factory, and bc takes its space as a name"

#: The addition head, needed with a GROUND left operand.
PLUS = S["+"]

#: Metamath's vocabulary, as this example spells it.
TERM, WFF, ZERO, TT = S["⟨term⟩"], S["⟨wff⟩"], S["⟨0⟩"], S["⟨t⟩"]

#: The three knowledge bases, one per level of difficulty. Their handles are
#: built from these names.
KBE, KBM, KBH = S["&kbe"], S["&kbm"], S["&kbh"]

#: The example's premise variables, in its own spelling: the one-premise clause
#: writes them without a digit and the rest number them from one.
PREMISE = (
    (V.premise_proof, V.premise_type),
    (V.premise_proof1, V.premise_type1),
    (V.premise_proof2, V.premise_type2),
    (V.premise_proof3, V.premise_type3),
    (V.premise_proof4, V.premise_type4),
    (V.premise_proof5, V.premise_type5),
)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 260932434 to 260914517, -17917 (-0.0069%), by the twin
#: contract change: nine `test` wrappers, one `collapse` and one `is-member`
#: left the engine for Python's own `assert` and `in`, and the three `bind!`
#: forms and sixteen `add-atom` forms became name bindings and `space += atom`.
#: The proof searches themselves did not move, and they are essentially the
#: whole cost. Against the example's 261045527 the ratio is 0.9995 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/reasoning/nilbc.metta`]. Prior: RE-PINNED at 260932434, -95, when
#: the base clause's anonymous variable became a singleton `$_`; ADDED
#: 2026-08-22 at 260932529 by the wave-3 twin baseline.
BUDGET = 260914517


def typed(term, kind):
    """`(: term kind)`, the declaration term. The design's own `typed` builder,
    written here because the library does not export one yet.
    """  # noqa: D205  -- one continuous statement, not summary-and-body prose
    return S[":"](term, kind)


def eq(left, right):
    """`(⟨=⟩ left right)`, Metamath equality."""
    return S["⟨=⟩"](left, right)


def plus(left, right):
    """`(⟨+⟩ left right)`, Metamath addition."""
    return S["⟨+⟩"](left, right)


def implies(premise, conclusion):
    """`(⟨->⟩ premise conclusion)`, Metamath implication."""
    return S["⟨->⟩"](premise, conclusion)


def _chain(premises):
    """The `bc` clause for `premises` premises, the example's shape written once.

    `(= (bc $kb (S $depth) (: ($rule $p1 ... $pn) $thm))
        (let* (((: $rule (-> (: $p1 $t1) ... $thm)) (bc $kb $depth <that>))
               ((: $pi $ti) (bc $kb $depth (: $pi $ti))) ...)
          (: ($rule $p1 ... $pn) $thm)))`
    """
    pairs = PREMISE[:1] if premises == 1 else PREMISE[1 : premises + 1]
    abstraction = typed(V.proof_rule,
                        S["->"](*[typed(proof, kind) for proof, kind in pairs], V.theorem))
    recurse = [(abstraction, S.bc(V.knowledge_base, V.depth, abstraction))]
    recurse += [
        (typed(proof, kind), S.bc(V.knowledge_base, V.depth, typed(proof, kind)))
        for proof, kind in pairs
    ]
    fulfilled = typed((V.proof_rule, *(proof for proof, _ in pairs)), V.theorem)
    return equation(S.bc(V.knowledge_base, S.S(V.depth), fulfilled)).to(
        S["let*"](tuple(recurse), fulfilled)
    )


def twin(m):
    """Three proof searches over three knowledge bases, and the proofs they build."""
    # Nat, and the casts between it and Number.
    m += typed(S.Nat, S.Type)
    m += typed(S.Z, S.Nat)
    m += typed(S.S, S["->"](S.Nat, S.Nat))
    m += typed(S.fromNumber, S["->"](S.Number, S.Nat))
    m += equation(S.fromNumber(V.n)).to(S["if"](V.n <= 0, S.Z, S.S(S.fromNumber(V.n - 1))))
    m += typed(S.fromNat, S["->"](S.Nat, S.Number))
    m += equation(S.fromNat(S.Z)).to(0)
    m += equation(S.fromNat(S.S(V.k))).to((PLUS, 1, S.fromNat(V.k)))

    # The chainer: a knowledge base, a maximum depth, a query, an answer.
    m += typed(S.bc, S["->"](V.a, S.Nat, V.b, V.b))

    # Base case: the query is destructured in the BODY rather than the head,
    # because a head parameter of the form (: $x $t) is an in-place type
    # annotation and would ask the engine to check the proof's type.
    m += equation(S.bc(V.knowledge_base, V._, V.query)).to(
        S.let(typed(V.proof, V.theorem),
              V.query,
              S.match(V.knowledge_base, typed(V.proof, V.theorem), typed(V.proof, V.theorem)))
    )
    for premises in range(1, 6):
        m += _chain(premises)

    # EASY: term and wff are ignored, and Metamath implication is replaced by
    # the arrow type. Equality is right Euclidean, and zero is a right identity.
    kbe = m.space(KBE.name)
    kbe += typed(S.a1, S["->"](typed(V.ter, eq(V.t, V.r)),
                               typed(V.tes, eq(V.t, V.s)),
                               eq(V.r, V.s)))
    kbe += typed(S.a2, eq(plus(V.t, ZERO), V.t))

    # Prove that equality is reflexive. The answer carries a free variable, so
    # the claim is alpha-equality rather than identity.
    reflexive, = m.eval(S.bc(KBE, S.fromNumber(1), typed(V.prf, eq(V.t, V.t))))
    assert alpha_eq(reflexive, typed(S.a1(S.a2, S.a2), eq(V.t, V.t)))

    # MEDIUM: the same, with the term and wff types used.
    kbm = m.space(KBM.name)
    kbm += typed(ZERO, TERM)
    kbm += typed(S["⟨+⟩"], S["->"](typed(V.t, TERM), typed(V.r, TERM), TERM))
    kbm += typed(S["⟨=⟩"], S["->"](typed(V.t, TERM), typed(V.r, TERM), WFF))
    kbm += typed(S.a1, S["->"](typed(V.t, TERM), typed(V.r, TERM), typed(V.s, TERM),
                               typed(V.ter, eq(V.t, V.r)), typed(V.tes, eq(V.t, V.s)),
                               eq(V.r, V.s)))
    kbm += typed(S.a2, S["->"](typed(V.t, TERM), eq(plus(V.t, ZERO), V.t)))
    kbm += typed(TT, TERM)

    # Several proofs come back at this depth, so the claim is membership.
    expected = typed(S.a1(plus(TT, ZERO), TT, TT, S.a2(TT), S.a2(TT)), eq(TT, TT))
    assert expected in m.eval(S.bc(KBM, S.fromNumber(3), typed(V.prf, eq(TT, TT))))

    # HARD: Metamath's own implication, and modus ponens with the major premise
    # first to speed the search up.
    kbh = m.space(KBH.name)
    kbh += typed(ZERO, TERM)
    kbh += typed(S["⟨+⟩"], S["->"](typed(V.t, TERM), typed(V.r, TERM), TERM))
    kbh += typed(S["⟨=⟩"], S["->"](typed(V.t, TERM), typed(V.r, TERM), WFF))
    kbh += typed(S["⟨->⟩"], S["->"](typed(V.P, WFF), typed(V.Q, WFF), WFF))
    kbh += typed(S.a1, S["->"](typed(V.t, TERM), typed(V.r, TERM), typed(V.s, TERM),
                               implies(eq(V.t, V.r), implies(eq(V.t, V.s), eq(V.r, V.s)))))
    kbh += typed(S.a2, S["->"](typed(V.t, TERM), eq(plus(V.t, ZERO), V.t)))
    kbh += typed(S.mp, S["->"](typed(V.maj, implies(V.P, V.Q)),
                               typed(V.P, WFF), typed(V.Q, WFF), typed(V.min, V.P),
                               V.Q))
    kbh += typed(TT, TERM)

    t_plus_zero = plus(TT, ZERO)
    sum_is_t = eq(t_plus_zero, TT)
    t_is_t = eq(TT, TT)

    # If t = t and t = t, then t = t.
    assert m.eval(S.bc(KBH, S.fromNumber(1),
                       typed(V.prf, implies(t_is_t, implies(t_is_t, t_is_t))))) == [
        typed(S.a1(TT, TT, TT), implies(t_is_t, implies(t_is_t, t_is_t)))
    ]

    # If t + 0 = t and t + 0 = t, then t = t.
    assert m.eval(S.bc(KBH, S.fromNumber(2),
                       typed(V.prf, implies(sum_is_t, implies(sum_is_t, t_is_t))))) == [
        typed(S.a1(t_plus_zero, TT, TT), implies(sum_is_t, implies(sum_is_t, t_is_t)))
    ]

    # t + 0 = t.
    assert m.eval(S.bc(KBH, S.fromNumber(1), typed(V.prf, sum_is_t))) == [
        typed(S.a2(TT), sum_is_t)
    ]

    # Both equalities are well formed formulas.
    assert m.eval(S.bc(KBH, S.fromNumber(2), typed(sum_is_t, WFF))) == [typed(sum_is_t, WFF)]
    assert m.eval(S.bc(KBH, S.fromNumber(1), typed(t_is_t, WFF))) == [typed(t_is_t, WFF)]

    # If t + 0 = t, then t = t: one modus ponens over the two axioms.
    one_step = S.mp(S.a1(t_plus_zero, TT, TT), sum_is_t, implies(sum_is_t, t_is_t), S.a2(TT))
    assert m.eval(S.bc(KBH, S.fromNumber(4),
                       typed(V.prf, implies(sum_is_t, t_is_t)))) == [
        typed(one_step, implies(sum_is_t, t_is_t))
    ]

    # And equality is reflexive: modus ponens twice over the same two axioms.
    assert m.eval(S.bc(KBH, S.fromNumber(5), typed(V.prf, t_is_t))) == [
        typed(S.mp(one_step, sum_is_t, t_is_t, S.a2(TT)), t_is_t)
    ]
