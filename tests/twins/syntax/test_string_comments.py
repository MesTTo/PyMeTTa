"""The Python twin of examples/syntax/test_string_comments.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 3883


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test ")" ")")
    yield m.eval(expr(S["test"], val(")"), val(")")))

    # !(test "(" "(")
    yield m.eval(expr(S["test"], val("("), val("(")))

    # !(test ";" ";")
    yield m.eval(expr(S["test"], val(";"), val(";")))

    # !(test (quote ";") (quote ";"))
    yield m.eval(expr(S["test"], expr(S["quote"], val(";")), expr(S["quote"], val(";"))))

    # !(test "foo;bar" "foo;bar")
    yield m.eval(expr(S["test"], val("foo;bar"), val("foo;bar")))

    # !(test ";;;" ";;;")
    yield m.eval(expr(S["test"], val(";;;"), val(";;;")))

    # !(test ";start" ";start")
    yield m.eval(expr(S["test"], val(";start"), val(";start")))

    # !(test "end;" "end;")
    yield m.eval(expr(S["test"], val("end;"), val("end;")))

    # !(test "quote: \"" "quote: \"")
    yield m.eval(expr(S["test"], val('quote: "'), val('quote: "')))

    # !(test "path\\file" "path\\file")
    yield m.eval(expr(S["test"], val("path\\file"), val("path\\file")))

    # (= (test-func) result)
    m += expr(S["="], expr(S["test-func"]), S["result"])

    # !(test (test-func) result)
    yield m.eval(expr(S["test"], expr(S["test-func"]), S["result"]))

    yield from ()
