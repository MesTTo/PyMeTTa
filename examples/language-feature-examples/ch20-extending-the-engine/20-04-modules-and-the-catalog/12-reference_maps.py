"""Purpose: reference_maps.metta in Python using name and call-pattern maps.

from_ writes the row; the engine evaluates its map once per source head.
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/12-reference_maps.metta; commit=a95e6c90c910db30c72311abadd58dee5349978c].
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

    m.from_(PAYLOAD, S.rename(((S.map_value, S.only_two(2)),)))
    assert m.fn.only_two(2) == [3]

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
#: RE-PINNED 2026-09-13, 227143 to 270967 (+43824). The call-pattern row
#: installs another native alias and its declarations; later references
#: include that binding in their published faces. Mapper results now carry
#: canonical argument constraints. Native 260533; both spellings prove 12 claims.
#: [measured: 270967 inferences, min-of-3 fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/12-reference_maps.metta;
#: fixture=built native engine; commit=a95e6c90c910db30c72311abadd58dee5349978c]
#: RE-PINNED 2026-09-13, 270967 to 271057 (+90). Effect planning follows
#: canonical reference bodies and keeps the defining module in its traversal.
#: [measured: 271057 twin and 260623 native inferences, min-of-3 fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/12-reference_maps.metta;
#: fixture=built native engine after deleting engine/lib QLF; commit=WORKTREE]
BUDGET = 271057
