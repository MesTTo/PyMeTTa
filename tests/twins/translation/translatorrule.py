"""The Python twin of examples/translation/translatorrule.metta.

Three definitions of the same computation, differing in when the `cons`
happens. `runtime42` has no translator rule, so its call runs at run time;
`compileeval42` has one, so the compiler expands the call and then EVALUATES
the expansion; `compile42` wraps its body in `noeval`, so the expansion is
handed back as data.

All three are computations and are written as ones: `cons` and `noeval` are
functions the engine knows under exactly those names, so a compiled body
reaches both.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4064 to 6498, +2434 (+59.89%), by the wave-4 idiom
#: rewrite moving all three definitions onto @m.define.
#: COMPILING a definition costs more than STORING one, and the difference is
#: paid once per process plus a little per definition, never per call: four
#: trivial one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more.
#: The 4064 this twin was pinned at is the same three equations stored, so the
#: whole move is those three; the 178 above 1629 + 2*193 is these bodies being
#: larger than the trivial ones the rate was taken on.
#: A second, smaller cause is in this figure: binding an engine function with
#: `m.fn(...)` makes its name PYTHON-RESOLVABLE, so @m.define records no
#: hazard and builds a RUNNABLE Python twin where it would otherwise build one
#: that refuses. Measured by deleting only that binding line: 6257 against
#: 6498, and with it `compile42.py((43,))` answers where without it the twin raises
#: "its body uses the engine function ..., which exist only in the engine".
BUDGET = 6498


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    an `add-translator-rule!` form answers the rule it registered.
    """
    # The engine's own `cons` and `noeval`, bound so the Python below stays
    # valid. A compiled body resolves the NAME through the engine's registry
    # rather than through these objects, so the bindings change nothing the
    # equations emit.
    cons, noeval = m.fn("cons"), m.fn("noeval")

    @m.define
    def runtime42(arg):
        # (= (runtime42 $arg) (cons 42 $arg))
        return cons(42, arg)

    @m.define
    def compileeval42(arg):
        # (= (compileeval42 $arg) (cons 42 $arg))
        return cons(42, arg)

    @m.define
    def compile42(arg):
        # (= (compile42 $arg) (noeval (cons 42 $arg)))
        return noeval(cons(42, arg))

    # !(add-translator-rule! compileeval42)
    yield m.eval(S["add-translator-rule!"](S.compileeval42))
    # !(add-translator-rule! compile42)
    yield m.eval(S["add-translator-rule!"](S.compile42))

    # !(test (runtime42 (43)) (42 43))
    yield m.eval(S.test(S.runtime42((43,)), (42, 43)))
    # !(test (compileeval42 (43)) (42 43))
    yield m.eval(S.test(S.compileeval42((43,)), (42, 43)))
    # !(test (compile42 (43)) (42 43))
    yield m.eval(S.test(S.compile42((43,)), (42, 43)))
