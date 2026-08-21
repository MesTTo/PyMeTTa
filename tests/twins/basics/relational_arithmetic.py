"""The Python twin of examples/basics/relational_arithmetic.metta: CLP(FD).

The `#` operators are constraints rather than evaluations, so they run in
every direction. Python has no `#+`, and it should not: the operators are
MeTTa names, so they are spelled at the naming door, `S["#+"]`. `S[name]` is
a NAME, which is why nothing here is a string in the sense the lane refuses.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 11342


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Forwards, the same as ordinary arithmetic.
    # !(test (#+ 1 2) 3)
    yield m.eval(S.test(S["#+"](1, 2), 3))
    # !(test (#* 3 4) 12)
    yield m.eval(S.test(S["#*"](3, 4), 12))
    # !(test (#- 10 4) 6)
    yield m.eval(S.test(S["#-"](10, 4), 6))

    # Backwards: `let` binds the RESULT and solves for the unknown.
    # !(test (let 5 (#+ $x 2) $x) 3)
    yield m.eval(S.test(S["let"](5, S["#+"](V.x, 2), V.x), 3))
    # !(test (let 12 (#* $y 4) $y) 3)
    yield m.eval(S.test(S["let"](12, S["#*"](V.y, 4), V.y), 3))
    # !(test (let 6 (#- $z 4) $z) 10)
    yield m.eval(S.test(S["let"](6, S["#-"](V.z, 4), V.z), 10))

    # Integer division, remainder, and the two extremes.
    # !(test (#div 13 4) 3)
    yield m.eval(S.test(S["#div"](13, 4), 3))
    # !(test (#mod 13 4) 1)
    yield m.eval(S.test(S["#mod"](13, 4), 1))
    # !(test (#min 3 7) 3)
    yield m.eval(S.test(S["#min"](3, 7), 3))
    # !(test (#max 3 7) 7)
    yield m.eval(S.test(S["#max"](3, 7), 7))

    # All six comparisons, answering True or False rather than succeeding.
    # !(test (#< 1 2) True)
    yield m.eval(S.test(S["#<"](1, 2), TRUE))
    # !(test (#< 2 1) False)
    yield m.eval(S.test(S["#<"](2, 1), FALSE))
    # !(test (#> 2 1) True)
    yield m.eval(S.test(S["#>"](2, 1), TRUE))
    # !(test (#= 3 3) True)
    yield m.eval(S.test(S["#="](3, 3), TRUE))
    # !(test (#\= 3 4) True)
    yield m.eval(S.test(S[r"#\="](3, 4), TRUE))
    # !(test (#=< 1 2) True)
    yield m.eval(S.test(S["#=<"](1, 2), TRUE))
    # !(test (#=< 2 1) False)
    yield m.eval(S.test(S["#=<"](2, 1), FALSE))
    # !(test (#>= 2 1) True)
    yield m.eval(S.test(S["#>="](2, 1), TRUE))
    # !(test (#>= 1 2) False)
    yield m.eval(S.test(S["#>="](1, 2), FALSE))

    # Composed, and still solvable backwards through two constraints.
    # !(test (let 20 (#* (#+ $a 1) 4) $a) 4)
    yield m.eval(S.test(S["let"](20, S["#*"](S["#+"](V.a, 1), 4), V.a), 4))
