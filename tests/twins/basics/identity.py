"""examples/basics/identity.metta in Python: square a number, check the answer.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: RE-PINNED 2026-08-23, 2208 to 2230, by the indexed equation lookup in
#: engine/filereader.pl. The move is LAYOUT, not work: with
#: translated_equation_of/3 present in that file but never called this twin
#: already costs 2230, and switching one, two or all three of its call sites
#: onto it costs nothing further, all three readings 2230. A single inert
#: fact inserted at the same point moves it the same +20. Inserting n inert
#: facts there measures 2210 at n=0, 2230 at 1 and 2, 2240 at 3 and 5, 2220
#: at 4, 2250 at 6 and 8, and 2210 again at 16, 32 and 400, so this twin's
#: own floor is a 2210..2250 band with no trend in clause count, five times
#: the 4-inference deterministic allowance a point budget carries [measured
#: 2026-08-23, min-of-3 per variant through tools/twin_coverage.run_twin,
#: every variant's three runs identical].
#: Prior: INTERIM PIN 2026-08-23, min-of-3 on the wave-merged tree (2208 against the example's 2626): this file gates the pytest lane, so it is priced ahead of the corpus-wide pass that follows the library fixes, the guide update, and the marked-site sweep, and it is re-priced there with everything else.
#: RE-PINNED 2026-08-23, 2230 to 2221, by the call-side precondition on
#: specialization_plan/5, which stops this twin's call sites reading the callee's
#: equations to find nothing. Inside the 2210..2250 band recorded above, and DOWN,
#: which the point budget refuses in both directions.
#: RE-PINNED 2026-08-23, 2221 to 2258, by keying each support edge on a hash of
#: its endpoints. Eight above the band's top, and the reason is that the keys are
#: inferences the counter SEES while what they buy, a scan of every edge sharing
#: a node functor, is a C-level clause walk it cannot see: this example's graph
#: is far too small to collect any of that, where loading 8,000 definitions fell
#: from 3.25 seconds to 0.73.
#: RE-PINNED 2026-08-24, 2258 to 2228, by dropping the second walk over an
#: already-translated data head, which is 30 inferences this example no longer
#: spends. Back inside the 2210..2250 band recorded above.
BUDGET = 2228


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
        return x * x

    assert f(1) == [1]
