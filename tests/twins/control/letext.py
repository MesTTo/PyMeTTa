"""Purpose: examples/control/letext.metta in Python: `let` matches a pattern.

`let` binds by MATCHING a pattern against a value, not by naming a variable:
`($x (42 (if (== $x 2) 43 44)))` meets `(3 (42 $z))`, so `$x` takes 3 from the
left of the value and `$z` takes what the right of the pattern holds.
Variables on BOTH sides bind at once, and the body then adds them, so the
answer is 47.

That is exactly the cell `solve` fills: assignment is the `let` whose pattern
is a fresh name, and `solve(pattern, subject)` is the `let` whose PATTERN must
win variables. Its answer carries BOTH sides' variables, `.x` from the pattern
and `.z` from the subject, already reduced, and the template is then whatever
Python writes with them. The `if` inside the pattern is `if_`, the keyword
builder for stored code, and the equality inside it is built by its operator
WORD, because `==` between two atoms is Python's structural test rather than a
term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, if_, solve


def twin(m):
    """Bind in both directions at once, then use what was bound."""
    # !(test (let ($x (42 (if (== $x 2) 43 44))) (3 (42 $z)) (+ $x $z)) 47)
    with m:
        bound = solve((V.x, (42, if_(S.eq(V.x, 2), 43, 44))), (3, (42, V.z)))
    assert m.eval(bound.x + bound.z) == [47]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1190 to 1209, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 1209 to 1210, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1210 to 1212, on the release tree:
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
#: RE-PINNED 2026-08-25, 1212 to 1214, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 1214
