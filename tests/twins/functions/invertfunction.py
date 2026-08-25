"""Purpose: examples/functions/invertfunction.metta in Python: functions run backwards.

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
BUDGET = 14531

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
