"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/04-nilbc.metta in Python: a dependently-typed backward chainer.

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

Every head that destructures is a `@m.rules` bundle, the door for equations
whose heads are structures or symbols: the six `bc` clauses destructure
`(S $depth)` and `(: ($rule $p1 ...) $thm)`, and `fromNat`'s two clauses have a
symbol head and a structural one. `fromNumber` is an ordinary compiled function
whose declaration is its signature, and `Nat` is a Python class so the arrow
can be built from Python types. The bundles' bodies are stored `let*`, `let`
and `match` terms, and a rules body EXECUTES, so those three are built by
naming their heads (friction, P14.4).

The three knowledge bases are ordinary spaces, and the Python variable IS each
one's binding, so none of them needs a name: a space crosses a term position as
itself, which is what `bc` receives.

The example's variables carry genuine underscores (`$knowledge_base`,
`$premise_proof1`), and the factory attribute door maps every underscore to a
hyphen, so those names take the bracket.

Every claim is the chainer CALLED, `m.fn.bc(kbh, S.fromNumber(1), typed(V.prf,
sum_is_t))`. Each query passes `(: $prf <theorem>)` and what comes back is the
proof term the chainer built, because a call answers its value whether or not
its arguments carry variables.
"""

import metta
from metta import S, V, arrow, equation, typed


class Nat:
    """The MeTTa type `Nat`, which `fromNumber` answers and `fromNat` reads."""


#: Metamath's vocabulary, as this example spells it.
TERM, WFF, ZERO, TT = S["⟨term⟩"], S["⟨wff⟩"], S["⟨0⟩"], S["⟨t⟩"]

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
    abstraction = typed(RULE, arrow(*[typed(proof, kind) for proof, kind in pairs], V.theorem))
    recurse = [(abstraction, S.bc(KB, V.depth, abstraction))]
    recurse += [
        (typed(proof, kind), S.bc(KB, V.depth, typed(proof, kind))) for proof, kind in pairs
    ]
    fulfilled = typed((RULE, *(proof for proof, _ in pairs)), V.theorem)
    return equation(S.bc(KB, S.S(V.depth), fulfilled)).to(
        S["let*"](
            tuple(recurse), fulfilled
        )  # rung: a stored let* whose bindings are proof-search calls (P14.4)
    )


def twin(m):
    """Three proof searches over three knowledge bases, and the proofs they build."""
    # Nat, and the casts between it and Number.
    # (: Nat Type) (: Z Nat) (: S (-> Nat Nat))
    m += typed(S.Nat, S.Type)
    m += typed(S.Z, Nat)
    m += typed(S.S, arrow(Nat, Nat))

    @m.define(name="fromNumber")
    def from_number(n: int) -> Nat:
        """(: fromNumber (-> Number Nat)), counting down to Z.

        Every claim below writes `(fromNumber n)` as a TERM inside `bc`'s
        argument, exactly as the example does, so this name installs the
        equation and is never called from Python.
        """
        # (= (fromNumber $n) (if (<= $n 0) Z (S (fromNumber (- $n 1)))))
        if n <= 0:
            return S.Z
        return S.S(from_number(n - 1))

    m += typed(S.fromNat, arrow(Nat, int))

    @m.rules
    def counting(step):
        """(= (fromNat Z) 0) and (= (fromNat (S $k)) (+ 1 (fromNat $k)))."""
        yield equation(S.fromNat(S.Z)).to(0)
        yield equation(S.fromNat(S.S(step))).to(1 + S.fromNat(step))

    # The chainer: a knowledge base, a maximum depth, a query, an answer.
    # (: bc (-> $a Nat $b $b))
    m += typed(S.bc, arrow(V.a, Nat, V.b, V.b))

    @m.rules
    def chainer():
        """The base case, and the five clauses `_chain` writes from one shape."""
        # Base case: the query is destructured in the BODY rather than the head,
        # because a head parameter of the form (: $x $t) is an in-place type
        # annotation and would ask the engine to check the proof's type.
        # (= (bc $kb $_ $query)
        #    (let (: $proof $theorem) $query
        #         (match $kb (: $proof $theorem) (: $proof $theorem))))
        yield equation(S.bc(KB, V._, V.query)).to(
            S.let(
                typed(
                    V.proof, V.theorem
                ),  # rung: a stored let whose PATTERN is a declaration term (P14.4)
                V.query,
                S.match(KB, typed(V.proof, V.theorem), typed(V.proof, V.theorem)),
            )  # rung: a stored match whose space is this clause's PARAMETER (P14.4)
        )
        for premises in range(1, 6):
            yield _chain(premises)

    # EASY: term and wff are ignored, and Metamath implication is replaced by
    # the arrow type. Equality is right Euclidean, and zero is a right identity.
    kbe = metta.space()
    kbe += typed(S.a1, arrow(typed(V.ter, eq(V.t, V.r)), typed(V.tes, eq(V.t, V.s)), eq(V.r, V.s)))
    kbe += typed(S.a2, eq(plus(V.t, ZERO), V.t))

    # Prove that equality is reflexive. The answer carries a free variable, so
    # the claim is alpha-equality rather than identity.
    reflexive = m.fn.bc(kbe, S.fromNumber(1), typed(V.prf, eq(V.t, V.t))).one()
    assert reflexive.alpha_eq(typed(S.a1(S.a2, S.a2), eq(V.t, V.t)))

    # MEDIUM: the same, with the term and wff types used.
    kbm = metta.space()
    kbm += typed(ZERO, TERM)
    kbm += typed(S["⟨+⟩"], arrow(typed(V.t, TERM), typed(V.r, TERM), TERM))
    kbm += typed(S["⟨=⟩"], arrow(typed(V.t, TERM), typed(V.r, TERM), WFF))
    kbm += typed(
        S.a1,
        arrow(
            typed(V.t, TERM),
            typed(V.r, TERM),
            typed(V.s, TERM),
            typed(V.ter, eq(V.t, V.r)),
            typed(V.tes, eq(V.t, V.s)),
            eq(V.r, V.s),
        ),
    )
    kbm += typed(S.a2, arrow(typed(V.t, TERM), eq(plus(V.t, ZERO), V.t)))
    kbm += typed(TT, TERM)

    # Several proofs come back at this depth, so the claim is membership.
    expected = typed(S.a1(plus(TT, ZERO), TT, TT, S.a2(TT), S.a2(TT)), eq(TT, TT))
    assert expected in m.fn.bc(kbm, S.fromNumber(3), typed(V.prf, eq(TT, TT)))

    # HARD: Metamath's own implication, and modus ponens with the major premise
    # first to speed the search up.
    kbh = metta.space()
    kbh += typed(ZERO, TERM)
    kbh += typed(S["⟨+⟩"], arrow(typed(V.t, TERM), typed(V.r, TERM), TERM))
    kbh += typed(S["⟨=⟩"], arrow(typed(V.t, TERM), typed(V.r, TERM), WFF))
    kbh += typed(S["⟨->⟩"], arrow(typed(V.P, WFF), typed(V.Q, WFF), WFF))
    kbh += typed(
        S.a1,
        arrow(
            typed(V.t, TERM),
            typed(V.r, TERM),
            typed(V.s, TERM),
            implies(eq(V.t, V.r), implies(eq(V.t, V.s), eq(V.r, V.s))),
        ),
    )
    kbh += typed(S.a2, arrow(typed(V.t, TERM), eq(plus(V.t, ZERO), V.t)))
    kbh += typed(
        S.mp,
        arrow(
            typed(V.maj, implies(V.P, V.Q)),
            typed(V.P, WFF),
            typed(V.Q, WFF),
            typed(V.min, V.P),
            V.Q,
        ),
    )
    kbh += typed(TT, TERM)

    t_plus_zero = plus(TT, ZERO)
    sum_is_t = eq(t_plus_zero, TT)
    t_is_t = eq(TT, TT)

    # If t = t and t = t, then t = t.
    assert m.fn.bc(
        kbh, S.fromNumber(1), typed(V.prf, implies(t_is_t, implies(t_is_t, t_is_t)))
    ) == [typed(S.a1(TT, TT, TT), implies(t_is_t, implies(t_is_t, t_is_t)))]

    # If t + 0 = t and t + 0 = t, then t = t.
    assert m.fn.bc(
        kbh, S.fromNumber(2), typed(V.prf, implies(sum_is_t, implies(sum_is_t, t_is_t)))
    ) == [typed(S.a1(t_plus_zero, TT, TT), implies(sum_is_t, implies(sum_is_t, t_is_t)))]

    # t + 0 = t.
    assert m.fn.bc(kbh, S.fromNumber(1), typed(V.prf, sum_is_t)) == [typed(S.a2(TT), sum_is_t)]

    # Both equalities are well formed formulas.
    assert m.fn.bc(kbh, S.fromNumber(2), typed(sum_is_t, WFF)) == [typed(sum_is_t, WFF)]
    assert m.fn.bc(kbh, S.fromNumber(1), typed(t_is_t, WFF)) == [typed(t_is_t, WFF)]

    # If t + 0 = t, then t = t: one modus ponens over the two axioms.
    one_step = S.mp(S.a1(t_plus_zero, TT, TT), sum_is_t, implies(sum_is_t, t_is_t), S.a2(TT))
    assert m.fn.bc(kbh, S.fromNumber(4), typed(V.prf, implies(sum_is_t, t_is_t))) == [
        typed(one_step, implies(sum_is_t, t_is_t))
    ]

    # And equality is reflexive: modus ponens twice over the same two axioms.
    assert m.fn.bc(kbh, S.fromNumber(5), typed(V.prf, t_is_t)) == [
        typed(S.mp(one_step, sum_is_t, t_is_t, S.a2(TT)), t_is_t)
    ]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=67c9b9a4e7204e9537c018de6e8c23ddfe842bed].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 128021219 to 128021356, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 128021356 to 128021346, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 128021346 to 128021311, on the release tree:
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
#: RE-PINNED 2026-08-25, 128021311 to 130075530, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration]. This
#: twin's +1.6% is the numeric-admission test at the arithmetic
#: FAILURE boundary: a backtracking search fails comparisons by the
#: million, and each failed op now asks once whether an operand is a
#: host numeric object before refusing - the price of (+ np-scalar 1)
#: computing, constant per failed op, zero on the success path.
#: RE-PINNED 2026-08-26, 130075530 to 130071186 (-4344), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 130071186 to 130071194 (+8), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 130071194 to 130071186 (-8), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 130071186 to 130066359 (-4827), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 130066359 to 283662908 (+153596549), one corpus
#: pricing pass on the merged tree for the 2026-08-27..09-01 engine span
#: (8e75816d..f0744f86), whose four mechanisms are decomposed per lane in
#: benchmarks/baseline.json and ai-parametricity-audit.md passes 10-16: the
#: seam-offer routing and its one-wrap fold (net +8 inferences per evaluation),
#: the strict-scope removal leaving the eval path, the doubling cursor chunk
#: (~3 engine-side inferences per answer replacing per-answer crossings; drains
#: halve on CPU), and the aligned-path work; thirteen twins additionally carry
#: the idiom sweep's local deltas tabulated in the twin-idioms notes, none
#: above 347 [measured 2026-09-01: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 283662908 to 283662869 (-39), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 283662869 to 283663702 (+833), generic Python
#: operators now dispatch through live protocols while source twins explicitly
#: name relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 283663702 to 283662927 (-775), exact numeric
#: annotations retain native operator heads, publish MeTTa type declarations,
#: and leave relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 283662927 to 288291872 (+4628945), static contract
#: discharge and policy-stable recompilation [measured 2026-09-02: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 288291872 to 288143587 (-148285), static contract
#: discharge with policy checks confined to invalidated contracts [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 288143587 to 288143596 (+9), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 288143596 to 292659842 (+4516246), the one pricing
#: pass at the 0.8.0 release cut, and trunk's own movement rather than any
#: mechanism in this twin: each pin was taken on the base its own branch had,
#: and the September merge wave has moved the engine's clause layout, the
#: evaluation path and the library's write doors since [measured 2026-09-06:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 292659842 to 309864840 (+17204998), trunk's own
#: movement since each twin's pin was taken on the base its own branch had:
#: twenty-two first-parent steps between the 0.8.0 release re-pin and this
#: tree, the prelude's move into Prolog the largest of them at +39 to +115 a
#: twin and -65,806 on the error algebra, the live-views merge -45 on every
#: twin that writes, the catalog and get-type repairs +169 on the types
#: chapter, and the rest SWI clause-indexing layout as the boot image grew;
#: this tree also stores the compiled default space operand as &self rather
#: than a (context-space) call [measured 2026-09-07: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 309864840 to 309864878 (+38), the merges between this
#: lane's burn-down base (dfd5003f) and the tree that merged it, placed by a
#: first-parent ladder through the lane's own driver over ten twins at
#: f8c4b672, 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 309864878 to 309863090 (-1788),
#: metta_substitute_self/3 probes the term for the text &self before walking
#: it, one C write and one C substring probe, where the twins-lane merge's one-
#: equation door (08f6f4df) walked every natively added equation in a named
#: space unconditionally, so every twin that adds or defines an equation in a
#: named space drops by about that equation's size in inferences; the same
#: probe now guards the reader's per-form door (record_translated_from/4), the
#: deferred door's fallback (stored_equation_source/4), a batch's arriving
#: equations (mark_or_translate_equation/5) and the removal probe
#: (remove_equation/6), where the walk is new and skipped for a term that never
#: says &self, and a twin that only removes or re-adds such equations pays the
#: two-inference probe per door crossing instead. Every twin here re-reads its
#: budget on this tree, minimum of three fresh processes [measured 2026-09-08:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 309863090 to 309861371 (-1719), the evaluation-fuel
#: scope marker is a trailed write (fix/every-intermittent-root-caused,
#: f6e05ca9): `$metta_fuel_scope` is written open with b_setval/2 at scope open
#: and read with b_getval/2 where nb_current/2 used to answer, so an abandoned
#: scope closes itself when an exception unwinds the trail and the cleanup is
#: the fast ordinary exit, and every runnable form pays fewer inferences per
#: scope; a twin drops by about the count of its runnables, and the engine
#: bench reads evaluate and translate 1642 lower each on the same tree. Every
#: twin here re-reads its budget on the merged tree, minimum of three fresh
#: processes [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 309861371 to 309861389 (+18), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 309861371 to 309861600 (+229), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 309861600 to 309861610 (+10), The engine and library
#: module boundaries retain explicit lookup owners, including host registration
#: and returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 309861610 to 309861699 (+89), the module boundary
#: merged with trunk's later packages (refactor/engine-and-libraries-as-modules
#: at b64291369): every space now resolves through one more chain link, prelude
#: -> metta_engine -> user, the engine's measured export list is imported into
#: the host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 309861389 to 309861444 (+55), The typed host door
#: catalog is published before user code. Its declarations change catalog
#: lookup indexes; generated public names bind directly to their existing
#: bodies [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 309861444 to 309861739 (+295), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 309861739 to 309861980 (+241), structured concurrency
#: landed (feat/structured-concurrency merged at f80cc416d): every space mint
#: records its allocation in the library's lifetime rows, every write and run
#: pays the ownership hook and every drop asks the library whether a scope owns
#: the name, measured on a pristine control as 32 per mint, 2 per write and 44
#: per drop with none per read; measured on the merged tree [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 309861699 to 309862456 (+757), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 309862456 to 309862396 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 309862396 to 309862722 (+326), tokens as storage
#: landed (feat/tokens-as-storage merged): every native occurrence carries a (t
#: actor generation) token as the trailing argument of its storage clause,
#: minted through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=WORKTREE].
BUDGET = 309862722

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 @doc): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "ffea9148a2d897adf25352af0819305ae1dddf577976d8e8e7516bd12403fa6b"
