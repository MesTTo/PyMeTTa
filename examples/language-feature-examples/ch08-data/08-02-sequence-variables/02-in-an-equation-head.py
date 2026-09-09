"""Purpose: examples/ch08-data/08-02-sequence-variables/02-in-an-equation-head.metta in Python: a gap in the head of an equation.

A head that carries a gap is a function of variable arity, and Python's own
variadic spelling does not reach it: a compiled `def f(*xs)` is refused,
because `*args` has no MeTTa image at the parameter position. The equation is
therefore written as DATA, `equation(lhs).to(rhs)` under the write door, which
is the rung below the decorator and the one the ledger keeps for a head Python
cannot spell.

Everything else is ordinary. The runs the heads answer are slices of the calls
that produced them, the two-gap head answers once per split, and `fn.<name>`
calls each head the space now holds.
"""

from metta import S, V, equation, seg


def twin(m):
    """Install eight segment-headed equations and ask what each answers."""
    # A head whose only child is a gap: the whole argument list as one run.
    m += equation(S.allof(seg(V.xs))).to(S.kept(V.xs))  # rung: *args is refused at a compiled parameter
    # A gap between fixed children destructures instead.
    m += equation(S.middle(S.row(S.start, seg(V.mid), S.end))).to(V.mid)  # rung: as above
    # Two gaps in one head make the call nondeterministic.
    m += equation(S.split(S.row(seg(V.before), S.SEP, seg(V.after)))).to(  # rung: as above
        S.pair(V.before, V.after)
    )
    # An ordinary name keeps the run as one expression; a written marker
    # splices it into the expression around it.
    m += equation(S.project(S.head(seg(V.xs), S.tail))).to(  # rung: as above
        S.rebuilt(S.before, V.xs, S.after)
    )
    m += equation(S.splice(S.head(seg(V.xs), S.tail))).to(  # rung: as above
        S.rebuilt(S.before, seg(V.xs), S.after)
    )
    # One name in both roles, which only an equation head admits.
    m += equation(S.echoes((seg(V.xs), S.tag, V.xs))).to(S.yes)  # rung: as above
    # A gap head and an ordinary head are additive.
    m += equation(S.kind(S.row(...))).to(S.row_shaped)  # rung: as above
    m += equation(S.kind(V.other)).to(S.anything)  # rung: as above

    assert m.fn.allof() == [S.kept(S.allof()[1:])]
    assert m.fn.allof(S.a) == [S.kept(S.allof(S.a)[1:])]
    assert m.fn.allof(S.a, S.b, S.c) == [S.kept(S.allof(S.a, S.b, S.c)[1:])]

    filled = S.row(S.start, S.a, S.b, S.end)
    assert m.fn.middle(filled) == [filled[2:4]]
    assert m.fn.middle(S.row(S.start, S.end)) == [S.row()[1:]]

    # One call, one answer per split, shortest prefix first.
    splittable = S.row(S.a, S.SEP, S.b, S.SEP, S.c)
    assert list(m.fn.split(splittable)) == [
        S.pair(splittable[1:2], splittable[3:]),
        S.pair(splittable[1:4], splittable[5:]),
    ]

    written = S.head(S.a, S.b, S.tail)
    assert m.fn.project(written) == [S.rebuilt(S.before, written[1:3], S.after)]
    assert m.fn.splice(written) == [S.rebuilt(S.before, S.a, S.b, S.after)]

    # The ordinary occurrence stands for the expression the run makes, so the
    # call agrees only when the tail repeats the run.
    assert m.fn.echoes((S.a, S.b, S.tag, S.a(S.b))) == [S.yes]
    assert m.fn.echoes((S.tag, S.row()[1:])) == [S.yes]
    assert list(m.fn.echoes((S.a, S.b, S.tag, S.a(S.c)))) == []

    assert list(m.fn.kind(S.row(S.a, S.b))) == [S.row_shaped, S.anything]
    assert list(m.fn.kind(7)) == [S.anything]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 16115, 16115, 16115 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/02-in-an-equation-head.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 16115 to 16179 (+64), 16176 of it is drift between
#: a403e56b4 and this branch's base, and 3 is this change: the twin writes no
#: unify at all, and 3 is what its equation heads pay for the subject case
#: metta_seq_atoms/2 now distinguishes [measured 2026-09-07: min-of-3 serial
#: fresh processes, this branch against the same twin on its base 5a85f5602;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=f4ae837efd23791200846ba72556c2ce96a7d05a].
#: RE-PINNED 2026-09-07, 16115 to 16452 (+337), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 16452 to 16214 (-238), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 16214 to 16178 (-36), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 16178 to 16186 (+8), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 16186 to 16366 (+180), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 16366 to 16588 (+222), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 16366 to 16899 (+533), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 16899 to 17121 (+222), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 16366 to 16372 (+6), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 16372 to 16393 (+21), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 16393 to 17148 (+755), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +27 against the trunk's own pin of 17121 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +728 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 17148 to 19814 (+2666), The fixed diagnostic reader
#: now consumes parameter and argument spines together, and segment families
#: compile once per shape. Fixed-arrow presentation and warmed single-run
#: callees keep their controls. Fused syntax admission adds 44 inferences for a
#: cold prepare/admit type shape versus the old annotation scan and eight per
#: source-preflight declaration; repeated shapes reuse the analysis. The
#: authoring control moves by -16 once, with its per-definition slope
#: unchanged. Cold family generation is included. See
#: docs/journal/2026-09-09-the-splice-in-an-arrow.md [measured 2026-09-09: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
BUDGET = 19814
