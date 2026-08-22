"""The Python twin of examples/reasoning/nilbc.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 260932529


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (: Nat Type)
    m += expr(S[":"], S["Nat"], S["Type"])

    # (: Z Nat)
    m += expr(S[":"], S["Z"], S["Nat"])

    # (: S (-> Nat Nat))
    m += expr(S[":"], S["S"], expr(S["->"], S["Nat"], S["Nat"]))

    # (: fromNumber (-> Number Nat))
    m += expr(S[":"], S["fromNumber"], expr(S["->"], S["Number"], S["Nat"]))

    # (= (fromNumber $n) (if (<= $n 0) Z (S (fromNumber (- $n 1)))))
    m += expr(
        S["="],
        expr(S["fromNumber"], V["n"]),
        expr(
            S["if"],
            expr(S["<="], V["n"], 0),
            S["Z"],
            expr(S["S"], expr(S["fromNumber"], expr(S["-"], V["n"], 1))),
        ),
    )

    # (: fromNat (-> Nat Number))
    m += expr(S[":"], S["fromNat"], expr(S["->"], S["Nat"], S["Number"]))

    # (= (fromNat Z) 0)
    m += expr(S["="], expr(S["fromNat"], S["Z"]), 0)

    # (= (fromNat (S $k)) (+ 1 (fromNat $k)))
    m += expr(
        S["="],
        expr(S["fromNat"], expr(S["S"], V["k"])),
        expr(S["+"], 1, expr(S["fromNat"], V["k"])),
    )

    # (: bc (-> $a                            ; Knowledge base space
    #           Nat                           ; Maximum depth
    #           $b                            ; Query
    #           $b))
    m += expr(S[":"], S["bc"], expr(S["->"], V["a"], S["Nat"], V["b"], V["b"]))

    # (= (bc $knowledge_base $_ $query)
    #    (let (: $proof $theorem) $query
    #         (match $knowledge_base (: $proof $theorem) (: $proof $theorem))))
    m += expr(
        S["="],
        expr(S["bc"], V["knowledge_base"], V["_1232"], V["query"]),
        expr(
            S["let"],
            expr(S[":"], V["proof"], V["theorem"]),
            V["query"],
            expr(
                S["match"],
                V["knowledge_base"],
                expr(S[":"], V["proof"], V["theorem"]),
                expr(S[":"], V["proof"], V["theorem"]),
            ),
        ),
    )

    # (= (bc $knowledge_base (S $depth) (: ($proof_rule $premise_proof) $theorem))
    #    (let* (;; Recurse on abstraction
    #           ((: $proof_rule (-> (: $premise_proof $premise_type) $theorem))
    #            (bc $knowledge_base $depth (: $proof_rule (-> (: $premise_proof $premise_type) $theorem))))
    #           ;; Recurse on premise
    #           ((: $premise_proof $premise_type)
    #            (bc $knowledge_base $depth (: $premise_proof $premise_type))))
    #      ;; Output fulfilled query
    #      (: ($proof_rule $premise_proof) $theorem)))
    m += expr(
        S["="],
        expr(
            S["bc"],
            V["knowledge_base"],
            expr(S["S"], V["depth"]),
            expr(S[":"], expr(V["proof_rule"], V["premise_proof"]), V["theorem"]),
        ),
        expr(
            S["let*"],
            expr(
                expr(
                    expr(
                        S[":"],
                        V["proof_rule"],
                        expr(
                            S["->"],
                            expr(S[":"], V["premise_proof"], V["premise_type"]),
                            V["theorem"],
                        ),
                    ),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(
                            S[":"],
                            V["proof_rule"],
                            expr(
                                S["->"],
                                expr(S[":"], V["premise_proof"], V["premise_type"]),
                                V["theorem"],
                            ),
                        ),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof"], V["premise_type"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof"], V["premise_type"]),
                    ),
                ),
            ),
            expr(S[":"], expr(V["proof_rule"], V["premise_proof"]), V["theorem"]),
        ),
    )

    # (= (bc $knowledge_base (S $depth) (: ($proof_rule $premise_proof1 $premise_proof2) $theorem))
    #    (let* (;; Recurse on abstraction
    #           ((: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                               (: $premise_proof2 $premise_type2)
    #                               $theorem))
    #            (bc $knowledge_base $depth (: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                                                           (: $premise_proof2 $premise_type2)
    #                                                           $theorem))))
    #           ;; Recurse on first premise
    #           ((: $premise_proof1 $premise_type1)
    #            (bc $knowledge_base $depth (: $premise_proof1 $premise_type1)))
    #           ;; Recurse on second premise
    #           ((: $premise_proof2 $premise_type2)
    #            (bc $knowledge_base $depth (: $premise_proof2 $premise_type2))))
    #      ;; Output fulfilled query
    #      (: ($proof_rule $premise_proof1 $premise_proof2) $theorem)))
    m += expr(
        S["="],
        expr(
            S["bc"],
            V["knowledge_base"],
            expr(S["S"], V["depth"]),
            expr(
                S[":"],
                expr(V["proof_rule"], V["premise_proof1"], V["premise_proof2"]),
                V["theorem"],
            ),
        ),
        expr(
            S["let*"],
            expr(
                expr(
                    expr(
                        S[":"],
                        V["proof_rule"],
                        expr(
                            S["->"],
                            expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                            expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                            V["theorem"],
                        ),
                    ),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(
                            S[":"],
                            V["proof_rule"],
                            expr(
                                S["->"],
                                expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                                expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                                V["theorem"],
                            ),
                        ),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(V["proof_rule"], V["premise_proof1"], V["premise_proof2"]),
                V["theorem"],
            ),
        ),
    )

    # (= (bc $knowledge_base (S $depth) (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3) $theorem))
    #    (let* (;; Recurse on abstraction
    #           ((: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                               (: $premise_proof2 $premise_type2)
    #                               (: $premise_proof3 $premise_type3)
    #                               $theorem))
    #            (bc $knowledge_base $depth (: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                                                           (: $premise_proof2 $premise_type2)
    #                                                           (: $premise_proof3 $premise_type3)
    #                                                           $theorem))))
    #           ;; Recurse on first premise
    #           ((: $premise_proof1 $premise_type1)
    #            (bc $knowledge_base $depth (: $premise_proof1 $premise_type1)))
    #           ;; Recurse on second premise
    #           ((: $premise_proof2 $premise_type2)
    #            (bc $knowledge_base $depth (: $premise_proof2 $premise_type2)))
    #           ;; Recurse on third premise
    #           ((: $premise_proof3 $premise_type3)
    #            (bc $knowledge_base $depth (: $premise_proof3 $premise_type3))))
    #      ;; Output fulfilled query
    #      (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3) $theorem)))
    m += expr(
        S["="],
        expr(
            S["bc"],
            V["knowledge_base"],
            expr(S["S"], V["depth"]),
            expr(
                S[":"],
                expr(
                    V["proof_rule"], V["premise_proof1"], V["premise_proof2"], V["premise_proof3"]
                ),
                V["theorem"],
            ),
        ),
        expr(
            S["let*"],
            expr(
                expr(
                    expr(
                        S[":"],
                        V["proof_rule"],
                        expr(
                            S["->"],
                            expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                            expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                            expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                            V["theorem"],
                        ),
                    ),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(
                            S[":"],
                            V["proof_rule"],
                            expr(
                                S["->"],
                                expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                                expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                                expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                                V["theorem"],
                            ),
                        ),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(
                    V["proof_rule"], V["premise_proof1"], V["premise_proof2"], V["premise_proof3"]
                ),
                V["theorem"],
            ),
        ),
    )

    # (= (bc $knowledge_base (S $depth) (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3 $premise_proof4) $theorem))
    #    (let* (;; Recurse on abstraction
    #           ((: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                               (: $premise_proof2 $premise_type2)
    #                               (: $premise_proof3 $premise_type3)
    #                               (: $premise_proof4 $premise_type4)
    #                               $theorem))
    #            (bc $knowledge_base $depth (: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                                                           (: $premise_proof2 $premise_type2)
    #                                                           (: $premise_proof3 $premise_type3)
    #                                                           (: $premise_proof4 $premise_type4)
    #                                                           $theorem))))
    #           ;; Recurse on first premise
    #           ((: $premise_proof1 $premise_type1)
    #            (bc $knowledge_base $depth (: $premise_proof1 $premise_type1)))
    #           ;; Recurse on second premise
    #           ((: $premise_proof2 $premise_type2)
    #            (bc $knowledge_base $depth (: $premise_proof2 $premise_type2)))
    #           ;; Recurse on third premise
    #           ((: $premise_proof3 $premise_type3)
    #            (bc $knowledge_base $depth (: $premise_proof3 $premise_type3)))
    #           ;; Recurse on fourth premise
    #           ((: $premise_proof4 $premise_type4)
    #            (bc $knowledge_base $depth (: $premise_proof4 $premise_type4))))
    #      ;; Output fulfilled query
    #      (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3 $premise_proof4) $theorem)))
    m += expr(
        S["="],
        expr(
            S["bc"],
            V["knowledge_base"],
            expr(S["S"], V["depth"]),
            expr(
                S[":"],
                expr(
                    V["proof_rule"],
                    V["premise_proof1"],
                    V["premise_proof2"],
                    V["premise_proof3"],
                    V["premise_proof4"],
                ),
                V["theorem"],
            ),
        ),
        expr(
            S["let*"],
            expr(
                expr(
                    expr(
                        S[":"],
                        V["proof_rule"],
                        expr(
                            S["->"],
                            expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                            expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                            expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                            expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                            V["theorem"],
                        ),
                    ),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(
                            S[":"],
                            V["proof_rule"],
                            expr(
                                S["->"],
                                expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                                expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                                expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                                expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                                V["theorem"],
                            ),
                        ),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(
                    V["proof_rule"],
                    V["premise_proof1"],
                    V["premise_proof2"],
                    V["premise_proof3"],
                    V["premise_proof4"],
                ),
                V["theorem"],
            ),
        ),
    )

    # (= (bc $knowledge_base (S $depth) (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3 $premise_proof4 $premise_proof5) $theorem))
    #    (let* (;; Recurse on abstraction
    #           ((: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                               (: $premise_proof2 $premise_type2)
    #                               (: $premise_proof3 $premise_type3)
    #                               (: $premise_proof4 $premise_type4)
    #                               (: $premise_proof5 $premise_type5)
    #                               $theorem))
    #            (bc $knowledge_base $depth (: $proof_rule (-> (: $premise_proof1 $premise_type1)
    #                                                           (: $premise_proof2 $premise_type2)
    #                                                           (: $premise_proof3 $premise_type3)
    #                                                           (: $premise_proof4 $premise_type4)
    #                                                           (: $premise_proof5 $premise_type5)
    #                                                           $theorem))))
    #           ;; Recurse on first premise
    #           ((: $premise_proof1 $premise_type1)
    #            (bc $knowledge_base $depth (: $premise_proof1 $premise_type1)))
    #           ;; Recurse on second premise
    #           ((: $premise_proof2 $premise_type2)
    #            (bc $knowledge_base $depth (: $premise_proof2 $premise_type2)))
    #           ;; Recurse on third premise
    #           ((: $premise_proof3 $premise_type3)
    #            (bc $knowledge_base $depth (: $premise_proof3 $premise_type3)))
    #           ;; Recurse on fourth premise
    #           ((: $premise_proof4 $premise_type4)
    #            (bc $knowledge_base $depth (: $premise_proof4 $premise_type4)))
    #           ;; Recurse on fifth premise
    #           ((: $premise_proof5 $premise_type5)
    #            (bc $knowledge_base $depth (: $premise_proof5 $premise_type5))))
    #      ;; Output fulfilled query
    #      (: ($proof_rule $premise_proof1 $premise_proof2 $premise_proof3 $premise_proof4 $premise_proof5) $theorem)))
    m += expr(
        S["="],
        expr(
            S["bc"],
            V["knowledge_base"],
            expr(S["S"], V["depth"]),
            expr(
                S[":"],
                expr(
                    V["proof_rule"],
                    V["premise_proof1"],
                    V["premise_proof2"],
                    V["premise_proof3"],
                    V["premise_proof4"],
                    V["premise_proof5"],
                ),
                V["theorem"],
            ),
        ),
        expr(
            S["let*"],
            expr(
                expr(
                    expr(
                        S[":"],
                        V["proof_rule"],
                        expr(
                            S["->"],
                            expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                            expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                            expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                            expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                            expr(S[":"], V["premise_proof5"], V["premise_type5"]),
                            V["theorem"],
                        ),
                    ),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(
                            S[":"],
                            V["proof_rule"],
                            expr(
                                S["->"],
                                expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                                expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                                expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                                expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                                expr(S[":"], V["premise_proof5"], V["premise_type5"]),
                                V["theorem"],
                            ),
                        ),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof1"], V["premise_type1"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof2"], V["premise_type2"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof3"], V["premise_type3"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof4"], V["premise_type4"]),
                    ),
                ),
                expr(
                    expr(S[":"], V["premise_proof5"], V["premise_type5"]),
                    expr(
                        S["bc"],
                        V["knowledge_base"],
                        V["depth"],
                        expr(S[":"], V["premise_proof5"], V["premise_type5"]),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(
                    V["proof_rule"],
                    V["premise_proof1"],
                    V["premise_proof2"],
                    V["premise_proof3"],
                    V["premise_proof4"],
                    V["premise_proof5"],
                ),
                V["theorem"],
            ),
        ),
    )

    # !(bind! &kbe (new-space))
    yield m.eval(expr(S["bind!"], S["&kbe"], expr(S["new-space"])))

    # !(add-atom &kbe (: a1 (-> (: $ter (⟨=⟩ $t $r))
    #                           (: $tes (⟨=⟩ $t $s))
    #                           (⟨=⟩ $r $s))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbe"],
            expr(
                S[":"],
                S["a1"],
                expr(
                    S["->"],
                    expr(S[":"], V["ter"], expr(S["⟨=⟩"], V["t"], V["r"])),
                    expr(S[":"], V["tes"], expr(S["⟨=⟩"], V["t"], V["s"])),
                    expr(S["⟨=⟩"], V["r"], V["s"]),
                ),
            ),
        )
    )

    # !(add-atom &kbe (: a2 (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbe"],
            expr(S[":"], S["a2"], expr(S["⟨=⟩"], expr(S["⟨+⟩"], V["t"], S["⟨0⟩"]), V["t"])),
        )
    )

    # !(test
    #   (bc &kbe (fromNumber 1) (: $prf (⟨=⟩ $t $t)))
    #   (: (a1 a2 a2) (⟨=⟩ $t $t)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbe"],
                expr(S["fromNumber"], 1),
                expr(S[":"], V["prf"], expr(S["⟨=⟩"], V["t"], V["t"])),
            ),
            expr(S[":"], expr(S["a1"], S["a2"], S["a2"]), expr(S["⟨=⟩"], V["t"], V["t"])),
        )
    )

    # !(bind! &kbm (new-space))
    yield m.eval(expr(S["bind!"], S["&kbm"], expr(S["new-space"])))

    # !(add-atom &kbm (: ⟨0⟩ ⟨term⟩))
    yield m.eval(expr(S["add-atom"], S["&kbm"], expr(S[":"], S["⟨0⟩"], S["⟨term⟩"])))

    # !(add-atom &kbm (: ⟨+⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨term⟩)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbm"],
            expr(
                S[":"],
                S["⟨+⟩"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    S["⟨term⟩"],
                ),
            ),
        )
    )

    # !(add-atom &kbm (: ⟨=⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨wff⟩)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbm"],
            expr(
                S[":"],
                S["⟨=⟩"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    S["⟨wff⟩"],
                ),
            ),
        )
    )

    # !(add-atom &kbm (: a1 (-> (: $t ⟨term⟩)
    #                           (: $r ⟨term⟩)
    #                           (: $s ⟨term⟩)
    #                           (: $ter (⟨=⟩ $t $r))
    #                           (: $tes (⟨=⟩ $t $s))
    #                           (⟨=⟩ $r $s))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbm"],
            expr(
                S[":"],
                S["a1"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    expr(S[":"], V["s"], S["⟨term⟩"]),
                    expr(S[":"], V["ter"], expr(S["⟨=⟩"], V["t"], V["r"])),
                    expr(S[":"], V["tes"], expr(S["⟨=⟩"], V["t"], V["s"])),
                    expr(S["⟨=⟩"], V["r"], V["s"]),
                ),
            ),
        )
    )

    # !(add-atom &kbm (: a2 (-> (: $t ⟨term⟩)
    #                           (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbm"],
            expr(
                S[":"],
                S["a2"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], V["t"], S["⟨0⟩"]), V["t"]),
                ),
            ),
        )
    )

    # !(add-atom &kbm (: ⟨t⟩ ⟨term⟩))
    yield m.eval(expr(S["add-atom"], S["&kbm"], expr(S[":"], S["⟨t⟩"], S["⟨term⟩"])))

    # !(test (is-member (: (a1 (⟨+⟩ ⟨t⟩ ⟨0⟩)
    #                          ⟨t⟩
    #                          ⟨t⟩
    #                          (a2 ⟨t⟩)
    #                          (a2 ⟨t⟩))
    #                      (⟨=⟩ ⟨t⟩ ⟨t⟩))
    #       (collapse (bc &kbm (fromNumber 3) (: $prf (⟨=⟩ ⟨t⟩ ⟨t⟩))))) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-member"],
                expr(
                    S[":"],
                    expr(
                        S["a1"],
                        expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]),
                        S["⟨t⟩"],
                        S["⟨t⟩"],
                        expr(S["a2"], S["⟨t⟩"]),
                        expr(S["a2"], S["⟨t⟩"]),
                    ),
                    expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                ),
                expr(
                    S["collapse"],
                    expr(
                        S["bc"],
                        S["&kbm"],
                        expr(S["fromNumber"], 3),
                        expr(S[":"], V["prf"], expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"])),
                    ),
                ),
            ),
            val(value=True),
        )
    )

    # !(bind! &kbh (new-space))
    yield m.eval(expr(S["bind!"], S["&kbh"], expr(S["new-space"])))

    # !(add-atom &kbh (: ⟨0⟩ ⟨term⟩))
    yield m.eval(expr(S["add-atom"], S["&kbh"], expr(S[":"], S["⟨0⟩"], S["⟨term⟩"])))

    # !(add-atom &kbh (: ⟨+⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨term⟩)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["⟨+⟩"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    S["⟨term⟩"],
                ),
            ),
        )
    )

    # !(add-atom &kbh (: ⟨=⟩ (-> (: $t ⟨term⟩)
    #                            (: $r ⟨term⟩)
    #                            ⟨wff⟩)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["⟨=⟩"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    S["⟨wff⟩"],
                ),
            ),
        )
    )

    # !(add-atom &kbh (: ⟨->⟩ (-> (: $P ⟨wff⟩)
    #                             (: $Q ⟨wff⟩)
    #                             ⟨wff⟩)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["⟨->⟩"],
                expr(
                    S["->"],
                    expr(S[":"], V["P"], S["⟨wff⟩"]),
                    expr(S[":"], V["Q"], S["⟨wff⟩"]),
                    S["⟨wff⟩"],
                ),
            ),
        )
    )

    # !(add-atom &kbh (: a1 (-> (: $t ⟨term⟩)
    #                           (: $r ⟨term⟩)
    #                           (: $s ⟨term⟩)
    #                           (⟨->⟩ (⟨=⟩ $t $r) (⟨->⟩ (⟨=⟩ $t $s) (⟨=⟩ $r $s))))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["a1"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S[":"], V["r"], S["⟨term⟩"]),
                    expr(S[":"], V["s"], S["⟨term⟩"]),
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], V["t"], V["r"]),
                        expr(
                            S["⟨->⟩"],
                            expr(S["⟨=⟩"], V["t"], V["s"]),
                            expr(S["⟨=⟩"], V["r"], V["s"]),
                        ),
                    ),
                ),
            ),
        )
    )

    # !(add-atom &kbh (: a2 (-> (: $t ⟨term⟩)
    #                           (⟨=⟩ (⟨+⟩ $t ⟨0⟩) $t))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["a2"],
                expr(
                    S["->"],
                    expr(S[":"], V["t"], S["⟨term⟩"]),
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], V["t"], S["⟨0⟩"]), V["t"]),
                ),
            ),
        )
    )

    # !(add-atom &kbh (: mp (-> (: $maj (⟨->⟩ $P $Q))
    #                           (: $P ⟨wff⟩)
    #                           (: $Q ⟨wff⟩)
    #                           (: $min $P)
    #                           $Q)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&kbh"],
            expr(
                S[":"],
                S["mp"],
                expr(
                    S["->"],
                    expr(S[":"], V["maj"], expr(S["⟨->⟩"], V["P"], V["Q"])),
                    expr(S[":"], V["P"], S["⟨wff⟩"]),
                    expr(S[":"], V["Q"], S["⟨wff⟩"]),
                    expr(S[":"], V["min"], V["P"]),
                    V["Q"],
                ),
            ),
        )
    )

    # !(add-atom &kbh (: ⟨t⟩ ⟨term⟩))
    yield m.eval(expr(S["add-atom"], S["&kbh"], expr(S[":"], S["⟨t⟩"], S["⟨term⟩"])))

    # !(test
    #   (bc &kbh (fromNumber 1)
    #       (: $prf
    #          (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    #   (: (a1 ⟨t⟩ ⟨t⟩ ⟨t⟩)
    #      (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨->⟩ (⟨=⟩ ⟨t⟩ ⟨t⟩) (⟨=⟩ ⟨t⟩ ⟨t⟩)))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 1),
                expr(
                    S[":"],
                    V["prf"],
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                        expr(
                            S["⟨->⟩"],
                            expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                            expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                        ),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(S["a1"], S["⟨t⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                expr(
                    S["⟨->⟩"],
                    expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    ),
                ),
            ),
        )
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
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 2),
                expr(
                    S[":"],
                    V["prf"],
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        expr(
                            S["⟨->⟩"],
                            expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                            expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                        ),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(S["a1"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                expr(
                    S["⟨->⟩"],
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    ),
                ),
            ),
        )
    )

    # !(test
    #   (bc &kbh (fromNumber 1)
    #       (: $prf
    #          (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)))
    #   (: (a2 ⟨t⟩)
    #      (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 1),
                expr(
                    S[":"], V["prf"], expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"])
                ),
            ),
            expr(
                S[":"],
                expr(S["a2"], S["⟨t⟩"]),
                expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
            ),
        )
    )

    # !(test
    #   (bc &kbh (fromNumber 2) (: (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) ⟨wff⟩))
    #   (: (⟨=⟩ (⟨+⟩ ⟨t⟩ ⟨0⟩) ⟨t⟩) ⟨wff⟩))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 2),
                expr(
                    S[":"], expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]), S["⟨wff⟩"]
                ),
            ),
            expr(S[":"], expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]), S["⟨wff⟩"]),
        )
    )

    # !(test
    #   (bc &kbh (fromNumber 1) (: (⟨=⟩ ⟨t⟩ ⟨t⟩) ⟨wff⟩))
    #   (: (⟨=⟩ ⟨t⟩ ⟨t⟩) ⟨wff⟩))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 1),
                expr(S[":"], expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]), S["⟨wff⟩"]),
            ),
            expr(S[":"], expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]), S["⟨wff⟩"]),
        )
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
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 4),
                expr(
                    S[":"],
                    V["prf"],
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    ),
                ),
            ),
            expr(
                S[":"],
                expr(
                    S["mp"],
                    expr(S["a1"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    expr(
                        S["⟨->⟩"],
                        expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    ),
                    expr(S["a2"], S["⟨t⟩"]),
                ),
                expr(
                    S["⟨->⟩"],
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                ),
            ),
        )
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
        expr(
            S["test"],
            expr(
                S["bc"],
                S["&kbh"],
                expr(S["fromNumber"], 5),
                expr(S[":"], V["prf"], expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"])),
            ),
            expr(
                S[":"],
                expr(
                    S["mp"],
                    expr(
                        S["mp"],
                        expr(S["a1"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"], S["⟨t⟩"]),
                        expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                        expr(
                            S["⟨->⟩"],
                            expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                            expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                        ),
                        expr(S["a2"], S["⟨t⟩"]),
                    ),
                    expr(S["⟨=⟩"], expr(S["⟨+⟩"], S["⟨t⟩"], S["⟨0⟩"]), S["⟨t⟩"]),
                    expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
                    expr(S["a2"], S["⟨t⟩"]),
                ),
                expr(S["⟨=⟩"], S["⟨t⟩"], S["⟨t⟩"]),
            ),
        )
    )

    yield from ()
