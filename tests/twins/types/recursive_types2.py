"""The Python twin of examples/types/recursive_types2.metta: Peano numbers.

`Z` is zero and `S` is successor, so `(S (S Z))` is two, and `Greater` decides
between two of them by peeling one constructor off each until one of them runs
out. The three equations are the whole definition and they are recursion over
STRUCTURE rather than over a value.

All three are written at the container door, because their heads match a
CONSTRUCTOR: `(Greater (S $x) Z)` fixes the shape of an argument, and a
compiled head takes plain parameters or literal patterns, not a structural
pattern. Python's own construct for that is the `match` statement, which the
compiled subset has no lowering for yet; the residue table records it against
P14.4.

`SUCC` names the successor because the successor's MeTTa name is `S`, and `S`
is already the name of the symbol factory this module builds every atom with.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 8923

#: The successor constructor, whose MeTTa name is the single letter S.
SUCC = S["S"]


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: Z Nat)
    m += S[":"](S.Z, S.Nat)
    # (: S (-> Nat Nat))
    m += S[":"](SUCC, S["->"](S.Nat, S.Nat))
    # (: Greater (-> Nat Nat Bool))
    m += S[":"](
        S.Greater, S["->"](S.Nat, S.Nat, S.Bool)
    )

    # (= (Greater (S $x) Z) True)
    m += S["="](S.Greater(SUCC(V.x), S.Z), TRUE)
    # (= (Greater Z $x) False)
    m += S["="](S.Greater(S.Z, V.x), FALSE)
    # (= (Greater (S $x) (S $y)) (Greater $x $y))
    m += S["="](
        S.Greater(SUCC(V.x), SUCC(V.y)), S.Greater(V.x, V.y)
    )

    # !(test (Greater (S Z) (S Z)) false)
    yield m.eval(
        S.test(S.Greater(SUCC(S.Z), SUCC(S.Z)), FALSE)
    )
    # !(test (Greater (S (S Z)) (S Z)) true)
    yield m.eval(
        S.test(
            S.Greater(SUCC(SUCC(S.Z)), SUCC(S.Z)), TRUE
        )
    )
