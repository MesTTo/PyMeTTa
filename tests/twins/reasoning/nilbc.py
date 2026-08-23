"""Purpose: examples/reasoning/nilbc.metta in Python: a dependently-typed backward chainer.

A proof search over Metamath's demo0, in three of the example's four levels of
difficulty: easy ignores the term and wff types, medium uses them, and hard adds
Metamath's own implication. Each level is a space of axioms, and each claim asks
the chainer to build a proof term and checks the one it built.

The chainer's five recursive clauses are ONE shape repeated for one through five
premises: recurse on the abstraction, recurse on each premise, answer the
fulfilled query. The example writes the five out; here `_chain(n)` writes the
n-premise clause and a `range` supplies the five, so the shape is stated once.
The Metamath vocabulary gets Python functions for the same reason: `eq`, `plus`
and `implies` turn a wall of angle brackets into readable logic, and `typed` is
the exported builder for the declaration term the whole file is written in.

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

Each is a residue entry against P14.4. The three knowledge bases are ordinary
spaces, and the Python variable IS each one's binding, so none of them needs a
name: a space crosses a term position as itself, which is what `bc` receives.

The example's variables carry genuine underscores (`$knowledge_base`,
`$premise_proof1`), and the factory attribute door maps every underscore to a
hyphen, so those names take the bracket.

Known issue, and it decides how every claim below is written: a call carrying
a caller variable answers that variable's BINDINGS and drops the value, and
every query here passes `(: $prf <theorem>)`, whose ANSWER is the proof term
the chainer built. So the claims read the form. They should read
`m.fn.bc(kbh, S.fromNumber(1), typed(V.prf, sum_is_t)) == [...]`.
"""

import petta
from petta import S, V, equation, fn, if_, typed

#: Metamath's vocabulary, as this example spells it.
TERM, WFF, ZERO, TT = S["⟨term⟩"], S["⟨wff⟩"], S["⟨0⟩"], S["⟨t⟩"]

#: The addition head, needed with a GROUND left operand, where Python's own
#: `+` would compute instead of building.
PLUS = fn["+"]

#: The example's premise variables, in its own spelling: the one-premise clause
#: writes them without a digit and the rest number them from one.
PREMISE = (
    (V["premise_proof"], V["premise_type"]),
    (V["premise_proof1"], V["premise_type1"]),
    (V["premise_proof2"], V["premise_type2"]),
    (V["premise_proof3"], V["premise_type3"]),
    (V["premise_proof4"], V["premise_type4"]),
    (V["premise_proof5"], V["premise_type5"]),
)

#: The chainer's own parameters, both underscored in the example.
KB, RULE = V["knowledge_base"], V["proof_rule"]

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


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
    abstraction = typed(RULE,
                        S["->"](*[typed(proof, kind) for proof, kind in pairs], V.theorem))
    recurse = [(abstraction, S.bc(KB, V.depth, abstraction))]
    recurse += [
        (typed(proof, kind), S.bc(KB, V.depth, typed(proof, kind)))
        for proof, kind in pairs
    ]
    fulfilled = typed((RULE, *(proof for proof, _ in pairs)), V.theorem)
    return equation(S.bc(KB, S.S(V.depth), fulfilled)).to(
        fn["let*"](tuple(recurse), fulfilled)  # rung: a let* whose bindings are proof-search calls (P14.4)
    )


def twin(m):
    """Three proof searches over three knowledge bases, and the proofs they build."""
    # Nat, and the casts between it and Number.
    m += typed(S.Nat, S.Type)
    m += typed(S.Z, S.Nat)
    m += typed(S.S, S["->"](S.Nat, S.Nat))
    m += typed(S.fromNumber, S["->"](S.Number, S.Nat))
    m += equation(S.fromNumber(V.n)).to(if_(V.n <= 0, S.Z, S.S(S.fromNumber(V.n - 1))))
    m += typed(S.fromNat, S["->"](S.Nat, S.Number))
    m += equation(S.fromNat(S.Z)).to(0)
    m += equation(S.fromNat(S.S(V.k))).to(PLUS(1, S.fromNat(V.k)))

    # The chainer: a knowledge base, a maximum depth, a query, an answer.
    m += typed(S.bc, S["->"](V.a, S.Nat, V.b, V.b))

    # Base case: the query is destructured in the BODY rather than the head,
    # because a head parameter of the form (: $x $t) is an in-place type
    # annotation and would ask the engine to check the proof's type.
    m += equation(S.bc(KB, V._, V.query)).to(
        fn.let(typed(V.proof, V.theorem),  # rung: a let whose PATTERN is a declaration term (P14.4)
               V.query,
               fn.match(KB, typed(V.proof, V.theorem), typed(V.proof, V.theorem)))  # rung: a match whose space is this clause's PARAMETER (P14.4)
    )
    for premises in range(1, 6):
        m += _chain(premises)

    # EASY: term and wff are ignored, and Metamath implication is replaced by
    # the arrow type. Equality is right Euclidean, and zero is a right identity.
    kbe = petta.space()
    kbe += typed(S.a1, S["->"](typed(V.ter, eq(V.t, V.r)),
                               typed(V.tes, eq(V.t, V.s)),
                               eq(V.r, V.s)))
    kbe += typed(S.a2, eq(plus(V.t, ZERO), V.t))

    # Prove that equality is reflexive. The answer carries a free variable, so
    # the claim is alpha-equality rather than identity.
    reflexive, = m.eval(S.bc(kbe, S.fromNumber(1), typed(V.prf, eq(V.t, V.t))))
    assert reflexive.alpha_eq(typed(S.a1(S.a2, S.a2), eq(V.t, V.t)))

    # MEDIUM: the same, with the term and wff types used.
    kbm = petta.space()
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
    assert expected in m.eval(S.bc(kbm, S.fromNumber(3), typed(V.prf, eq(TT, TT))))

    # HARD: Metamath's own implication, and modus ponens with the major premise
    # first to speed the search up.
    kbh = petta.space()
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
    assert m.eval(S.bc(kbh, S.fromNumber(1),
                       typed(V.prf, implies(t_is_t, implies(t_is_t, t_is_t))))) == [
        typed(S.a1(TT, TT, TT), implies(t_is_t, implies(t_is_t, t_is_t)))
    ]

    # If t + 0 = t and t + 0 = t, then t = t.
    assert m.eval(S.bc(kbh, S.fromNumber(2),
                       typed(V.prf, implies(sum_is_t, implies(sum_is_t, t_is_t))))) == [
        typed(S.a1(t_plus_zero, TT, TT), implies(sum_is_t, implies(sum_is_t, t_is_t)))
    ]

    # t + 0 = t.
    assert m.eval(S.bc(kbh, S.fromNumber(1), typed(V.prf, sum_is_t))) == [
        typed(S.a2(TT), sum_is_t)
    ]

    # Both equalities are well formed formulas.
    assert m.eval(S.bc(kbh, S.fromNumber(2), typed(sum_is_t, WFF))) == [typed(sum_is_t, WFF)]
    assert m.eval(S.bc(kbh, S.fromNumber(1), typed(t_is_t, WFF))) == [typed(t_is_t, WFF)]

    # If t + 0 = t, then t = t: one modus ponens over the two axioms.
    one_step = S.mp(S.a1(t_plus_zero, TT, TT), sum_is_t, implies(sum_is_t, t_is_t), S.a2(TT))
    assert m.eval(S.bc(kbh, S.fromNumber(4),
                       typed(V.prf, implies(sum_is_t, t_is_t)))) == [
        typed(one_step, implies(sum_is_t, t_is_t))
    ]

    # And equality is reflexive: modus ponens twice over the same two axioms.
    assert m.eval(S.bc(kbh, S.fromNumber(5), typed(V.prf, t_is_t))) == [
        typed(S.mp(one_step, sum_is_t, t_is_t, S.a2(TT)), t_is_t)
    ]
