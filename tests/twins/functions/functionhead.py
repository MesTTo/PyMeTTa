"""Purpose: examples/functions/functionhead.metta in Python: an argument constrained to be a call's OUTPUT.

An equation HEAD cannot carry the constraint, because a head is a pattern and
a pattern is matched structurally at every depth: `(= (h (myfunc (10) $B) $C)
...)` asks for a first argument that IS the three-element expression, not for
one the call can produce. So the constraint goes in the BODY, where the
argument is unified with what the call produces, the call runs backwards, and
`$B` comes out bound.

All three definitions are ordinary Python functions. What makes that possible
is the mention doors a compiled body now has: `V.b` MINTS the hole the
backwards call fills, a variable no parameter supplies; `fn.append` and
`fn["="]` name engine functions whose spellings Python's grammar will not take
as bare identifiers; and `S.let` names the relational `let` itself, which has
no Python statement, because assignment is `let` in the OTHER direction, where
the pattern is a fresh name and the subject is the call.

`h_old` tests with `=`, MeTTa's unification, and `fn["="]` is the function
namespace's exact spelling for that head; the newer `h` says the same thing
with the inversion door.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, fn


def twin(m):
    """Constrain an argument to be what a call produces, two ways."""

    @m.define
    def myfunc(a, b):
        # (= (myfunc $A $B) (append (append (42) $A) $B))
        return fn.append(fn.append((42,), a), b)

    # The example's own head carries an underscore, which the naming ladder's
    # total underscore-to-hyphen map does not produce, so this one door takes
    # the exact name.
    @m.define(name="h_old")  # rung: def h_old maps to h-old, while the source head is h_old
    def h_old(a, c):
        # (= (h_old $A $C) (if (= $A (myfunc (10) $B)) ($B $C) (empty)))
        return (V.b, c) if fn["="](a, myfunc((10,), V.b)) else fn.empty()

    @m.define
    def h(a, c):
        # (= (h $A $C) (let $A (myfunc (10) $B) ($B $C)))
        return S.let(a, myfunc((10,), V.b), (V.b, c))  # rung: relational let

    # Both claims call the decorated functions rather than naming their heads.
    # `h_old`'s MeTTa name carries an underscore, and the factory's attribute
    # door applies rung 4's total map, so `S.h_old` is the atom `h-old` and
    # would ask about a head nothing defines; the exact spelling is
    # `S["h_old"]`. Calling the Python name sidesteps the trap entirely.
    assert h((42, 10, 40), 42000) == [Expression(((40,), 42000))]
    assert h_old((42, 10, 40), 42000) == [Expression(((40,), 42000))]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 20764 to 20804, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 20804 to 20810, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 20810 to 20779, on the release tree:
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
#: RE-PINNED 2026-08-25, 20779 to 20784, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 20784 to 22706 (+1922), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 22706 to 22728 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 22728 to 21203 (-1525), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 21203
