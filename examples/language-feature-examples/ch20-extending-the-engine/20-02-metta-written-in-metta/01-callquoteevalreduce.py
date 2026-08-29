"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/01-callquoteevalreduce.metta in Python: the same four, timed.

`call`, `quote`, `eval` and `reduce` around `(fib 5)`, asked three times: before
`fib` exists, from inside the definition that installs it, and after. What each
one answers depends on whether the compiler had seen `fib` when the wrapper was
compiled, which is the whole file.

Every definition compiles. `fib` does not exist when the `before-*` wrappers
are written, so their inner call is mentioned rather than called; the four
outer heads carry hyphens and no equations, so they are mentioned too.

`compilefib` is the interesting one and it compiles whole. Its body installs an
equation from inside itself, which is `add-atom` at the function namespace
taking the handle it was given, and the original's `let` around that write is a
Python assignment to a name the body then ignores. The equation being installed
is built in place, `if` and all, because a compiled body's expressions are the
stored term rather than control flow: `$n < 2` there BUILDS `(< $n 2)`, where
the same comparison on an atom in hand would order it instead.
"""

from metta import Expression, S, V, fn


def twin(m):
    """Install wrappers around a dynamically installed Fibonacci definition."""
    fib5 = S.fib(5)

    @m.define
    def before_call():                  # (= (before-call) (call-before (call (fib 5))))
        return S.call_before(S.call(S.fib(5)))

    @m.define
    def before_quote():                 # (= (before-quote) (quote-before (quote (fib 5))))
        return S.quote_before(S.quote(S.fib(5)))

    @m.define
    def before_eval():                  # (= (before-eval) (eval-before (eval (fib 5))))
        return S.eval_before(S.eval(S.fib(5)))

    @m.define
    def before_reduce():                # (= (before-reduce) (reduce-before (reduce (fib 5))))
        return S.reduce_before(S.reduce(S.fib(5)))

    # With no fib to reduce, quote keeps its payload and the other two hand
    # theirs back unevaluated. `before-call` is left out because it errors,
    # which is what the original's head says in as many words. The original
    # writes the two unevaluated payloads as `(noeval (fib 5))`, because `test`
    # evaluates its expected side too and `noeval` comes off there; an assert
    # compares against a literal, so the payload is written as it arrives.
    assert m.eval(S.before_call_errors_ofc(
        S.before_quote(), S.before_eval(), S.before_reduce()
    )) == [S.before_call_errors_ofc(
        # Each control form retains its OWN irreducible call — LeaTTa
        # 9ea9f9d answers this exact expression with these three wrappers,
        # `eval` and `reduce` keeping their written frames.
        S.quote_before(S.quote(fib5)),
        S.eval_before(S.eval(fib5)),
        S.reduce_before(S.reduce(fib5)),
    )]

    @m.define
    def compilefib():
        # (= (compilefib) (let $temp (add-atom &self (= (fib $N) (if (< $N 2) $N
        #      (+ (fib (- $N 1)) (fib (- $N 2)))))) ((within (fib 5)) ...)))
        _temp = fn.add_atom(m, S["="](
            S.fib(V.n), V.n if V.n < 2 else S.fib(V.n - 1) + S.fib(V.n - 2)
        ))
        return (S.within(S.fib(5)),
                S.call_within(S.call(S.fib(5))),
                S.quote_within(S.quote(S.fib(5))),
                S.eval_within(S.eval(S.fib(5))),
                S.reduce_within(S.reduce(S.fib(5))))

    # The five inside were compiled before the add-atom ran, so `within` still
    # holds an unevaluated call while the four wrappers reduce.
    assert compilefib().one() == Expression((
        S.within(fib5),
        S.call_within(5),
        S.quote_within(S.quote(fib5)),
        S.eval_within(5),
        S.reduce_within(5),
    ))

    @m.define
    def after_call():                   # (= (after-call) (call-after (call (fib 5))))
        return S.call_after(S.call(S.fib(5)))

    @m.define
    def after_quote():                  # (= (after-quote) (quote-after (quote (fib 5))))
        return S.quote_after(S.quote(S.fib(5)))

    @m.define
    def after_eval():                   # (= (after-eval) (eval-after (eval (fib 5))))
        return S.eval_after(S.eval(S.fib(5)))

    @m.define
    def after_reduce():                 # (= (after-reduce) (reduce-after (reduce (fib 5))))
        return S.reduce_after(S.reduce(S.fib(5)))

    # fib exists now, so the four wrappers written BEFORE it reduce too.
    assert m.eval(Expression((
        S.before_call(), S.before_quote(), S.before_eval(), S.before_reduce()
    ))) == [Expression((
        S.call_before(5),
        S.quote_before(S.quote(fib5)),
        S.eval_before(5),
        S.reduce_before(5),
    ))]

    assert m.eval(Expression((
        S.after_call(), S.after_quote(), S.after_eval(), S.after_reduce()
    ))) == [Expression((
        S.call_after(5),
        S.quote_after(S.quote(fib5)),
        S.eval_after(5),
        S.reduce_after(5),
    ))]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: RE-PINNED 2026-08-25, 1 to 102651, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 102651 to 102557, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 102557 to 102532, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
BUDGET = {
    # Widened to 102445..102625 by a second ten-round full-lane
    # observe pass; observations count both passes.
    "minimum": 102445,
    "maximum": 102625,
    "observations": 20,
    "protocol": "full-lane/219/workers=32",
}
