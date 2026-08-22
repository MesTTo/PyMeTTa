"""The Python twin of examples/translation/translatorrule.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4064


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (runtime42 $arg)
    #    (cons 42 $arg))
    m += expr(S["="], expr(S["runtime42"], V["arg"]), expr(S["cons"], 42, V["arg"]))

    # (= (compileeval42 $arg)
    #    (cons 42 $arg))
    m += expr(S["="], expr(S["compileeval42"], V["arg"]), expr(S["cons"], 42, V["arg"]))

    # (= (compile42 $arg)
    #    (noeval (cons 42 $arg)))
    m += expr(
        S["="], expr(S["compile42"], V["arg"]), expr(S["noeval"], expr(S["cons"], 42, V["arg"]))
    )

    # !(add-translator-rule! compileeval42)
    yield m.eval(expr(S["add-translator-rule!"], S["compileeval42"]))

    # !(add-translator-rule! compile42)
    yield m.eval(expr(S["add-translator-rule!"], S["compile42"]))

    # !(test (runtime42 (43)) (42 43))
    yield m.eval(expr(S["test"], expr(S["runtime42"], expr(43)), expr(42, 43)))

    # !(test (compileeval42 (43)) (42 43))
    yield m.eval(expr(S["test"], expr(S["compileeval42"], expr(43)), expr(42, 43)))

    # !(test (compile42 (43)) (42 43))
    yield m.eval(expr(S["test"], expr(S["compile42"], expr(43)), expr(42, 43)))

    yield from ()
