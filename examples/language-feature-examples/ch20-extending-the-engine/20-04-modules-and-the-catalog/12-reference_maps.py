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
#: fixture=built native engine after deleting engine/lib QLF; commit=89084b43ff1a758f703ce77cd96b026f56510116]
#: RE-PINNED 2026-09-18, 271057 to 278009 (+6952), the branch's landings since
#: the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 278009 to 278326 (+317), 49478d67a landed the
#: polynomial carrier, whose preset row and variable claim every catalog scan
#: reads, the product carriers and the guard read in the fixpoint door, and the
#: binding's five-element rule read: the examples that scan the catalog moved
#: with their twins (restricted_spaces +522, the three pln twins +63 each, the
#: two tabling twins +20 and +10, reflect_lib +6) and the twins that cross the
#: seat's declaration and query paths moved with their examples unmoved (the
#: class twins between -4212 and +2841, the reference twins +208 and +317, the
#: tagged fixpoint twin +610, the documentation twins -22 and -50, types_nondet
#: +5) [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-PINNED 2026-09-18, 278326 to 276024 (-2302), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=55d451b670949c2dc9d2ab7bc678f33f21094bd2].
#: RE-PINNED 2026-09-19, 276024 to 276059 (+35), cost follows the answer: a
#: block is charged for its own thread's work and for the workers whose answers
#: it used, so a race's losers, the branches par-any and par-forall stopped,
#: and a cancelled future or timer are joined through the engine's discarding
#: door (metta_join_measured/3) and their partial spend, which only the
#: schedule sized, is taken out; lib_thread's join no longer polls on the host
#: patched for swi-thread-join-detach-window, and the seat's counter doors read
#: the discarded tally outside the window they bracket (metta_py_stats/2,
#: metta_py_work/2) [measured 2026-09-19: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=32335687084e4d8ad43cf8800f2dedce707fa137].
#: ENVELOPED 2026-09-19: the point 276059 becomes the envelope 276059..276387
#: over 11: under the lane's own protocol (full-lane/294/workers=32, ten
#: rounds) the counter reads 276059 every time, and under the gate's concurrent
#: lanes (three runs) it reads 276387, each reading exact on its run; the extra
#: mode is the same program's work done on a different thread under load, a
#: loader flight or a settle step the foreground runs itself when the worker is
#: late, which the join accounting does not reach; an envelope states what was
#: observed and the point was a lie under the gate [measured 2026-09-19: the
#: twins lane alone on the final tree and under the gate's concurrent lanes,
#: wt-battery-2 ai-full-gate-10da82e4a.log, ai-full-gate-19fdb0b86.log, ai-
#: lanes-exports-back.log; commit=1ccbb142315d16a719807cd2c9754e4a2fcefdf1].
BUDGET = {
    "minimum": 276059,
    "maximum": 276387,
    "observations": 11,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
