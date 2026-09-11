"""Purpose: reference_maps.metta in Python using head maps as ordinary atoms.

from_ writes the row; the engine evaluates its map once per source head.
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/12-reference_maps.metta; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
"""

from metta import S, V

PAYLOAD = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/maps"]


def twin(m):
    """Select and rename one canonical home's public heads."""
    m.from_(PAYLOAD, S.only((S.map_value,)))
    assert m.fn.map_value(2) == [3]
    assert m.eval(S.map_label()) == [S.map_label()]
    m.from_(PAYLOAD, S.except_((S.map_value,)))
    assert m.fn.map_label() == [S.label]
    m.from_(PAYLOAD, S.prefix(S["p."]))
    m.from_(PAYLOAD, S.rename(((S.map_value, S.renamed),)))
    m.from_(PAYLOAD, S.qualified(S.module))
    assert m.fn["p.map-value"](2) == [3]
    assert m.fn.renamed(2) == [3]
    assert m.fn["module.map-value"](2) == [3]
    assert m.fn.map_label() == [S.label]

    m.from_(PAYLOAD, S["|->"]((V.h,), S.if_(
        S["=="](V.h, S.map_value),
        S.superpose((S.lambda_one, S.lambda_two)), S.empty(),
    )))
    assert m.fn.lambda_one(2) == [3]
    assert m.fn.lambda_two(2) == [3]
    assert m.fn.prefix(S["text."], S.word) == [S["text.word"]]
    m.fn["pragma!"](S.from_map, S.prefix(S["default."]))
    m.from_(PAYLOAD)
    assert m.fn["default.map-value"](2) == [3]
    m.fn["pragma!"](S.from_map, S.none)


#: Face publication defers dependent repairs until every linked head is ready,
#: so the shared lambda compiles once. Both spellings exercise all six maps.
#: [measured: 228075 inferences, min-of-3 fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/12-reference_maps.metta;
#: fixture=built native engine; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427]
#: RE-PINNED 2026-09-10, 228075 to 227143 (-932), The reference, visibility and
#: property declarations add six heads to the cold-import census. Partial
#: catalog reads now sort occurrence tokens; source-scoped claims and cache
#: reservations change first translation work. The explicitly revised lib_he
#: examples load upstream equations. Warm imports save nine inferences through
#: one rollback collection; ordinary call and row slopes stay unchanged
#: [measured 2026-09-10: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
#: RE-PINNED 2026-09-11, 227143 to 227465 (+322), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-11, 227465 to 227513 (+48), engine/metta/limits.pl
#: (docs/host-workarounds.md: swi-autoload-cut-installs-the-undefined-
#: supervisor, swi-findall-bag-push-window): every first-use resolution of an
#: undefined predicate pays one inference for the catch around the trap query,
#: and a twin that bounds pays one inference per findall under the bound plus
#: the first bound of its process installing the findall scope [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
BUDGET = 227513
