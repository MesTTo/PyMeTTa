"""Purpose: examples/ch09-types/21-a_librarys_declared_types.metta in Python: the types an import brought in.

`m += lib.datastructures` brings the library's declarations in with its
equations, and `space.type` reads them back: a declaration is an atom in the
space, and an imported one is no different from a local one.

Two doors answer the same question at different arities. `space.type(atom)` is
the single-answer door and REFUSES when there is no type, naming the term,
where the original collapses `get-type` to the empty bag; `m.answers(...)` over
the built form is that bag, so both spellings are here for the two terms whose
arguments do not fit.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, Symbol, arrow, lib
from metta._errors.errors import EngineError

EMPTY = S.FTEmpty


def twin(m):
    """Read the four declarations back, then ask about two that do not fit."""
    m += lib.datastructures

    # `FTree` is declared `Type`, which is what makes the other three mean
    # anything.
    assert m.type(S.FTree) == S.Type

    # `FTEmpty` takes nothing, so its type is the type itself: it IS a tree
    # rather than a way of making one. The other two are arrows, and their
    # argument types say what each field holds.
    assert m.type(EMPTY) == S.FTree
    assert m.type(S.FTSingle) == arrow(S.Atom, S.FTree)
    assert m.type(S.FTDeep) == arrow(S.Expression, S.FTree, S.Expression, S.FTree)

    # Applying one answers the type its arrow ends in, which is how trees
    # built out of different constructors are all one type.
    assert m.type(S.FTSingle(1)) == S.FTree
    assert m.type(S.FTDeep((1, 2), EMPTY, (3, 4))) == S.FTree

    # A nullary constructor is a SYMBOL, and out here the metatype IS the
    # Python class, so nothing crosses the seam to ask for it. Wrapping it in
    # brackets would be a one-element expression rather than the atom the
    # library means, and neither side writes that form: the coverage lane
    # reads call position out of the corpus text, where a one-element
    # expression and a nullary call are the same characters.
    assert type(EMPTY) is Symbol
    assert type(S.FTSingle(1)) is Expression

    # The argument types are checked, and an application that does not fit has
    # no type at all rather than a wrong one.
    for bad in (S.FTSingle(1, 2), S.FTDeep(1, EMPTY, (3, 4))):
        assert m.answers(S.get_type(bad)) == []
        refused = None
        try:
            m.type(bad)
        except EngineError as refusal:
            refused = refusal
        assert "returned no type" in str(refused)
        assert repr(bad) in str(refused)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 22672 inferences, 0.9700x the example's 23372; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 22672 to 22926 (+254), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 22926 to 22961 (+35), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 22961 to 23013 (+52), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 22961 to 23722 (+761), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 23722 to 23774 (+52), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 22961 to 22870 (-91), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 22870 to 23683 (+813), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, -91 against the trunk's own pin of 23774 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +904 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 23683 to 23578 (-105), the binding resolves Janus
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
#: --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-13, 23578 to 103861 (+80283), Immutable maps and priority
#: queues are MeTTa equations over the shared collection libraries, replacing
#: the native tree adaptation [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9c9e60542491416e2c5e431a2672bb20f04264fa].
BUDGET = 103861
