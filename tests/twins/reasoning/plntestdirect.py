"""The Python twin of examples/reasoning/plntestdirect.metta: PLN, chained.

The same rule set as plntest, driven by represented `sentence` facts instead of
an explicit `|-` step, so the answer is the two-step chain a-b-c.

`clamp` is the one definition whose whole body has a compiled spelling, so it is
an ordinary Python function and `min`/`max` are Python's own builtins, which the
subset lowers to the engine's. Everything else stays at the term door, and each
has a different reason:

- the two probability bounds DIVIDE, and `/` in a compiled body lowers to
  `(/ (* 1.0 $left) $right)` so an exact integer quotient stays a float the way
  Python's `/` does. The example writes MeTTa's own `/`, which the coercion is
  not, so the equation would no longer be the example's;
- `conditional-probability-consistency`, `Truth_Deduction` and the recursive
  `sentence` clause use MeTTa's `and`, which is a generate-and-test over two
  values where Python's `and` short-circuits on truthiness. `m.fn` is the escape
  a body normally takes for a name the operators do not reach, and it is closed
  here because it binds the ENGINE's name and `and` is a Python keyword;
- `Truth_Deduction` and all three `sentence` clauses destructure in the HEAD,
  and a compiled head pattern must be a literal;
- `STV` has literal SYMBOL heads, and a stacked clause's default must be a
  literal too, so `def g(_t=1)` writes `(= (g 1) ...)` but nothing writes
  `(= (g a) ...)`.

Each is a residue entry against P14.4. Where an operator does build the term it
is used, and where it cannot the tuple is: `0 < V.As` answers `(> $As 0)`
because Python reflects `<` into `>`, so `(< 0 $As)` is written the way MeTTa
writes it, as the tuple `(LT, 0, V.As)`. The third `sentence` clause unifies
rather than defines, and `equation($TV).to(...)` is the same builder either way:
`(= $TV ...)` as a GOAL is the atom `(= lhs rhs)` in an evaluated position.
"""

from petta import S, V, equation, val

#: The comparison head this file needs with a GROUND left operand, which
#: is the one shape Python's own operators cannot build: `<` reflects into `>`.
LT = S["<"]

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 32602 to 34231, +1629 (+5.00%), by `clamp` moving to the
#: definitional decorator. The compiled clause is the same clause; the charge is
#: @m.define's per-name admission, the three reflection facts the container door
#: never writes (`(defined &self clamp)`, `(effect clamp immutable)` and
#: `(source-span &self clamp ...)`), measured at ~1.6k inferences per decorated
#: name and paid once at decoration. Prior: ADDED 2026-08-22 at 32602 by the
#: wave-3 twin baseline.
BUDGET = 34231


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def clamp(v, low, high):
        # (= (clamp $v $min $max) (min $max (max $v $min)))
        return min(high, max(v, low))

    # (: smallest-intersection-probability (-> Number Number Number))
    m += S[":"](
        S["smallest-intersection-probability"],
        S["->"](S.Number, S.Number, S.Number),
    )

    # (= (smallest-intersection-probability $As $Bs)
    #    (clamp (/ (- (+ $As $Bs) 1) $As) 0 1))
    m += equation(S["smallest-intersection-probability"](V.As, V.Bs)).to(
        S.clamp((V.As + V.Bs - 1) / V.As, 0, 1)
    )

    # (: largest-intersection-probability (-> Number Number Number))
    m += S[":"](
        S["largest-intersection-probability"],
        S["->"](S.Number, S.Number, S.Number),
    )

    # (= (largest-intersection-probability $As $Bs)
    #    (clamp (/ $Bs $As) 0 1))
    m += equation(S["largest-intersection-probability"](V.As, V.Bs)).to(
        S.clamp(V.Bs / V.As, 0, 1)
    )

    # (: conditional-probability-consistency (-> Number Number Number Bool))
    m += S[":"](
        S["conditional-probability-consistency"],
        S["->"](S.Number, S.Number, S.Number, S.Bool),
    )

    # (= (conditional-probability-consistency $As $Bs $ABs)
    #    (and (< 0 $As)
    #         (and (<= (smallest-intersection-probability $As $Bs) $ABs)
    #              (<= $ABs (largest-intersection-probability $As $Bs)))))
    m += equation(
        S["conditional-probability-consistency"](V.As, V.Bs, V.ABs)
    ).to(
        (LT, 0, V.As)
        & (
            (S["smallest-intersection-probability"](V.As, V.Bs) <= V.ABs)
            & (V.ABs <= S["largest-intersection-probability"](V.As, V.Bs))
        )
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
    m += equation(
        S.Truth_Deduction(
            S.stv(V.Ps, V.Pc),
            S.stv(V.Qs, V.Qc),
            S.stv(V.Rs, V.Rc),
            S.stv(V.PQs, V.PQc),
            S.stv(V.QRs, V.QRc),
        )
    ).to(
        S["if"](
            S["conditional-probability-consistency"](V.Ps, V.Qs, V.PQs)
            & S["conditional-probability-consistency"](V.Qs, V.Rs, V.QRs),
            S.stv(
                S["if"](
                    (LT, 0.9999, V.Qs),
                    V.Rs,
                    V.PQs * V.QRs
                    + (1 - V.PQs) * (V.Rs - V.Qs * V.QRs) / (1 - V.Qs),
                ),
                S.min(V.Pc, S.min(V.Qc, S.min(V.Rc, S.min(V.PQc, V.QRc)))),
            ),
            S.stv(1, 0),
        )
    )

    # (= (STV a) (stv 0.4 0.9))
    m += equation(S.STV(S.a)).to(S.stv(0.4, 0.9))

    # (= (STV b) (stv 0.4 0.9))
    m += equation(S.STV(S.b)).to(S.stv(0.4, 0.9))

    # (= (STV c) (stv 0.4 0.9))
    m += equation(S.STV(S.c)).to(S.stv(0.4, 0.9))

    # (= (sentence (Inheritance a b) (stv 0.9 0.9)) (once True))
    m += equation(S.sentence(S.Inheritance(S.a, S.b), S.stv(0.9, 0.9))).to(
        S.once(TRUE)
    )

    # (= (sentence (Inheritance b c) (stv 0.9 0.9)) (once True))
    m += equation(S.sentence(S.Inheritance(S.b, S.c), S.stv(0.9, 0.9))).to(
        S.once(TRUE)
    )

    # (= (sentence (Inheritance $A $C) $TV)
    #    (once (and (and (sentence (Inheritance $A $B) $T1)
    #                    (sentence (Inheritance $B $C) $T2))
    #               (= $TV (Truth_Deduction (STV $A) (STV $B) (STV $C) $T1 $T2)))))
    m += equation(S.sentence(S.Inheritance(V.A, V.C), V.TV)).to(
        S.once(
            S.sentence(S.Inheritance(V.A, V.B), V.T1)
            & S.sentence(S.Inheritance(V.B, V.C), V.T2)
            & equation(V.TV).to(
                S.Truth_Deduction(
                    S.STV(V.A), S.STV(V.B), S.STV(V.C), V.T1, V.T2
                )
            )
        )
    )

    # !(test (let $derivation (sentence (Inheritance a c) $TV) $TV)
    #        (stv 0.8166666666666668 0.9))
    yield m.eval(
        S.test(
            S.let(V.derivation, S.sentence(S.Inheritance(S.a, S.c), V.TV), V.TV),
            S.stv(0.8166666666666668, 0.9),
        )
    )
