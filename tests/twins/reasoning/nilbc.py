"""The Python twin of examples/reasoning/nilbc.metta: a dependently-typed chainer.

The backward chainer's five recursive clauses are ONE shape repeated for one
through five premises: recurse on the abstraction, recurse on each premise,
answer the fulfilled query. The example writes the five out; here `_chain(n)`
writes the n-premise clause and a `range` supplies the five, so the shape is
stated once and the file says what the example's own comments say it does.

Everything stays at the term door, and the reasons are in the clauses:

- every `bc` clause destructures in the HEAD (`(S $depth)` and
  `(: ($rule $p1 ...) $thm)`), and a compiled head pattern must be a literal;
- `fromNat`'s two clauses have a SYMBOL head pattern (`Z`) and a structural one
  (`(S $k)`), which a stacked Python clause's literal default cannot spell;
- `fromNumber` would compile except for one collision: its body builds `(S ...)`
  and a capitalised free name in a compiled body is a data constructor UNLESS
  it is a module binding, which `S` is here because `S` is the symbol factory
  every twin imports. The refusal is right (silently dropping a host value would
  be worse) and the collision is real.

Each is a residue entry against P14.4. Where an operator builds the term it is
used: `V.n <= 0` is `(<= $n 0)` and `V.n - 1` is `(- $n 1)`. `(+ 1 (fromNat $k))`
is the tuple `(PLUS, 1, ...)`, because `1 + <expr>` reflects into `__radd__` and
would build `(+ 1 ...)` correctly, while `1 <= $n` would reflect `<=` into `>=`
and build a different term; the tuple keeps one rule for the whole file.
"""

from petta import S, V, equation, val

#: The addition head, needed with a GROUND left operand.
PLUS = S["+"]

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

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 260932529 to 260932434, -95 (-0.00004%), by the base
#: clause's anonymous variable. The wave-3 twin minted `$_1232` for the example's
#: own `$_`; this one writes `$_`, which occurs once in that clause and so
#: compiles as a singleton the engine never has to bind. Everything else in the
#: file is byte-identical at the atom level, `_chain` included, which the
#: atom-level differential confirms. Prior: ADDED 2026-08-22 at 260932529 by the
#: wave-3 twin baseline.
BUDGET = 260932434


def _chain(premises):
    """The `bc` clause for `premises` premises, the example's shape written once.

    `(= (bc $kb (S $depth) (: ($rule $p1 ... $pn) $thm))
        (let* (((: $rule (-> (: $p1 $t1) ... $thm)) (bc $kb $depth <that>))
               ((: $pi $ti) (bc $kb $depth (: $pi $ti))) ...)
          (: ($rule $p1 ... $pn) $thm)))`
    """
    pairs = PREMISE[:1] if premises == 1 else PREMISE[1 : premises + 1]
    abstraction = S[":"](
        V.proof_rule,
        S["->"](*[S[":"](proof, kind) for proof, kind in pairs], V.theorem),
    )
    recurse = [(abstraction, S.bc(V.knowledge_base, V.depth, abstraction))]
    recurse += [
        (S[":"](proof, kind), S.bc(V.knowledge_base, V.depth, S[":"](proof, kind)))
        for proof, kind in pairs
    ]
    fulfilled = S[":"]((V.proof_rule, *(proof for proof, _ in pairs)), V.theorem)
    return equation(S.bc(V.knowledge_base, S.S(V.depth), fulfilled)).to(
        S["let*"](tuple(recurse), fulfilled)
    )


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Define Nat
    # (: Nat Type)
    m += S[":"](S.Nat, S.Type)
    # (: Z Nat)
    m += S[":"](S.Z, S.Nat)
    # (: S (-> Nat Nat))
    m += S[":"](S.S, S["->"](S.Nat, S.Nat))

    # Define cast functions between Nat and Number
    # (: fromNumber (-> Number Nat))
    m += S[":"](S.fromNumber, S["->"](S.Number, S.Nat))
    # (= (fromNumber $n) (if (<= $n 0) Z (S (fromNumber (- $n 1)))))
    m += equation(S.fromNumber(V.n)).to(
        S["if"](V.n <= 0, S.Z, S.S(S.fromNumber(V.n - 1)))
    )
    # (: fromNat (-> Nat Number))
    m += S[":"](S.fromNat, S["->"](S.Nat, S.Number))
    # (= (fromNat Z) 0)
    m += equation(S.fromNat(S.Z)).to(0)
    # (= (fromNat (S $k)) (+ 1 (fromNat $k)))
    m += equation(S.fromNat(S.S(V.k))).to((PLUS, 1, S.fromNat(V.k)))

    # (: bc (-> $a                            ; Knowledge base space
    #           Nat                           ; Maximum depth
    #           $b                            ; Query
    #           $b))                          ; Result
    m += S[":"](S.bc, S["->"](V.a, S.Nat, V.b, V.b))

    # Base case
    # (= (bc $knowledge_base $_ $query)
    #    (let (: $proof $theorem) $query
    #         (match $knowledge_base (: $proof $theorem) (: $proof $theorem))))
    m += equation(S.bc(V.knowledge_base, V._, V.query)).to(
        S.let(
            S[":"](V.proof, V.theorem),
            V.query,
            S.match(
                V.knowledge_base,
                S[":"](V.proof, V.theorem),
                S[":"](V.proof, V.theorem),
            ),
        )
    )

    # Recursive step, one clause per premise count, exactly as the example
    # writes its five.
    for premises in range(1, 6):
        m += _chain(premises)

    # !(bind! &kbe (new-space))
    yield m.eval(S["bind!"](S["&kbe"], S["new-space"]()))

    # !(add-atom &kbe (: a1 (-> (: $ter (⟨=⟩ $t $r))
    #                           (: $tes (⟨=⟩ $t $s))
    #                           (⟨=⟩ $r $s))))
    yield m.eval(
        S["add-atom"](S["&kbe"],
            S[":"](S.a1,
                S["->"](S[":"](V.ter, S["⟨=⟩"](V.t, V.r)),
                    S[":"](V.tes, S["⟨=⟩"](V.t, V.s)),
                    S["⟨=⟩"](V.r, V.s))))
    )

    # !(add-atom &kbe (: a2 (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t)))
    yield m.eval(
        S["add-atom"](S["&kbe"],
            S[":"](S.a2, S["⟨=⟩"](S["⟨+⟩"](V.t, S["⟨0⟩"]), V.t)))
    )

    # !(test
    #   (bc &kbe (fromNumber 1) (: $prf (⟨=⟩ $t $t)))
    #   (: (a1 a2 a2) (⟨=⟩ $t $t)))
    yield m.eval(
        S.test(S.bc(S["&kbe"],
                S.fromNumber(1),
                S[":"](V.prf, S["⟨=⟩"](V.t, V.t))),
            S[":"](S.a1(S.a2, S.a2), S["⟨=⟩"](V.t, V.t)))
    )

    # !(bind! &kbm (new-space))
    yield m.eval(S["bind!"](S["&kbm"], S["new-space"]()))

    # !(add-atom &kbm (: ⟨0⟩ ⟨term⟩))
    yield m.eval(S["add-atom"](S["&kbm"], S[":"](S["⟨0⟩"], S["⟨term⟩"])))

    # !(add-atom &kbm (: ⟨+⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨term⟩)))
    yield m.eval(
        S["add-atom"](S["&kbm"],
            S[":"](S["⟨+⟩"],
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S["⟨term⟩"])))
    )

    # !(add-atom &kbm (: ⟨=⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨wff⟩)))
    yield m.eval(
        S["add-atom"](S["&kbm"],
            S[":"](S["⟨=⟩"],
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S["⟨wff⟩"])))
    )

    # !(add-atom &kbm (: a1 (-> (: $t ⟨term⟩)
    #                           (: $r ⟨term⟩)
    #                           (: $s ⟨term⟩)
    #                           (: $ter (⟨=⟩ $t $r))
    #                           (: $tes (⟨=⟩ $t $s))
    #                           (⟨=⟩ $r $s))))
    yield m.eval(
        S["add-atom"](S["&kbm"],
            S[":"](S.a1,
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S[":"](V.s, S["⟨term⟩"]),
                    S[":"](V.ter, S["⟨=⟩"](V.t, V.r)),
                    S[":"](V.tes, S["⟨=⟩"](V.t, V.s)),
                    S["⟨=⟩"](V.r, V.s))))
    )

    # !(add-atom &kbm (: a2 (-> (: $t ⟨term⟩)
    #                           (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t))))
    yield m.eval(
        S["add-atom"](S["&kbm"],
            S[":"](S.a2,
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S["⟨=⟩"](S["⟨+⟩"](V.t, S["⟨0⟩"]), V.t))))
    )

    # !(add-atom &kbm (: ⟨t⟩ ⟨term⟩))
    yield m.eval(S["add-atom"](S["&kbm"], S[":"](S["⟨t⟩"], S["⟨term⟩"])))

    # !(test (is-member (: (a1 (⟨+⟩ ⟨t⟩ ⟨0⟩)
    #                          ⟨t⟩
    #                          ⟨t⟩
    #                          (a2 ⟨t⟩)
    #                          (a2 ⟨t⟩))
    #                      (⟨=⟩ ⟨t⟩ ⟨t⟩))
    #       (collapse (bc &kbm (fromNumber 3) (: $prf (⟨=⟩ ⟨t⟩ ⟨t⟩))))) true)
    yield m.eval(
        S.test(S["is-member"](S[":"](S.a1(S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]),
                        S["⟨t⟩"],
                        S["⟨t⟩"],
                        S.a2(S["⟨t⟩"]),
                        S.a2(S["⟨t⟩"])),
                    S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])),
                S.collapse(S.bc(S["&kbm"],
                        S.fromNumber(3),
                        S[":"](V.prf, S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]))))),
            TRUE)
    )

    # !(bind! &kbh (new-space))
    yield m.eval(S["bind!"](S["&kbh"], S["new-space"]()))

    # !(add-atom &kbh (: ⟨0⟩ ⟨term⟩))
    yield m.eval(S["add-atom"](S["&kbh"], S[":"](S["⟨0⟩"], S["⟨term⟩"])))

    # !(add-atom &kbh (: ⟨+⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨term⟩)))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S["⟨+⟩"],
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S["⟨term⟩"])))
    )

    # !(add-atom &kbh (: ⟨=⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨wff⟩)))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S["⟨=⟩"],
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S["⟨wff⟩"])))
    )

    # !(add-atom &kbh (: ⟨->⟩ (-> (: $P ⟨wff⟩)
    #                             (: $Q ⟨wff⟩)
    #                             ⟨wff⟩)))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S["⟨->⟩"],
                S["->"](S[":"](V.P, S["⟨wff⟩"]),
                    S[":"](V.Q, S["⟨wff⟩"]),
                    S["⟨wff⟩"])))
    )

    # !(add-atom &kbh (: a1 (-> (: $t ⟨term⟩)
    #                           (: $r ⟨term⟩)
    #                           (: $s ⟨term⟩)
    #                           (⟨->⟩ (⟨=⟩ $t $r) (⟨->⟩ (⟨=⟩ $t $s) (⟨=⟩ $r $s))))))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S.a1,
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S[":"](V.r, S["⟨term⟩"]),
                    S[":"](V.s, S["⟨term⟩"]),
                    S["⟨->⟩"](S["⟨=⟩"](V.t, V.r),
                        S["⟨->⟩"](S["⟨=⟩"](V.t, V.s),
                            S["⟨=⟩"](V.r, V.s))))))
    )

    # !(add-atom &kbh (: a2 (-> (: $t ⟨term⟩)
    #                           (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t))))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S.a2,
                S["->"](S[":"](V.t, S["⟨term⟩"]),
                    S["⟨=⟩"](S["⟨+⟩"](V.t, S["⟨0⟩"]), V.t))))
    )

    # !(add-atom &kbh (: mp (-> (: $maj (⟨->⟩ $P $Q))
    #                           (: $P ⟨wff⟩)
    #                           (: $Q ⟨wff⟩)
    #                           (: $min $P)
    #                           $Q)))
    yield m.eval(
        S["add-atom"](S["&kbh"],
            S[":"](S.mp,
                S["->"](S[":"](V.maj, S["⟨->⟩"](V.P, V.Q)),
                    S[":"](V.P, S["⟨wff⟩"]),
                    S[":"](V.Q, S["⟨wff⟩"]),
                    S[":"](V.min, V.P),
                    V.Q)))
    )

    # !(add-atom &kbh (: ⟨t⟩ ⟨term⟩))
    yield m.eval(S["add-atom"](S["&kbh"], S[":"](S["⟨t⟩"], S["⟨term⟩"])))

    # !(test
    #   (bc &kbh (fromNumber 1)
    #       (: $prf
    #          (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    #   (: (a1 ⟨t⟩ ⟨t⟩ ⟨t⟩)
    #      (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(1),
                S[":"](V.prf,
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]),
                        S["⟨->⟩"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]),
                            S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]))))),
            S[":"](S.a1(S["⟨t⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                S["⟨->⟩"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]),
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]),
                        S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])))))
    )

    # !(test
    #   (bc &kbh (fromNumber 2)
    #       (: $prf
    #          (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)
    #                (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    #   (: (a1 (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩ ⟨t⟩)
    #      (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)
    #            (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(2),
                S[":"](V.prf,
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                            S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]))))),
            S[":"](S.a1(S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])))))
    )

    # !(test
    #   (bc &kbh (fromNumber 1)
    #       (: $prf
    #          (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)))
    #   (: (a2 ⟨t⟩)
    #      (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(1),
                S[":"](V.prf, S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]))),
            S[":"](S.a2(S["⟨t⟩"]),
                S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"])))
    )

    # !(test
    #   (bc &kbh (fromNumber 2) (: (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) ⟨wff⟩))
    #   (: (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) ⟨wff⟩))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(2),
                S[":"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]), S["⟨wff⟩"])),
            S[":"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]), S["⟨wff⟩"]))
    )

    # !(test
    #   (bc &kbh (fromNumber 1) (: (⟨=⟩ ⟨t⟩ ⟨t⟩) ⟨wff⟩))
    #   (: (⟨=⟩ ⟨t⟩ ⟨t⟩) ⟨wff⟩))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(1),
                S[":"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]), S["⟨wff⟩"])),
            S[":"](S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]), S["⟨wff⟩"]))
    )

    # !(test
    #   (bc &kbh (fromNumber 4)
    #       (: $prf
    #          (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩))))
    #   (: (mp (a1 (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩ ⟨t⟩)
    #          (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)
    #          (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩))
    #          (a2 ⟨t⟩))
    #      (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩))))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(4),
                S[":"](V.prf,
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])))),
            S[":"](S.mp(S.a1(S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                    S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])),
                    S.a2(S["⟨t⟩"])),
                S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]))))
    )

    # !(test
    #   (bc &kbh (fromNumber 5)
    #       (: $prf
    #          (⟨=⟩ ⟨t⟩ ⟨t⟩)))
    #   (: (mp (mp (a1 (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩ ⟨t⟩)
    #              (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)
    #              (⟨->⟩ (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩))
    #              (a2 ⟨t⟩))
    #          (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)
    #          (⟨=⟩ ⟨t⟩ ⟨t⟩)
    #          (a2 ⟨t⟩))
    #      (⟨=⟩ ⟨t⟩ ⟨t⟩)))
    yield m.eval(
        S.test(S.bc(S["&kbh"],
                S.fromNumber(5),
                S[":"](V.prf, S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]))),
            S[":"](S.mp(S.mp(S.a1(S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                        S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        S["⟨->⟩"](S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                            S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])),
                        S.a2(S["⟨t⟩"])),
                    S["⟨=⟩"](S["⟨+⟩"](S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"]),
                    S.a2(S["⟨t⟩"])),
                S["⟨=⟩"](S["⟨t⟩"], S["⟨t⟩"])))
    )
