"""The Python twin of examples/syntax/test_string_comments.metta: `;` in a string.

The original is a reader test: a semicolon inside a string starts no comment,
a lone `(` or `)` is a string and not a paren, and a backslash escape survives.
A Python twin cannot re-run the reader, because it never hands the engine any
text to read; what it CAN prove is the other half, that the string VALUES the
reader is supposed to produce are the ones the engine compares equal, and that
is what these forms assert. Each string crosses through `val`, the door for a
Python value that travels whole.

`(= (test-func) result)` is written at the container door, ONE RUNG BELOW the
decorator, and the reason is the subset's data convention: a compiled body
reads a lowercase free name as a call it cannot resolve, and capitalisation is
what marks data, so `result` has no `@m.define` spelling. The residue table
records that against P14.4, which owns the subset's growth. The drop would be
declared as `RUNG = "<reason>"` if that declaration were usable; the lane's own
source scan reads the reason string as MeTTa text, which the residue records
too.
"""

from petta import S, equation, val

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 3883 across the rewrite into the authority's idiom:
#: `expr(S["test"], val(";"), val(";"))` became `S.test(val(";"), val(";"))`
#: and the equation became `equation(...).to(...)`. Both are Python-side
#: spellings of the same atoms, so the engine's twelve forms cost what they
#: cost before. Prior: ADDED 2026-08-22 at 3883 by 7f15dc1's wave-3 baseline.
BUDGET = 3883


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Test 0: comment separator and parentheses in strings.
    # !(test ")" ")")
    yield m.eval(S.test(val(")"), val(")")))
    # !(test "(" "(")
    yield m.eval(S.test(val("("), val("(")))
    # !(test ";" ";")
    yield m.eval(S.test(val(";"), val(";")))

    # Test 1: a semicolon constant, held by quote as a wrapper value.
    # !(test (quote ";") (quote ";"))
    yield m.eval(S.test(S.quote(val(";")), S.quote(val(";"))))

    # Test 2: a semicolon in the middle.
    # !(test "foo;bar" "foo;bar")
    yield m.eval(S.test(val("foo;bar"), val("foo;bar")))
    # Test 3: several of them.
    # !(test ";;;" ";;;")
    yield m.eval(S.test(val(";;;"), val(";;;")))
    # Test 4: one at the start.
    # !(test ";start" ";start")
    yield m.eval(S.test(val(";start"), val(";start")))
    # Test 5: one at the end.
    # !(test "end;" "end;")
    yield m.eval(S.test(val("end;"), val("end;")))

    # Test 6: an escaped quote inside the string.
    # !(test "quote: \"" "quote: \"")
    yield m.eval(S.test(val('quote: "'), val('quote: "')))
    # Test 7: a backslash escape.
    # !(test "path\\file" "path\\file")
    yield m.eval(S.test(val("path\\file"), val("path\\file")))

    # Test 8: an ordinary definition, with a comment after it.
    # (= (test-func) result)
    # rung: below the function shape: the body is the lowercase symbol `result`, which
    #   a compiled body reads as a call it cannot resolve (residue, P14.4)
    m += equation(S["test-func"]()).to(S.result)
    # !(test (test-func) result)
    yield m.eval(S.test(S["test-func"](), S.result))
