"""examples/ch07-control-flow/07-04-bounded-and-committed-searches/05-foldall.metta in Python: ten spellings of one fold.

`foldall` takes an aggregator, a GENERATOR TERM and a seed, and folds every
answer the generator gives. The term is what makes the file: `(f)` answers 2
and then 3, and foldall sees both, so the argument may not be evaluated on the
way in. That is what the mention door is for. Calling a Symbol BUILDS, so
`S.f()` is the term `(f)` and nothing has run; calling the Python name `f()`
would run it and hand foldall a value.

The ten claims are the same fold with the aggregator and the generator each
written four ways: a defined function, a lambda, a lambda bound by a name, and
a lambda applied to a variable. A `let` that only names a value IS Python's
assignment, so those bindings are locals here and only the last two keep a
construct of their own.

`f` and `g` are the two shapes of stacked clause, and Python spells each one.
`f` is nullary, so its two clauses are two ALTERNATIVES and Python's word for
several results is `yield`: each independent yield stores one equation. `g`'s
clauses fix a literal in an argument position, which is what a parameter
default is, so `g` is two ordinary defs.
"""

from metta import TRUE, Expression, S, V, if_


def twin(m):
    """Fold two answers into five, ten ways round."""

    @m.define
    def f():                        # (= (f) 2)
        yield 2                     # (= (f) 3)
        yield 3                     #   one equation per alternative

    @m.define
    def g(_=1):                     # (= (g 1) 2): the default IS the head's
        return 2                    #   literal, so the parameter never appears

    @m.define
    def g(_=2):  # noqa: F811  -- two literal heads are two equations, so the second def stacks rather than replacing
        return 3                    # (= (g 2) 3)

    @m.define
    def merge(a, b):                # (= (merge $A $B) (+ $A $B))
        return a + b

    def fold(aggregate, generator, start=0):
        """Aggregate every answer of `generator`, starting from `start`."""
        return m.fn.foldall(aggregate, generator, start).one()

    add = S["|->"]((V.x, V.y), V.x + V.y)     # (|-> ($x $y) (+ $x $y))
    answering_f = S["|->"]((V.z,), S.f())     # (|-> ($z) (f))
    answering_g = S["|->"]((V.z,), S.g(V.z))  # (|-> ($z) (g $z))
    twice_g = S["|->"]((V.z,), 2 * S.g(V.z))  # (|-> ($z) (* 2 (g $z)))

    # A named aggregator, over an argument-free and then an argument-ful
    # generator.
    assert fold(S.merge, S.f()) == 5          # (foldall merge (f) 0)
    assert fold(S.merge, S.g(V.x)) == 5       # (foldall merge (g $x) 0)

    # The same folds with a lambda. `(let $agglambda <lambda> ...)` is this
    # local: a let that only names a value is Python's own assignment. The
    # original states the third of these twice, so this does too.
    assert fold(add, S.f()) == 5
    assert fold(add, S.g(V.z)) == 5
    assert fold(add, S.g(V.z)) == 5

    # A lambda generator, applied to a variable it ignores and then uses.
    assert fold(add, Expression((answering_f, V.x))) == 5
    assert fold(add, Expression((answering_g, V.x))) == 5
    assert fold(add, Expression((answering_g, V.w))) == 5

    # And the aggregator arriving out of a syntactic construct rather than out
    # of a name. `if_` has the arity the engine's `if` has, which is why it is
    # the builder for stored code.
    chosen = if_(TRUE, S.let(V.f, add, V.f), S.empty())  # rung: this `let` is inside a STORED term, where there is no Python statement position for an assignment
    assert fold(chosen, Expression((answering_g, V.w))) == 5
    assert fold(chosen, Expression((twice_g, V.w))) == 10


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 38332 to 37385, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 37385 to 37315, on the release tree:
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
#: RE-PINNED 2026-08-25, 37315 to 37085, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 37085 to 38090 (+1005), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 38090 to 37390 (-700), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 37390 to 36910 (-480), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 36910 to 28525 (-8385), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 28525
