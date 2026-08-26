"""Purpose: examples/libraries/patrick.metta in Python: as-patterns, comprehension, and a lambda.

Three of lib_patrick's own forms, so all three stay named.

`mirror` is at the container door, and the residue entry says exactly what is
missing. Its body is a `let` whose PATTERN wins the variables from what the
subject produces, `(@ $L (cons $head $tail))` run backwards against the
argument. `solve(pattern, subject)` is that let's Python spelling and the same
combinator this file's sibling twin uses live, but a compiled body REFUSES it,
naming it as neither a parameter, a known function nor a constructor, so the
equation is built instead of compiled.

`for` reads like a comprehension and is not one: its body `(if (> $x 3) $x)` is
an `if` with NO else, which answers nothing for the items it rejects, and
Python's conditional expression requires the else. `if_` takes that one-armed
filtering form as well as the three-armed conditional, so the claim is written
with the keyword builder and the comparison takes the operator's WORD, `S.gt`,
Python's `>` having been given to atom ordering.

`iterate`'s step is `(|-> ($i $x) (+ $x $i))`, a MeTTa lambda, built as the term
it is. A Python `lambda i, x: x + i` is accepted in that position and answers
46 too, and the twin does NOT take it: it spends one janus crossing per
element, which is the crossing the three-lane model prices per collection.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, if_, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 41267 to 41342, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 41342 to 41345, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 41345 to 41351, on the release tree:
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
#: RE-PINNED 2026-08-26, 41351 to 43052 (+1701), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 43052


def twin(m):
    """Mirror a name around its head, filter six numbers, and fold ten."""
    m += lib.patrick

    # The as-pattern names the whole argument and destructures it at the same
    # time. It is a function, so it goes in the body under a `let` that unifies
    # it with the argument: a head is a pattern and matches structurally.
    m += equation(S.mirror(V.A)).to(S.let(V.A, S["@"](V.L, S.cons(V.head, V.tail)), S.append(S.reverse(V.L), V.tail)))  # rung: this `let` unifies a PATTERN against its argument rather than binding a name to a value, and its Python spelling, solve(), is refused inside a compiled body

    mirrored = m.fn.mirror((S.h, S.a, S.n, S.n, S.e, S.s)).one()
    assert list(mirrored) == [S.s, S.e, S.n, S.n, S.a, S.h, S.a, S.n, S.n, S.e, S.s]

    kept = m.fn["for"](V.x, (1, 2, 3, 4, 5, 6), if_(S.gt(V.x, 3), V.x))
    assert kept == [4, 5, 6]

    step = S["|->"](Expression((V.i, V.x)), V.x + V.i)
    assert m.fn.iterate(0, 10, 1, step) == [46]
