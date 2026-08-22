"""examples/translation/translatorrule.metta in Python: when the cons happens.

Three definitions of one computation, differing only in WHEN. `runtime42` has
no translator rule, so its call runs at run time. `compileeval42` has one, so
the compiler expands the call and then evaluates the expansion. `compile42`
wraps its body in `noeval`, so the expansion is handed back as data.

All three are computations, so all three are Python functions: `cons` and
`noeval` are engine functions under exactly those names, and a compiled body
resolves a free name against the engine's registry, so a body reaches both.
Binding them with `m.fn` first is what keeps the Python valid to read and
runnable as a twin; the equations the decorator emits are the same either way.

Registering a rule is `m.fn("add-translator-rule!")`, the engine function as an
ordinary callable, because the rewrite seam has no Python declaration door yet
(residue, P14.10).
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6498 to 5807, -691 (-10.6%), by the twin contract
#: change: three `(test ...)` terms became three Python `assert`s, so the
#: `test` wrapper left the engine three times while the three definitions, the
#: two rule registrations and the three calls over them stayed in it. Against
#: the example's 8287 the ratio is 0.7007.
#: Prior: 6498, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 5807


def twin(m):
    """Write one computation three ways, and see which of them runs when."""
    cons, noeval = m.fn("cons"), m.fn("noeval")

    @m.define
    def runtime42(arg):
        return cons(42, arg)

    @m.define
    def compileeval42(arg):
        return cons(42, arg)

    @m.define
    def compile42(arg):
        return noeval(cons(42, arg))

    add_rule = m.fn("add-translator-rule!")
    add_rule(S.compileeval42)
    add_rule(S.compile42)

    assert runtime42((43,)) == [expr(42, 43)]
    assert compileeval42((43,)) == [expr(42, 43)]
    assert compile42((43,)) == [expr(42, 43)]
