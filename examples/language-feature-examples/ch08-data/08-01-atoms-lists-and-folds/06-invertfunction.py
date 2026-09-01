"""Purpose: examples/ch08-data/08-01-atoms-lists-and-folds/06-invertfunction.metta in Python: functions run backwards.

Unifying a pattern with what a call PRODUCES makes the call run backwards and
its variables come out bound, so destructuring a list with `cons` and
destructuring it with an ordinary user function are the same act. The last
form does it through arithmetic, where `#+` is the constraint path, so
`(g $X $Y 35)` solves `$X + 35 = 42`.

Both definitions are ordinary Python functions. `f` is `(append ($X) $Y)`,
where the one-element Python tuple is the one-element expression; `g` names
`#+`, which no Python identifier spells, and `fn["#+"]` is the function
namespace's exact spelling for that head.

`m.solve(pattern, subject)` is the inversion door: the known list on `let`'s
pattern side, the call on its subject side, and the answer template derived
from the subject's own variables, so each solution is a row keyed by the
variable that solved it. The subject is a BUILT term rather than a Python
call, because solve must receive the call unevaluated; `S.f` and `S.g` name
the two definitions and `fn.cons` names the constructor.
"""

from metta import Expression, S, V, fn

#: The list every claim destructures, and the head and tail it splits into.
ITEMS = (1, 2, 3, 4, 5, 6)
SPLIT = (1, Expression((2, 3, 4, 5, 6)))


def twin(m):
    """Destructure a list three ways, one of them through arithmetic."""

    @m.define
    def f(x, y):
        # (= (f $X $Y) (append ($X) $Y))
        return fn.append((x,), y)

    @m.define
    def g(x, y, z):
        # (= (g $X $Y $Z) (append ((#+ $X $Z)) $Y))
        return fn.append((fn["#+"](x, z),), y)

    # List destructuring, through the cons constructor.
    assert tuple(m.solve(ITEMS, fn.cons(V.Head, V.Tail)).one()) == SPLIT
    # And through an ordinary user function, which is the point.
    assert tuple(m.solve(ITEMS, S.f(V.Head, V.Tail)).one()) == SPLIT
    # A more complex case: the constraint solves 42 = $X + 35.
    assert tuple(m.solve((42, 2, 3), S.g(V.X, V.Y, 35)).one()) == (7, Expression((2, 3)))


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 14553 to 14561, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 14561 to 14526, on the release tree:
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
#: RE-PINNED 2026-08-25, 14526 to 14531, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 14531 to 14650 (+119), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 14650 to 14670 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 14670 to 7094 (-7576), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 7094 to 7075 (-19), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 7075 to 7083 (+8), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 7083
