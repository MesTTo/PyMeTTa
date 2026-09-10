"""Purpose: examples/ch08-data/08-02-sequence-variables/03-the-one-sided-fragment.metta in Python: the fragment every gap ask lands in.

One side carries no gap at all, which is what every door in either notation
hands the matcher: `solve(pattern, row)` faces a built row, `space[pattern]`
faces stored atoms. So matching is the enumeration of the pattern's splits and
nothing more.

The expected runs are written as SLICES of the row they came out of, because a
run of children is exactly what Python's slice already means, and reading them
back is the ordinary atom protocol: `isinstance`, `len` and indexing.
"""

from metta import Expression, S, V, seg, solve


def twin(m):
    """Enumerate splits, take empty runs, repeat a name, and join a conjunct."""
    # Shortest first, one answer per split, so a two-gap pattern parses a
    # sequence with no recursion written.
    full = S.row(S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    splits = solve((seg(V.pre), S.SEP, seg(V.post)), full[1:])
    assert [(answer.pre, answer.post) for answer in splits] == [
        (full[1:3], full[4:]),
        (full[1:5], full[6:]),
    ]

    # Zero children is a run, so the empty case needs no separate arm.
    assert [answer.r for answer in solve((S.row, seg(V.r)), S.row())] == [S.row()[1:]]
    three = S.row(S.a, S.b, S.c)
    assert [answer.r for answer in solve((S.row, seg(V.r)), three)] == [three[1:]]

    # The run is an ordinary expression: read it the way any other is read.
    run = solve((S.row, seg(V.r)), S.row(S.a, S.b)).one().r
    assert isinstance(run, Expression)
    assert len(run) == 2
    assert run[0] == S.a

    # A repeated named gap has to take the same run twice, and "the same" is
    # the engine's own comparison rather than sameness of spelling.
    repeated = (S.f, seg(V.x), S.g, seg(V.x))
    twice = S.f(S.a, S.b, S.g, S.a, S.b)
    assert [answer.x for answer in solve(repeated, twice)] == [twice[1:3]]
    assert list(solve(repeated, S.f(S.a, S.b, S.g, S.c))) == []
    assert len(list(solve(repeated, S.f(1, S.g, 1.0)))) == 1

    # Distinct anonymous gaps are distinct variables, so neither constrains the
    # other; what pins this pattern down is the literal `g` between them. These
    # three patterns carry no name to project, so they ask through the engine's
    # own two-operand head: `solve` needs a variable in one of its sides.
    anonymous = m.fn.unify((S.f, ..., S.g, ...), S.f(S.a, S.g, S.b, S.c), S.matched, S.no)  # rung: solve refuses a wholly ground ask
    assert list(anonymous) == [S.matched]

    # A gap below the root matches inside a child, and a settled child that
    # disagrees refutes every split rather than some of them.
    nested = m.fn.unify((S.f, (S.g, ...), S.b), S.f(S.g(1, 2), S.b), S.matched, S.no)  # rung: as above
    assert list(nested) == [S.matched]
    clash = m.fn.unify((S.A, ..., S.D), S.A(S.b, S.c, S.E), S.matched, S.no)  # rung: as above
    assert list(clash) == [S.no]

    # Against a space the stored side is the value, so a gap pattern reads
    # every arity the gap can span and joins with an ordinary conjunct.
    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c, S.d)
    m += S.tag(S.b, S.hot)
    assert [row.last for row in m[(S.edge, S.a, ..., V.last)]] == [S.b]
    joined = m.match((S.edge, ..., V.mid), (S.tag, V.mid, V.heat))
    assert [(row.mid, row.heat) for row in joined] == [(S.b, S.hot)]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 7851, 7851, 7851 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/03-the-one-sided-fragment.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 7851 to 7953 (+102), 7868 of it is drift between
#: a403e56b4 and this branch's base, and 85 is this change: three m.fn.unify
#: asks, each translated at the ask, so each pays for parsing its right operand
#: [measured 2026-09-07: min-of-3 serial fresh processes, this branch against
#: the same twin on its base 5a85f5602; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f4ae837efd23791200846ba72556c2ce96a7d05a].
#: RE-PINNED 2026-09-07, 7851 to 7868 (+17), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 7868 to 7952 (+84), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 7952 to 7943 (-9), the evaluation-fuel scope marker is
#: a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 7943 to 7949 (+6), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 7949 to 8020 (+71), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 8020 to 8112 (+92), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 8020 to 8189 (+169), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 8189 to 8281 (+92), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 8020 to 8033 (+13), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 8033 to 8294 (+261), the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): boot publishes the initial vocabulary
#: types from a compiled payload through the tokenized funnel, a warm
#: membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +13 against the trunk's own pin of 8281 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +248 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 8294 to 8188 (-106), the binding resolves Janus
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
BUDGET = 8188
