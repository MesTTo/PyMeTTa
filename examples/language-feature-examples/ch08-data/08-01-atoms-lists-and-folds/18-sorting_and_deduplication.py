"""Purpose: examples/ch08-data/08-01-atoms-lists-and-folds/18-sorting_and_deduplication.metta in Python: four ways to tidy a collection.

`sort`, `msort` and `list_to_set` keep their Prolog underscores and come
through the exact subscript door; `sort-atom` is a MeTTa name and takes the
host-convention map.

`alpha-unique` works over an answer STREAM rather than an expression, so its
Python spelling is an answer LIST: `m.answers(fn.alpha_unique(fn.superpose(...)))`
is the collapse, because a list IS what collapse answers. Its answers carry
fresh variables, so the claims read their heads and their length rather than
comparing variable names the engine mints.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, V, fn

#: The one string this file compares, as ground data rather than as source.
G_TEXT = G("s")


def twin(m):
    """Order, deduplicate, drop an item, and deduplicate up to renaming."""
    # COST, recorded rather than hidden: this twin costs 16159 against the
    # example's 11629, past the 10% band and with no compiled definition to
    # earn the band's per-definition credit. The gap is the Python boundary
    # rather than anything this file does differently -- twenty calls cross
    # it where the example's twenty forms are compiled into one program --
    # and it is the library's to close, not this twin's
    # [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
    # --measure --rounds 3 on this file's own pair].
    ordered, kept, merged = m.fn["sort"], m.fn.sort_atom, m.fn["msort"]
    to_set, exclude = m.fn["list_to_set"], m.fn.exclude_item

    # `sort` is the standard order of terms with duplicates REMOVED;
    # `sort-atom` and `msort` order and keep them.
    assert ordered((3, 1, 2, 1)) == [(1, 2, 3)]
    assert kept((3, 1, 2, 1)) == [(1, 1, 2, 3)]
    assert merged((3, 1, 2, 1)) == [(1, 1, 2, 3)]
    assert ordered(()) == [()]

    # The order is the STANDARD order of terms, so mixed content still has
    # one total order: numbers, then strings, then names.
    assert ordered((S.b, S.a, 10, 2, G_TEXT)) == [(2, 10, G_TEXT, S.a, S.b)]

    # `list_to_set` removes duplicates and keeps the ORIGINAL order.
    assert to_set((S.b, S.a, S.b, S.c, S.a)) == [(S.b, S.a, S.c)]
    assert to_set((3, 1, 2, 1)) == [(3, 1, 2)]
    assert to_set(()) == [()]

    # `exclude-item` drops one named item wherever it appears, item first.
    assert exclude(2, (1, 2, 3, 2)) == [(1, 3)]
    assert exclude(S.x, (1, 2, 3)) == [(1, 2, 3)]
    assert exclude(1, (1, 1, 1)) == [()]

    # `alpha-unique` deduplicates an answer stream up to a consistent renaming
    # of variables; `unique` compares atoms exactly, so two answers differing
    # only in a variable's name both survive there and one survives here.
    varied = (S.f(V.x), S.f(V.y), S.g(V.z))
    assert len(m.answers(fn.unique(fn.superpose(varied)))) == 3
    alpha = m.answers(fn.alpha_unique(fn.superpose(varied)))
    assert [answer[0] for answer in alpha] == [S.f, S.g]

    # A ground answer is only alpha-equivalent to itself, so on ground data
    # the two agree.
    assert m.answers(fn.alpha_unique(fn.superpose((1, 2, 1, 3)))) == [1, 2, 3]
    assert m.answers(fn.unique(fn.superpose((1, 2, 1, 3)))) == [1, 2, 3]

    # And a variable answer is not the same as the ground one it would unify
    # with: (f $x) and (f 1) are two answers, not one.
    mixed = m.answers(fn.alpha_unique(fn.superpose((S.f(V.x), S.f(V.y), S.f(1)))))
    assert len(mixed) == 2
    assert mixed[1] == S.f(1)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 16159 inferences, 1.3895x the example's 11629; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=e04c24d15b80804a8db7bcf6f2b8e99135e84793].
#: RE-PINNED 2026-09-08, 16159 to 16118 (-41), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 16118 to 16480 (+362), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 16480 to 16705 (+225), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 16705 to 16978 (+273), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 16705 to 16817 (+112), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 16817 to 16021 (-796), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 16021 to 16294 (+273), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 16705 to 17036 (+331), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 17036 to 16625 (-411), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +331 against the trunk's own pin of 16294 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining -742 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 16625 to 16408 (-217), the binding resolves Janus
#: maplist/2 at boot, removing its first-failure autoload; one compiled option
#: policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=WORKTREE].
BUDGET = 16408

#: OVERRUN 2026-09-08, 3500: the twin reads 16161 against a ceiling of 12794
#: (the example's 11631 plus 10%, no definition to author), and the FLOOR any
#: Python twin of this example can reach is 13451, above the ceiling itself:
#: the band is tighter than the library's own floor for a program that sorts
#: and deduplicates through the structured evaluation door, which is the
#: class the burn-down found eleven times. The 2710 above the floor is this
#: twin's own program, which proves each claim through both the Python
#: spelling and the engine's operation [measured 2026-09-08: one fresh
#: process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: OVERRUN 2026-09-08, 3500 to 3689 (+189, four of them the deterministic
#: allowance the point pins carry, because a band met exactly is refused): the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 16705
#: against a ceiling of 16520; a minimal twin costs 13815 against the band's
#: 13020, above that ceiling, so no twin of it fits the band at all, as before
#: [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
OVERRUN = 3689
