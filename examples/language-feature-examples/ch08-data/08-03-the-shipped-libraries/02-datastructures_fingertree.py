"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/02-datastructures_fingertree.metta in Python: the finger tree, walked.

The finger tree from lib_datastructures: O(1) at both ends, O(log n)
concatenation, one structure serving as sequence and deque at once. Fifteen
claims, every one of them about one of the eleven `ft-*` functions, so all
eleven are named.

Every claim nests the calls the way Python nests calls,
`push_front(1, push_back(3, push_front(2, ft_empty())))` through
`m.fn.ft_push_front` and its siblings. A call answers a lazy view, and a view
crossing into term position is an observation point: exactly one answer is
encoded, and zero or several refuse loudly, so a deterministic function
composes without any `.one()` between the levels. The one place `.one()` is
written is where a pop's single answer is UNPACKED into two Python names.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, lib


def twin(m):
    """Build, inspect, drain, and concatenate finger trees from Python."""
    m += lib.datastructures

    ft_empty, from_list, to_list = m.fn.ft_empty, m.fn.ft_from_list, m.fn.ft_to_list
    push_front, push_back = m.fn.ft_push_front, m.fn.ft_push_back
    front, back = m.fn.ft_front, m.fn.ft_back
    pop_front, pop_back = m.fn.ft_pop_front, m.fn.ft_pop_back
    concat, is_empty = m.fn.ft_concat, m.fn.ft_is_empty

    built_at_both_ends = push_front(1, push_back(3, push_front(2, ft_empty())))
    assert to_list(built_at_both_ends) == [Expression((1, 2, 3))]

    ten = (S.a, S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert to_list(from_list(ten)) == [Expression(ten)]

    abc = from_list((S.a, S.b, S.c))
    assert front(abc) == [S.a]
    assert back(abc) == [S.c]

    # A pop answers the element and the remaining tree, so the example reads
    # both out of one answer; Python's own unpacking is that reading.
    item, remainder = pop_front(abc).one()
    assert (item, to_list(remainder)) == (S.a, [S.b(S.c)])

    item, remainder = pop_back(abc).one()
    assert (item, to_list(remainder)) == (S.c, [S.a(S.b)])

    deep = tuple(range(1, 16))
    assert to_list(from_list(deep)) == [Expression(deep)]

    deque = push_back(9, push_front(0, from_list((4, 5, 6))))
    assert to_list(deque) == [Expression((0, 4, 5, 6, 9))]

    left, right = from_list((1, 2, 3, 4, 5)), from_list((6, 7, 8, 9, 10))
    assert to_list(concat(left, right)) == [Expression(range(1, 11))]
    assert to_list(concat(ft_empty(), from_list((S.x, S.y)))) == [S.x(S.y)]
    assert to_list(concat(from_list((S.x, S.y)), ft_empty())) == [S.x(S.y)]

    singleton = push_front(S.a, ft_empty())
    seven = from_list((S.b, S.c, S.d, S.e, S.f, S.g, S.h))
    assert to_list(concat(singleton, seven)) == [
        S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h)
    ]

    assert is_empty(ft_empty()) == [True]
    assert is_empty(push_front(1, ft_empty())) == [False]

    nested = from_list((S.nested(S.pair), S.plain))
    assert front(nested) == [S.nested(S.pair)]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 264 inferences over the concurrent lane's own observations, because
#: the shared engine's scheduling changes what a concurrent round costs
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 451921 to 452776, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 452776 to 452137, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 452137 to 452229, on the release tree:
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
#: RE-PINNED 2026-08-25, 452229 to 452495, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 452495 to 452854 (+359), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 452854 to 452374 (-480), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 452374 to 452214 (-160), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 452214 to 450830 (-1384), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 450830 to 239106 (-211724), the compiled-language
#: batch: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
BUDGET = 239106
