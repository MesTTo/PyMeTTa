"""examples/translation/translatorrule.metta in Python: when the cons happens.

Three definitions of one computation, differing only in WHEN it runs.
`runtime42` has no translator rule, so its call runs at run time.
`compileeval42` has one, so the compiler expands the call and then evaluates
the expansion. `compile42` wraps its body in `noeval`, so the expansion is
handed back as data.

All three are ordinary compiled functions, and `cons` and `noeval` are reached
at the static function namespace, which is what that namespace is for: a
compiled body resolves those names against the engine's catalog, and writing
them as attributes keeps the file readable by a linter and by a reader.

Registering a rule has no Python declaration door yet, so it is the engine's
own function under its MeTTa name. That name ends in `!`, so the call performs
where it is written and needs no forcing read.
"""

from metta import Expression, S, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Write one computation three ways, and see which of them runs when."""

    @m.define
    def runtime42(arg):                   # (= (runtime42 $arg) (cons 42 $arg))
        return fn.cons(42, arg)

    @m.define
    def compileeval42(arg):               # (= (compileeval42 $arg) (cons 42 $arg))
        return fn.cons(42, arg)

    @m.define
    def compile42(arg):                   # (= (compile42 $arg) (noeval (cons 42 $arg)))
        return fn.noeval(fn.cons(42, arg))

    m.fn.add_translator_rule(S.compileeval42)   # (add-translator-rule! compileeval42)
    m.fn.add_translator_rule(S.compile42)       # (add-translator-rule! compile42)

    assert runtime42((43,)).one() == Expression((42, 43))       # [(42 43)]
    assert compileeval42((43,)).one() == Expression((42, 43))   # [(42 43)]
    assert compile42((43,)).one() == Expression((42, 43))       # [(42 43)]
