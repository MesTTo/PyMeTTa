"""examples/ch08-data/08-02-sequence-variables/01-segments.metta in Python: a pattern child that stands for a run.

MeTTa's gap glyph is Python's own Ellipsis, so `...` in a pattern child
position is the anonymous gap and reads the same in both notations. The named
one is `seg(V.rest)`, and the run it takes arrives as an ordinary Expression on
the answer row, which is why the expected values below are SLICES: a run of
children is what `order[2:]` already means in Python.

The `case` arm is where Python had the concept and did not know it: a star
pattern in `match/case` IS the named gap. It needs a function to live in, and
the example's `case` is a runnable that stores nothing, so the function goes in
a scratch space and the home space holds exactly the four atoms the example
adds to it.

Two claims stay at the engine because Python has no spelling for either. The
two-operand `unify` is an engine head, reached through `m.fn.unify`; the
refusal outside the proved-finite fragments is an EngineError whose message
carries the theorem, since the structured payload the MeTTa side reads with
`index-atom` is not exposed as an attribute.
"""

from metta import S, V, seg, solve
from metta.errors import EngineError


def twin(m):
    """Read every arity a head has, name a run, and meet the fence."""
    seven = S.Order(7, S.x, S.y)
    eight = S.Order(8)
    m += seven
    m += eight
    m += S.Order(9, S.z)
    m += S.Note(1)

    # A gap matches any number of children, zero included, so one pattern
    # reads every arity the head has, and it does not widen the head.
    assert len(list(m[(S.Order, ...)])) == 3
    assert len(list(m[(S.Note, ...)])) == 1

    # A named gap answers the run it took, as the expression those children
    # make, which is the slice of the row after the children the pattern fixed.
    assert [row.rest for row in m[(S.Order, 8, seg(V.rest))]] == [eight[2:]]
    assert [row.rest for row in m[(S.Order, 7, seg(V.rest))]] == [seven[2:]]

    # Parsing by unification: two gaps around a separator enumerate the
    # splits, one answer per split, with no recursion written.
    row = (S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    splits = solve((V.pre, ..., S.SEP, ..., V.post), row)
    assert [(answer.pre, answer.post) for answer in splits] == [
        (S.a, S.d),
        (S.a, S.d),
    ]

    # A repeated named gap has to take the same run twice.
    repeated = (S.f, seg(V.run), S.mid, seg(V.run))
    twice = S.f(S.a, S.b, S.mid, S.a, S.b)
    assert [answer.run for answer in solve(repeated, twice)] == [twice[1:3]]
    assert list(solve(repeated, S.f(S.a, S.b, S.mid, S.c))) == []

    # A case arm reads a run the same way, and the first match wins.
    scratch = m.metta.space()

    @scratch.define
    def tail(order):
        match order:
            case (S.Order, id, *rest):
                return S.pair(id, rest)
            case _:
                return S.nope

    assert list(tail(seven)) == [S.pair(7, seven[2:])]
    assert list(tail(S.Note(1))) == [S.nope]

    # A marker written on the other operand of unify is data, so a gap
    # consumes one as a single child. Alpha equality, because the marker in the
    # answered run carries the engine's own fresh variable rather than the name
    # this file wrote.
    subject = S.f(S.a, S.b, seg(V.v))
    open_run = m.fn.unify(S.f(S.a, seg(V.u)), subject, V.u, S.none).one()
    assert open_run.alpha_eq(subject[2:])

    # The fence: general sequence unification is infinitary, so an ask outside
    # the three proved-finite fragments refuses and names the theorem.
    refusal = None
    try:
        m.fn.unify(S.f(seg(V.x), S.a), S.f(S.a, seg(V.x)), S.yes, S.no).one()
    except EngineError as error:
        refusal = error
    assert "Theorem 62" in str(refusal)
    assert "outside the proved finitary fragment" in str(refusal)

    # A marker a variable carries is data, never a gap: only what the program
    # wrote is read as one.
    m += S.Marked(..., S.tail)
    assert [row.slot for row in m[(S.Marked, V.slot, S.tail)]] == [S["..."]]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 9502, 9502, 9502 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/01-segments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 9502 to 9703 (+201), 9664 of it is drift between
#: a403e56b4, where the number was taken, and this branch's base, and 39 is
#: this change: the twin's two m.fn.unify asks are translated at the ask, so
#: parsing the right operand is counted here [measured 2026-09-07: min-of-3
#: serial fresh processes, this branch against the same twin on its base
#: 5a85f5602; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=f4ae837efd23791200846ba72556c2ce96a7d05a].
#: RE-PINNED 2026-09-07, 9502 to 9736 (+234), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 9736 to 9813 (+77), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 9813 to 9748 (-65), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 9748 to 9739 (-9), the evaluation-fuel scope marker is
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
#: RE-PINNED 2026-09-08, 9739 to 9770 (+31), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 9739 to 9914 (+175), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 9914 to 9924 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 9924 to 10026 (+102), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 9770 to 9803 (+33), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 9803 to 10044 (+241), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
BUDGET = 10044
