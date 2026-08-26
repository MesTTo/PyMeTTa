"""Purpose: examples/spaces/super.metta in Python: reaching the definition you shadow.

A space can redefine a function it inherits, and `super` is how the new
definition reaches the old one. Without it an override is replace-or-nothing,
and a guard that wants to check a call and then let it through has no way
through. It reaches the ENGINE's own definitions too, so a builtin can be
WRAPPED rather than only replaced.

The base definition compiles: `S.stored` is the mention door reading a
lowercase symbol as the data it is. The two overrides do not, and one blocker
is all that is left of the two this file used to carry: `super` is a translator
form rather than a registry function, so `is_function` answers False and a
compiled body naming it is refused (residue, P14.4)
[measured 2026-08-24: `fn.super` in a compiled body is refused with "names no
target function in this space's catalog"; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT: `super`
joins the registry, so an override is `@guarded.define def store(atom)` with
`fn.super` in its body.

Inside those stored terms the comparison is written by its WORD, `S.eq(a, b)`
being the atom `==`, because the four rich comparisons carry the engine's total
order of terms and a term outside a compiled body is built by naming its head.

Asking is ordinary: `space.eval(term)` is evalc, and `space.fn.<name>` is the
same function asked in that space, which is how the wrapped `car-atom` and the
untouched one are the same question put to two handles.
"""

import metta
from metta import S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 20394 to 20553, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 20553 to 20495, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 20495 to 20472, on the release tree:
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
#: RE-PINNED 2026-08-25, 20472 to 20465, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 20465 to 21920 (+1455), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 21920 to 21892 (-28), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
#: RE-PINNED 2026-08-26, 21892 to 21862 (-30), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=WORKTREE].
#: RE-PINNED 2026-08-26, 21862 to 20454 (-1408), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 20454
def twin(m):
    """Shadow one definition and one builtin, then delegate to each."""

    # (= (store $atom) (stored $atom)): the definition every space below
    # this one inherits.
    @m.define
    def store(atom):
        return S.stored(atom)

    # A space that gates it. `super` names the next definition up THIS space's
    # chain, so the guard delegates without naming what it delegates to.
    guarded = metta.space(S.guarded)
    guarded += equation(S.store(V.atom)).to(
        if_(S.eq(V.atom, S.bad), S.refused, fn.super(S.store(V.atom)))  # rung: the stored body of an equation naming `super`, which no compiled body reaches
    )

    assert guarded.eval(S.store(S.good)) == [S.stored(S.good)]
    assert guarded.eval(S.store(S.bad)) == [S.refused]
    # The space above is untouched by the shadow, which is what makes a shadow
    # a shadow rather than a replacement.
    assert store(S.bad) == [S.stored(S.bad)]

    # `super` reaches the engine's own definitions too.
    wrapping = metta.space(S.wrapping)
    head = fn.car_atom(V.expr)
    wrapping += equation(head).to(S.wrapped(fn.super(head)))  # rung: as above

    # `e[0]` is the dissolved spelling of car-atom everywhere the question is
    # "what is this expression's head". It is the wrong question here: this
    # example OVERRIDES car-atom, so the claim has to reach the space's own
    # equations, which only naming the head does.
    assert wrapping.fn.car_atom((1, 2, 3)) == [S.wrapped(1)]   # rung: the subject is the override, not the head
    # And every other space still gets the builtin it always had.
    assert m.fn.car_atom((1, 2, 3)) == [1]   # rung: as above

    # `evalc` is the other direction: it names the space absolutely, where
    # `super` names the next definition along, relatively.
    assert m.eval(S.store(S.good)) == [S.stored(S.good)]
