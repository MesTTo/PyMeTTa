"""The Python twin of examples/syntax/parse.metta: reading text back into atoms.

The first five forms hand `parse` a piece of MeTTa SOURCE, which is exactly
what a twin may not carry, so they are declined and the residue table records
each one against P14.1. The last three do not: they start from ordinary string
DATA and let the program itself apply `repr` before `parse`, so the round trip
is `parse(repr(s)) == s` over a string with backslashes, one with embedded
quotes, and one whose backslash-n is two characters rather than a newline.

Those three are ordinary Python strings through `val`, the door for a value
that crosses whole, and the terms around them are built by calling the head:
`S.parse(S.repr(...))` is the term `(parse (repr ...))`, not a call to the
reader, which is the distinction the lane draws by looking at what the callee
IS rather than at its name.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 2238 across the rewrite into the authority's idiom:
#: `expr(S["test"], expr(S["parse"], ...), ...)` became
#: `S.test(S.parse(...), ...)`. Calling a symbol and building with expr make
#: the same atom in Python, so the engine's three runnable forms are unchanged
#: and the count is too. Prior: ADDED 2026-08-22 at 2238 by 7f15dc1's wave-3
#: baseline.
BUDGET = 2238


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (parse "A") A)
    yield None

    # !(test (parse "(R A B)") (R A B))
    yield None

    # !(test (parse "(R A (S B C))") (R A (S B C)))
    yield None

    # !(test (parse "(* 2 21)") (noeval (* 2 21)))
    yield None

    # !(test (parse "\"42\"") "42")
    yield None

    # !(test (parse (repr "C:\\Users\\bob")) "C:\\Users\\bob")
    yield m.eval(S.test(S.parse(S.repr(val("C:\\Users\\bob"))), val("C:\\Users\\bob")))

    # !(test (parse (repr "say \"hi\"")) "say \"hi\"")
    yield m.eval(S.test(S.parse(S.repr(val('say "hi"'))), val('say "hi"')))

    # !(test (parse (repr "a\\nb")) "a\\nb")
    yield m.eval(S.test(S.parse(S.repr(val("a\\nb"))), val("a\\nb")))
