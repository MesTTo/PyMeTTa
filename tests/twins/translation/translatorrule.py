"""Purpose: examples/translation/translatorrule.metta in Python: when the cons happens.

Three definitions of one computation, differing only in WHEN. `runtime42` has
no translator rule, so its call runs at run time. `compileeval42` has one, so
the compiler expands the call and then evaluates the expansion. `compile42`
wraps its body in `noeval`, so the expansion is handed back as data.

All three are computations, so all three are Python functions: `cons` and
`noeval` are engine functions under exactly those names, and a compiled body
resolves a free name against the engine's registry, so a body reaches both.
Binding them with `m.fn` first is what keeps the Python valid to read and
runnable as a twin; the equations the decorator emits are the same either way.

Registering a rule has no Python declaration door yet, so it is the engine's
own function under its MeTTa name (residue, P14.10).
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Write one computation three ways, and see which of them runs when."""
    cons, noeval = m.fn.cons, m.fn.noeval

    @m.define
    def runtime42(arg):
        return cons(42, arg)

    @m.define
    def compileeval42(arg):
        return cons(42, arg)

    @m.define
    def compile42(arg):
        return noeval(cons(42, arg))

    # Known issue: a call through the function namespace answers a LAZY view,
    # so the perfect statement-level spelling of a directive,
    # `m.fn.add_translator_rule(S.compileeval42)`, REGISTERS NOTHING until
    # something pulls its answers [measured 2026-08-23: the rule fires only
    # after list() of the view]. The term door evaluates eagerly, so a
    # directive is written that way until a side-effecting call runs at
    # statement level.
    m.eval(S["add-translator-rule!"](S.compileeval42))
    m.eval(S["add-translator-rule!"](S.compile42))

    assert runtime42((43,)).one() == Expression((42, 43))
    assert compileeval42((43,)).one() == Expression((42, 43))
    assert compile42((43,)).one() == Expression((42, 43))
