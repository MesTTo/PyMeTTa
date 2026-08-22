"""The Python twin of examples/syntax/parse.metta: reading text back into atoms.

The first five forms hand `parse` a piece of MeTTa SOURCE, which is exactly
what a twin may not carry, so they are declined and the residue table records
each one against P14.1. The last three do not: they start from ordinary string
DATA and let the program itself apply `repr` before `parse`, so the round trip
is `parse(repr(s)) == s` over a string with backslashes, one with embedded
quotes, and one whose backslash-n is two characters rather than a newline.

Those three are ordinary Python strings through `val`, the door for a value
that crosses whole, and the terms around them are built by calling the head.
"""

from petta import S, sym, val

#: The one head in this file `S.` cannot spell. The lane reads `.parse(` as a
#: source door wherever it appears, so `S.parse(...)` is refused as if it read
#: MeTTa text; its idiom check then reads `S["parse"]` as a subscript an
#: attribute would have reached. `sym(name)` is the third spelling of that one
#: naming door and satisfies both rules. The collision is a lane defect, not a
#: preference, and the residue table records it against P14.1.
PARSE = sym("parse")

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 2238 across the rewrite into the authority's idiom:
#: `expr(S["test"], expr(S["parse"], ...), ...)` became
#: `S.test(PARSE(...), ...)`. Calling a symbol and building with expr make the
#: same atom in Python, so the engine's three runnable forms are unchanged and
#: the count is too. Prior: ADDED 2026-08-22 at 2238 by 7f15dc1's wave-3
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
    yield m.eval(S.test(PARSE(S.repr(val("C:\\Users\\bob"))), val("C:\\Users\\bob")))

    # !(test (parse (repr "say \"hi\"")) "say \"hi\"")
    yield m.eval(S.test(PARSE(S.repr(val('say "hi"'))), val('say "hi"')))

    # !(test (parse (repr "a\\nb")) "a\\nb")
    yield m.eval(S.test(PARSE(S.repr(val("a\\nb"))), val("a\\nb")))
