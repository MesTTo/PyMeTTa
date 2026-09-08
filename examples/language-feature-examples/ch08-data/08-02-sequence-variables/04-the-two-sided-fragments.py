"""examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.metta in Python: the two-sided fragments and the door that reaches them.

The last-position and linear-shallow calculi need a gap on BOTH sides, so they
need a door that hands the matcher two pieces of SYNTAX. `unify` is that door
and the only one, which is why every ask here goes through `m.fn.unify` rather
than through `solve`: `solve` lowers to `let`, whose subject is EVALUATED, so a
marker written there arrives as a value and a value's marker-shaped children
are data. That is not a limitation of Python's spelling, it is the same
one-sided reading `let` has in MeTTa, and 03 is the file it belongs to.

The four two-sided shapes and the trivial identity answered `none`, `no` and a
`mixed_roles` refusal until 2026-09-07, when the door began parsing both
operands; each one is now the answer its own calculus gives, and the identity
row agrees with upstream PeTTa, which has no reading of a gap at all and
unifies the two identical expressions. A pair outside all three fragments still
refuses, and 05-the-fence.py reads that refusal apart.
"""

from metta import Expression, S, V, seg
from metta.errors import EngineError


def twin(m):
    """Ask each two-sided shape through the door whose operands are syntax."""
    # One side with no gap is the one-sided fragment whichever side it is: a
    # gap written on the right alone consumes the left's children.
    assert m.fn.unify(S.f(S.a, S.b), S.f(S.a, seg(V.v)), V.v, S.none).one() == (
        S.f(S.a, S.b)[2:]
    )

    # Last position: the right side is longer by exactly its gap, so the run is
    # empty.
    assert m.fn.unify(
        S.f(S.a, S.b), S.f(S.a, S.b, seg(V.v)), V.v, S.none
    ).one() == Expression(())

    # A remainder that still holds the other side's gap keeps it, as the marker
    # that would match it, so the run IS the tail of the side it came from.
    # Alpha equality, because the marker in the answered run carries the
    # engine's own fresh variable rather than this file's name.
    longer = S.f(S.a, S.b, seg(V.v))
    open_run = m.fn.unify(S.f(S.a, seg(V.u)), longer, V.u, S.none).one()
    assert open_run.alpha_eq(longer[2:])
    whole = S.f(seg(V.v))
    whole_gap = m.fn.unify(S.f(seg(V.u)), whole, V.u, S.none).one()
    assert whole_gap.alpha_eq(whole[1:])

    # An anonymous gap is a name like any other here, absorbing the other
    # side's gap as one child of its run.
    assert list(m.fn.unify((S.f, ...), S.f(seg(V.v)), S.taken, S.none)) == [S.taken]

    # Linearity is not required in this fragment, so a name may occur twice and
    # its second occurrence solves the run its first took against what it
    # faces.
    repeated = m.fn.unify(
        (S.f, (S.g, seg(V.x)), (S.h, seg(V.x))),
        S.f(S.g(seg(V.y)), S.h(S.b)),
        V.x,
        S.none,
    )
    assert repeated.one() == S.f(S.b)[1:]

    # And the calculus keeps `X = X` as trivial rather than as a clash, so a
    # name written as a gap on both sides plays one role and the pair holds.
    assert list(m.fn.unify(S.f(seg(V.u)), S.f(seg(V.u)), S.yes, S.no)) == [S.yes]

    # The fragment is unitary: one answer or none, never a stream.
    assert len(list(m.fn.unify(S.f(S.a, S.b), S.f(S.a, S.b, seg(V.v)), V.v, S.none))) == 1

    # Linear shallow: two root gaps, each taking the other side's fixed child.
    pair = m.fn.unify(
        (S.f, seg(V.u), S.b), S.f(S.a, seg(V.v)), (V.u, V.v), S.no
    ).one()
    assert pair == Expression((S.f(S.a)[1:], S.f(S.b)[1:]))

    # What a gap absorbs is whole children, expressions included, so two gaps
    # can trade the settled children written between them.
    traded = m.fn.unify(
        (S.f, seg(V.u), (S.g, S.a)), S.f(S.g(S.b), seg(V.v)), (V.u, V.v), S.no
    ).one()
    assert traded == Expression(
        (Expression((S.g(S.b),)), Expression((S.g(S.a),)))
    )

    # Each of those answers once too, because each gap is pinned by the other
    # side's settled children.
    assert len(list(
        m.fn.unify((S.f, seg(V.u), S.b), S.f(S.a, seg(V.v)), (V.u, V.v), S.no)
    )) == 1

    # A space operand makes the ask a query, which is one-sided again: the
    # stored side is data. Both doors then answer the same rows.
    m += S.friend(S.Bob, S.Alice)
    m += S.friend(S.Carol, S.Alice)
    queried = list(m.fn.unify(m, S.friend(seg(V.who)), V.who, S.none))
    assert queried == [S.friend(S.Bob, S.Alice)[1:], S.friend(S.Carol, S.Alice)[1:]]
    assert [row.who for row in m[(S.friend, seg(V.who))]] == queried

    # Outside all three fragments the ask refuses. Kutsia's own witness is a
    # pair of root gaps sharing one name across a settled child, which is
    # neither all-final nor linear, so it has no certificate.
    refusal = None
    try:
        list(m.fn.unify((S.f, seg(V.x), S.a), S.f(S.a, seg(V.x)), S.yes, S.no))
    except EngineError as error:
        refusal = error
    assert "no_certificate" in str(refusal)


#: What this twin spends, its own tripwire, taken on the tree that
#: rewrote it onto the two-sided door, with the engine's .qlf set built,
#: which is what the gate leaves behind and what ships. The twin it
#: replaces asked through `solve` and priced 8469; the door changed, so the
#: number is a fresh measurement rather than a re-pin of that one.
#: [measured: 11233, 11233, 11233 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 77; commit=f4ae837efd23791200846ba72556c2ce96a7d05a]
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 8469, 8469, 8469 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 8469 to 8629 (+160), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 8629 to 11232 (+2603), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 11232 to 11197 (-35), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 11197 to 11209 (+12), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 11197 to 11360 (+163), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 11360 to 11567 (+207), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 11567 to 11806 (+239), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
BUDGET = 11806

#: OVERRUN 2026-09-07, 4500: it asks through `solve`, the pattern door, where
#: the example asks through `unify`, the one MeTTa form whose operands are both
#: syntax; the door costs 367 inferences an ask against the form's 259.
#: Measured 8629 against a ceiling of 4164; a MINIMAL twin of this example --
#: its own forms stored and asked through the structured door, nothing else --
#: costs 6467 against the ceiling's 4164, so no twin of it fits the band at all
#: [measured 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
OVERRUN = 4500
