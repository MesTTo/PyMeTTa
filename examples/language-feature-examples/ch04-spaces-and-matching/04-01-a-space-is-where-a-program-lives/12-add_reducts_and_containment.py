"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/12-add_reducts_and_containment.metta in Python: answers in, or programs in.

`add-atoms` stores what was written and `add-reducts` stores what it reduces
to, so the two spaces below hold a program and its answers. Both are called
through the function namespace rather than through `space += atom`, because
which of the two doors is being used IS the subject.

`space-contains` asks about UNIFICATION and answers one Bool, which is a
different question from a match: it binds nothing and costs one indexed probe
whatever the space holds.

What each space HOLDS is read through `space[pattern]`, which is what a match
is here, rather than through a collapse of `get-atoms`: a Python list IS the
collapse, so asking for one and then rendering it would be the long way round
to a count.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn


def twin(m):
    """Two write doors, and the containment probe over what each stored."""
    written = m.metta.space(S.written)
    reduced = m.metta.space(S.reduced)
    single = m.metta.space(S.single)
    contains = m.fn["space-contains"]

    # `add-atoms` stores what you wrote, so the space holds CALLS.
    assert m.fn.add_atoms(written, (fn.add(1, 1), fn.mul(2, 3))) == [True]
    assert len(written[fn.add(1, 1)]) == 1
    assert len(written[fn.mul(2, 3)]) == 1

    # `add-reducts` is the same door with the elements reduced first, so the
    # space holds ANSWERS. It is `add-reduct` over a list.
    assert m.fn.add_reducts(reduced, (fn.add(1, 1), fn.mul(2, 3))) == [True]
    assert len(reduced[2]) == 1
    assert len(reduced[6]) == 1
    assert m.fn.add_reduct(single, fn.add(1, 1)) == [True]
    assert len(single[2]) == 1
    assert len(single[fn.add(1, 1)]) == 0

    # Which of the two you want is the difference between a space of FACTS and
    # a space of PROGRAM.
    assert len(written[2]) == 0

    # `space-contains` answers True or False for one atom, and its atom
    # argument is HELD.
    assert contains(reduced, 2) == [True]
    assert contains(reduced, 99) == [False]
    assert contains(written, S["+"](1, 1)) == [True]
    assert contains(written, 2) == [False]

    # It asks about UNIFICATION rather than identity, so a stored atom with a
    # variable in it answers True for every atom that variable could stand for.
    written += S.edge(V.a, V.b)
    assert contains(written, S.edge(S.a, S.b)) == [True]
    assert contains(written, S.edge(V.x, V.y)) == [True]
    assert contains(written, S.node(S.a)) == [False]

    # The difference from a match is what comes back: a match binds and
    # enumerates, this answers one Bool and binds nothing.
    assert len(written[S.edge(V.x, V.y)]) == 1
    assert contains(written, S.edge(S.a, S.b)) == [True]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 5593 inferences, 0.8445x the example's 6623; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 5593 to 5561 (-32), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 5561 to 5903 (+342), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 5903 to 6058 (+155), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 6058 to 6315 (+257), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 6058 to 6156 (+98), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 6156 to 6413 (+257), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 6058 to 6186 (+128), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 6186 to 6541 (+355), the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): boot publishes the initial vocabulary
#: types from a compiled payload through the tokenized funnel, a warm
#: membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +128 against the trunk's own pin of 6413 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +227 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 6541 to 6535 (-6), Public add-atom calls
#: metta_add_atom/4 directly and the native bulk loop calls add_sexp_in/5
#: directly, removing one forwarding inference per accepted atom while keeping
#: the atomic token clock, hooks and errors. Open native enumeration uses the
#: shared native_storage_functor/2 mapping, including parametric scalar
#: storage. Receipt scopes retain the nearest unnested transaction and post no
#: cleanup when no reservation exists. Full-lane ten-round observations on the
#: repaired tree place this point below the published budget; the provisioned
#: cut is 3e5855a35d7b206c847845f12467551ea4c54a59. See the 2026-09-09 entries in
#: docs/journal/2026-09-07-every-fact-has-a-token.md. Autoload-only excursions
#: are excluded from this point selection and keep their pins [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 6535
