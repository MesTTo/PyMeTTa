"""The Python twin of examples/reasoning/plntest.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 31759


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (clamp $v $min $max)
    #    (min $max (max $v $min)))
    m += expr(
        S["="],
        expr(S["clamp"], V["v"], V["min"], V["max"]),
        expr(S["min"], V["max"], expr(S["max"], V["v"], V["min"])),
    )

    # (: smallest-intersection-probability (-> Number Number Number))
    m += expr(
        S[":"],
        S["smallest-intersection-probability"],
        expr(S["->"], S["Number"], S["Number"], S["Number"]),
    )

    # (= (smallest-intersection-probability $As $Bs)
    #    (clamp (/ (- (+ $As $Bs) 1) $As) 0 1))
    m += expr(
        S["="],
        expr(S["smallest-intersection-probability"], V["As"], V["Bs"]),
        expr(
            S["clamp"], expr(S["/"], expr(S["-"], expr(S["+"], V["As"], V["Bs"]), 1), V["As"]), 0, 1
        ),
    )

    # (: largest-intersection-probability (-> Number Number Number))
    m += expr(
        S[":"],
        S["largest-intersection-probability"],
        expr(S["->"], S["Number"], S["Number"], S["Number"]),
    )

    # (= (largest-intersection-probability $As $Bs)
    #    (clamp (/ $Bs $As) 0 1))
    m += expr(
        S["="],
        expr(S["largest-intersection-probability"], V["As"], V["Bs"]),
        expr(S["clamp"], expr(S["/"], V["Bs"], V["As"]), 0, 1),
    )

    # (: conditional-probability-consistency (-> Number Number Number Bool))
    m += expr(
        S[":"],
        S["conditional-probability-consistency"],
        expr(S["->"], S["Number"], S["Number"], S["Number"], S["Bool"]),
    )

    # (= (conditional-probability-consistency $As $Bs $ABs)
    #    (and (< 0 $As)
    #         (and (<= (smallest-intersection-probability $As $Bs) $ABs)
    #              (<= $ABs (largest-intersection-probability $As $Bs)))))
    m += expr(
        S["="],
        expr(S["conditional-probability-consistency"], V["As"], V["Bs"], V["ABs"]),
        expr(
            S["and"],
            expr(S["<"], 0, V["As"]),
            expr(
                S["and"],
                expr(
                    S["<="],
                    expr(S["smallest-intersection-probability"], V["As"], V["Bs"]),
                    V["ABs"],
                ),
                expr(
                    S["<="], V["ABs"], expr(S["largest-intersection-probability"], V["As"], V["Bs"])
                ),
            ),
        ),
    )

    # (= (Truth_Deduction (stv $Ps $Pc)
    #                     (stv $Qs $Qc)
    #                     (stv $Rs $Rc)
    #                     (stv $PQs $PQc)
    #                     (stv $QRs $QRc))
    #    (if (and (conditional-probability-consistency $Ps $Qs $PQs)
    #             (conditional-probability-consistency $Qs $Rs $QRs))
    #        ;; Preconditions are met
    #        (stv (if (< 0.9999 $Qs)                  ; avoid division by 0
    #                 ;; Qs tends to 1
    #                 $Rs
    #                 ;; Otherwise
    #                 (+ (* $PQs $QRs) (/ (* (- 1 $PQs) (- $Rs (* $Qs $QRs))) (- 1 $Qs))))
    #             (min $Pc (min $Qc (min $Rc (min $PQc $QRc)))))
    #        ;; Preconditions are not met
    #        (stv 1 0)))
    m += expr(
        S["="],
        expr(
            S["Truth_Deduction"],
            expr(S["stv"], V["Ps"], V["Pc"]),
            expr(S["stv"], V["Qs"], V["Qc"]),
            expr(S["stv"], V["Rs"], V["Rc"]),
            expr(S["stv"], V["PQs"], V["PQc"]),
            expr(S["stv"], V["QRs"], V["QRc"]),
        ),
        expr(
            S["if"],
            expr(
                S["and"],
                expr(S["conditional-probability-consistency"], V["Ps"], V["Qs"], V["PQs"]),
                expr(S["conditional-probability-consistency"], V["Qs"], V["Rs"], V["QRs"]),
            ),
            expr(
                S["stv"],
                expr(
                    S["if"],
                    expr(S["<"], 0.9999, V["Qs"]),
                    V["Rs"],
                    expr(
                        S["+"],
                        expr(S["*"], V["PQs"], V["QRs"]),
                        expr(
                            S["/"],
                            expr(
                                S["*"],
                                expr(S["-"], 1, V["PQs"]),
                                expr(S["-"], V["Rs"], expr(S["*"], V["Qs"], V["QRs"])),
                            ),
                            expr(S["-"], 1, V["Qs"]),
                        ),
                    ),
                ),
                expr(
                    S["min"],
                    V["Pc"],
                    expr(
                        S["min"],
                        V["Qc"],
                        expr(S["min"], V["Rc"], expr(S["min"], V["PQc"], V["QRc"])),
                    ),
                ),
            ),
            expr(S["stv"], 1, 0),
        ),
    )

    # (= (SyllogisticRuleGuard Inheritance) True)
    m += expr(S["="], expr(S["SyllogisticRuleGuard"], S["Inheritance"]), val(value=True))

    # (= (SyllogisticRuleGuard Implication) True)
    m += expr(S["="], expr(S["SyllogisticRuleGuard"], S["Implication"]), val(value=True))

    # (= (STV a) (stv 0.4 0.9))
    m += expr(S["="], expr(S["STV"], S["a"]), expr(S["stv"], 0.4, 0.9))

    # (= (STV b) (stv 0.4 0.9))
    m += expr(S["="], expr(S["STV"], S["b"]), expr(S["stv"], 0.4, 0.9))

    # (= (STV c) (stv 0.4 0.9))
    m += expr(S["="], expr(S["STV"], S["c"]), expr(S["stv"], 0.4, 0.9))

    # (= (|- (($LinkType $A $B) $T1)
    #        (($LinkType $B $C) $T2))
    #    (if (SyllogisticRuleGuard $LinkType)
    #        (($LinkType $A $C)
    #         (Truth_Deduction (STV $A)
    #                          (STV $B)
    #                          (STV $C) $T1 $T2)) (empty)))
    m += expr(
        S["="],
        expr(
            S["|-"],
            expr(expr(V["LinkType"], V["A"], V["B"]), V["T1"]),
            expr(expr(V["LinkType"], V["B"], V["C"]), V["T2"]),
        ),
        expr(
            S["if"],
            expr(S["SyllogisticRuleGuard"], V["LinkType"]),
            expr(
                expr(V["LinkType"], V["A"], V["C"]),
                expr(
                    S["Truth_Deduction"],
                    expr(S["STV"], V["A"]),
                    expr(S["STV"], V["B"]),
                    expr(S["STV"], V["C"]),
                    V["T1"],
                    V["T2"],
                ),
            ),
            expr(S["empty"]),
        ),
    )

    # !(test (|- ((Inheritance a b) (stv 0.9 0.9))
    #            ((Inheritance b c) (stv 0.8 0.9)))
    #        ((Inheritance a c) (stv 0.7333333333333334 0.9)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["|-"],
                expr(expr(S["Inheritance"], S["a"], S["b"]), expr(S["stv"], 0.9, 0.9)),
                expr(expr(S["Inheritance"], S["b"], S["c"]), expr(S["stv"], 0.8, 0.9)),
            ),
            expr(expr(S["Inheritance"], S["a"], S["c"]), expr(S["stv"], 0.7333333333333334, 0.9)),
        )
    )

    yield from ()
