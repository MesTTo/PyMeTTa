"""Purpose: examples/control/metta4_streams.metta in Python: answers as a stream.

`range` answers one number at a time, and the three things the file does with
those answers are three ordinary Python lines: iterating them all, taking the
first, and folding them into a total.

`range` itself is the superposition it is: `superpose(k, counter(k + 1, n))`
is the fork in expression position and `empty()` is the branch with nothing to
say, so the equation stored is the original's own. Written as a generator with
two yields it would store one superposition wrapped in another, which answers
the same and is not the same knowledge. It is `counter` on the Python side
because `range` is a BUILTIN a compiled body lowers to `py-range` before it
looks for the definition's own name, so `def range` would compile its own
recursion to the builtin and answer `[1, (2 3 4)]`; `name="range"` puts the
MeTTa name on the equation and the recursion resolves to it.

metta4's `forall` runs its body once per answer and stops early if one answers
false, which is what a `for` loop over an iterator already does; `once` is
`first(default=...)`, which pulls at most one answer out of the lazy view and
leaves the producer where it stands; and `foldall` with `+` and a zero start is
`sum`, because a fold over answers is collection work and the dissolution
table puts collection work in Python.

That last fold adds Python numbers, not atoms, so it reads the answers'
carried scalars: `+` over a grounded atom STAGES `(+ ...)` rather than
computing it, which is what makes `G(1) + 2` a term everywhere else in this
corpus [source: bindings/python/metta/_atoms_core.py, Grounded.value;
re-measured 2026-08-24: `sum(m.fn.gen())` builds `(+ (+ (+ 0 1) 2) 3)`;
commit=028b41a056cfd706e516cd0b945cbf69ac066da7].

`gen` has three clauses for one head. Stacked `@m.define` will not say that:
stacking reads as first-match, so two clauses fixing no literal are a
REDEFINITION. `@rules` is the other shape of the definitional door and says it
directly, and `space += bundle` lands the clause set through the one write
door.
Guarantees:
  - UNIT used here is a package value rather than a local reconstruction
    [tested: test_the_canonical_atoms_are_public_values; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import UNIT, S, equation, rules, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11757 to 11814, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11814 to 11827, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11827 to 11763, on the release tree:
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
#: RE-PINNED 2026-08-25, 11763 to 11773, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 11773


def twin(m):
    """Fan a range into two spaces, then fold three answers into one."""
    @m.define(name="range")
    def counter(k, n):
        # (= (range $K $N) (if (< $K $N) (superpose ($K (range (+ $K 1) $N))) (empty)))
        return superpose(k, counter(k + 1, n)) if k < n else empty()  # noqa: F821  -- `empty` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    s1 = metta.space("&s1")
    s2 = metta.space("&s2")

    # !(forall (range 1 5) (|-> ($x) (add-atom &s1 (num $x))))
    for x in counter(1, 5):
        s1 += S.num(x)

    # !(let $x (once (range 1 5)) (add-atom &s2 (num $x)))
    s2 += S.num(counter(1, 5).first(default=UNIT))

    # !(test (collapse (get-atoms &s1)) ((num 1) (num 2) (num 3) (num 4)))
    assert list(s1) == [S.num(1), S.num(2), S.num(3), S.num(4)]

    # !(test (collapse (get-atoms &s2)) ((num 1)))
    assert list(s2) == [S.num(1)]

    @rules
    def gen():
        # (= (gen) 1) (= (gen) 2) (= (gen) 3)
        yield equation(S.gen()).to(1)
        yield equation(S.gen()).to(2)
        yield equation(S.gen()).to(3)

    m += gen

    # !(test (foldall (|-> ($x $y) (+ $x $y)) (gen) 0) 6)
    assert sum(answer.value for answer in m.fn.gen()) == 6
